from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import streamlit as st


# -------------------- Configuração --------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LATEST = REPO_ROOT / "opcua_client" / "latest_data.json"
DEFAULT_DB = REPO_ROOT / "data" / "aas_history.sqlite3"

st.set_page_config(page_title="SCARA Dashboard", layout="wide")


# -------------------- Acesso a dados --------------------

def _connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


@st.cache_data(show_spinner=False, ttl=5.0)
def list_paths(db_path: str) -> List[Tuple[str, str]]:
    if not db_path or not Path(db_path).exists():
        return []
    with _connect(Path(db_path)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT DISTINCT submodel_name, element_path FROM timeseries ORDER BY submodel_name, element_path LIMIT 2000"
        )
        return [(r[0], r[1]) for r in cur.fetchall()]


@st.cache_data(show_spinner=False, ttl=2.0)
def load_timeseries(db_path: str, submodel: str, path: str, limit: int = 300) -> List[Tuple[str, float]]:
    if not db_path or not Path(db_path).exists():
        return []
    with _connect(Path(db_path)) as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT value, created_at
            FROM timeseries
            WHERE submodel_name = ? AND element_path = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (submodel, path, limit),
        )
        rows = [(str(t), float(v)) for (v, t) in cur.fetchall()]
        rows.reverse()  # do mais antigo para o mais recente
        return rows


@st.cache_data(show_spinner=False, ttl=1.0)
def load_latest(latest_path: str) -> Dict[str, Any]:
    p = Path(latest_path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}


def load_latest_http(url: str) -> Dict[str, Any] | None:
    """Busca o snapshot mais recente via REST com cabeçalhos condicionais.

    Retorna o dicionário se houver mudança ou None em caso de 304 (não modificado).
    Armazena ETag/Last-Modified em session_state para polling eficiente.
    """
    try:
        import requests  # type: ignore
    except Exception:
        return {}

    headers: Dict[str, str] = {"Cache-Control": "no-cache"}
    etag_key = "_etag"
    lm_key = "_last_modified"
    if etag_key in st.session_state:
        headers["If-None-Match"] = str(st.session_state[etag_key])
    if lm_key in st.session_state:
        headers["If-Modified-Since"] = str(st.session_state[lm_key])
    try:
        r = requests.get(url, headers=headers, timeout=2)
        if r.status_code == 304:
            return None
        r.raise_for_status()
        st.session_state[etag_key] = r.headers.get("ETag") or st.session_state.get(etag_key)
        st.session_state[lm_key] = r.headers.get("Last-Modified") or st.session_state.get(lm_key)
        return r.json()
    except Exception:
        return {}


# -------------------- Utilitários de UI --------------------

def kpi_pill(text: str, tone: str = "neutral") -> str:
    palette = {
        "ok": "#16c266",
        "warn": "#f39c12",
        "err": "#e74c3c",
        "neutral": "#7a8598",
    }
    color = palette.get(tone, palette["neutral"])
    return (
        "<span style='display:inline-block;padding:6px 10px;border-radius:999px;"
        "border:1px solid rgba(255,255,255,.12);color:" + color + ";'>" + str(text) + "</span>"
    )


def classify_status(status_text: str) -> str:
    s = (status_text or "").lower()
    if any(x in s for x in ("estop", "fault", "error")):
        return "err"
    if any(x in s for x in ("slow", "manual")):
        return "warn"
    return "ok"


def col_metrics(latest: Dict[str, Any]) -> None:
    op = latest.get("OperationalData", {}) if isinstance(latest, dict) else {}
    tech = latest.get("TechnicalData", {}) if isinstance(latest, dict) else {}

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.caption("Working Mode")
        st.markdown(kpi_pill(op.get("WorkingMode", "--")), unsafe_allow_html=True)
    with c2:
        st.caption("Robot Status")
        s = str(op.get("RobotStatus", "--"))
        st.markdown(kpi_pill(s, classify_status(s)), unsafe_allow_html=True)
    with c3:
        st.caption("Cycle Time")
        st.markdown(kpi_pill(op.get("CycleTime", "--")), unsafe_allow_html=True)
    with c4:
        st.caption("Payload User")
        st.markdown(kpi_pill(str(tech.get("PayloadUser", "--")), "ok"), unsafe_allow_html=True)


def joints_values(latest: Dict[str, Any]) -> List[str]:
    op = latest.get("OperationalData", {}) if isinstance(latest, dict) else {}
    labels = ["JointPosition1", "JointPosition2", "JointPosition3", "JointPosition4"]
    out: List[str] = []
    for name in labels:
        vals = op.get(name)
        if isinstance(vals, list) and vals:
            try:
                avg = sum(float(v) for v in vals) / len(vals)
                out.append(f"{avg:.1f}°")
            except Exception:
                out.append("--")
        else:
            out.append("--")
    return out


def plot_timeseries(rows: Sequence[Tuple[str, float]]) -> None:
    try:
        import pandas as pd  # type: ignore
        import altair as alt  # type: ignore

        if not rows:
            st.info("Sem dados de histórico para exibir.")
            return
        df = pd.DataFrame(rows, columns=["t", "v"])  # t as ISO string
        df["t"] = pd.to_datetime(df["t"], errors="coerce")
        line = (
            alt.Chart(df)
            .mark_line(color="#16c266")
            .encode(x=alt.X("t:T", title="Tempo"), y=alt.Y("v:Q", title="Valor"))
            .properties(height=260)
        )
        st.altair_chart(line, use_container_width=True)
    except Exception:
        st.line_chart([v for (_, v) in rows], height=260)


# -------------------- Aplicação --------------------

def main() -> None:
    st.title("SCARA Dashboard")

    # Controles da barra lateral
    st.sidebar.header("Configuração")
    source = st.sidebar.radio("Fonte do snapshot", ["Arquivo local", "REST API"], index=0)
    latest_path = st.sidebar.text_input("Arquivo de snapshot (latest_data.json)", str(DEFAULT_LATEST))
    api_url = st.sidebar.text_input("Endpoint REST (/api/latest)", "http://127.0.0.1:8000/api/latest")
    db_path = st.sidebar.text_input("Banco SQLite (aas_history.sqlite3)", str(DEFAULT_DB))
    # Seções fixas / espaços reservados
    st.subheader("Status Atual")
    kpi_ph = st.empty()
    joints_ph = st.expander("Juntas (médias)", expanded=True)
    # Placeholders persistentes para juntas (sobrescrevem o valor no mesmo lugar)
    with joints_ph:
        _joint_cols = st.columns(4)
        joint_ph = [_joint_cols[i].empty() for i in range(4)]

    st.subheader("Histórico")
    paths = list_paths(db_path)
    if not paths:
        st.info("Nenhum caminho disponível em timeseries.")
        options: List[str] = []
        idx = 0
        limit = 300
    else:
        left, right = st.columns([2, 1])
        with left:
            options = [f"{sm} | {p}" for (sm, p) in paths]
            idx = st.selectbox(
                "Métrica",
                options=list(range(len(options))),
                format_func=lambda i: options[i] if options else "",
                index=0,
                key="metric_idx",
            )
        with right:
            limit = st.slider("Máximo de pontos", min_value=50, max_value=2000, value=300, step=50, key="limit_points")

    chart_ph = st.empty()
    caption_ph = st.empty()

    def render_once() -> None:
        # Escolhe a fonte do snapshot mais recente
        latest: Dict[str, Any]
        if source == "REST API":
            data = load_latest_http(api_url)
            if data is None:
                # Unchanged; reuse last snapshot if available
                latest = st.session_state.get("_latest_cache", {})
            else:
                latest = data or {}
                st.session_state["_latest_cache"] = latest
        else:
            latest = load_latest(latest_path)
            st.session_state["_latest_cache"] = latest
        with kpi_ph.container():
            col_metrics(latest)
        # Atualiza as métricas das juntas no mesmo lugar
        jvals = joints_values(latest)
        jlabels = ["JointPosition1", "JointPosition2", "JointPosition3", "JointPosition4"]
        for i, ph in enumerate(joint_ph):
            ph.metric(label=jlabels[i], value=jvals[i])
        if paths:
            sm, ep = paths[idx]
            rows = load_timeseries(db_path, sm, ep, limit)
            with chart_ph.container():
                plot_timeseries(rows)
            caption_ph.caption(f"{sm} · {ep} · {len(rows)} pontos")

        with st.expander("JSON bruto (latest_data.json)"):
            st.json(latest)
    # Loop de atualização contínua (sem recarregar o navegador)
    render_once()
    time.sleep(1.0)
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()
if __name__ == "__main__":
    main()


