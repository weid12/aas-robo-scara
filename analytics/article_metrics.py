# -*- coding: utf-8 -*-
import sys, io
# Força UTF-8 no stdout do Windows para suportar caracteres especiais
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
# ==============================================================================
#   article_metrics.py
#   Coleta e visualiza métricas do sistema AAS SCARA para artigo acadêmico.
#
#   Métricas geradas:
#     1. Latência OPC UA → JSON
#     2. Taxa de coleta (frequência de amostragem real)
#     3. Variação de temperatura vs. ciclos operacionais
#     4. Uptime do sistema
#     5. Throughput da API REST (/api/robot/state/latest)
#     6. Estatísticas descritivas das juntas e temperaturas
#
#   Uso:
#     python analytics/article_metrics.py
#     python analytics/article_metrics.py --output resultados/
#     python analytics/article_metrics.py --api-url http://localhost:5000
#
#   Saída:
#     - Gráficos PNG em --output (padrão: analytics/output/)
#     - Tabela de métricas no terminal e em metrics_summary.csv
# ==============================================================================

import argparse
import json
import os
import sqlite3
import statistics
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos padrão (relativos à raiz do projeto)
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_AAS_DB      = str(_ROOT / "persistence" / "storage" / "aas_history.sqlite3")
DEFAULT_BACKEND_DB  = str(_ROOT / "web" / "backend" / "robot_api" / "aas_robot_scara.db")
DEFAULT_LATEST_JSON = str(_ROOT / "acquisition" / "client" / "latest_data.json")
DEFAULT_OUTPUT_DIR  = str(Path(__file__).parent / "output")
DEFAULT_API_URL     = "http://localhost:5000"

# ---------------------------------------------------------------------------
# Imports opcionais (matplotlib / pandas / requests)
# ---------------------------------------------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("[AVISO] matplotlib não instalado — gráficos desabilitados. Execute: pip install matplotlib")

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("[AVISO] pandas não instalado — algumas análises simplificadas. Execute: pip install pandas")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[AVISO] requests não instalado — métricas de API desabilitadas. Execute: pip install requests")


# ==============================================================================
# MÉTRICA 1: Latência OPC UA → JSON
# ==============================================================================

def metric_latency(latest_json_path: str) -> dict:
    """
    Estima latência entre a captura OPC UA e o timestamp do arquivo latest_data.json.

    Como o cliente injeta RuntimeDiagnostics.CurrentTime (UTC) imediatamente antes
    de escrever o arquivo, a diferença entre o horário atual e o CurrentTime é uma
    aproximação da latência total do ciclo de leitura.
    """
    result = {"metric": "Latência OPC UA → JSON", "unit": "segundos"}
    try:
        with open(latest_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        diag = data.get("RuntimeDiagnostics", {})
        current_time_str = diag.get("CurrentTime")
        if not current_time_str:
            result["error"] = "CurrentTime não encontrado em latest_data.json"
            return result

        current_time = datetime.fromisoformat(current_time_str)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        latency_s = (now_utc - current_time).total_seconds()

        # Ignora leituras com arquivos muito desatualizados (robô offline)
        if latency_s < 0 or latency_s > 3600:
            result["warning"] = f"Arquivo desatualizado ({latency_s:.1f}s). Robô offline?"
        else:
            result["latency_s"] = round(latency_s, 4)
            result["latency_ms"] = round(latency_s * 1000, 2)

        result["current_time"] = current_time_str
        result["measured_at"] = now_utc.isoformat()

    except FileNotFoundError:
        result["error"] = f"Arquivo não encontrado: {latest_json_path}"
    except Exception as e:
        result["error"] = str(e)

    return result


# ==============================================================================
# MÉTRICA 2: Taxa de Coleta (frequência real de amostragem)
# ==============================================================================

def metric_collection_rate(aas_db_path: str, submodel: str = "OperationalData",
                            hours: int = 1) -> dict:
    """
    Calcula a frequência real de amostragem com base no número de registros
    inseridos na tabela timeseries nas últimas `hours` horas.
    """
    result = {"metric": "Taxa de Coleta", "unit": "amostras/segundo", "periodo_h": hours}
    if not Path(aas_db_path).exists():
        result["error"] = f"Banco não encontrado: {aas_db_path}"
        return result

    try:
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with sqlite3.connect(aas_db_path) as conn:
            cur = conn.execute(
                """
                SELECT COUNT(*) as total,
                       MIN(created_at) as first_ts,
                       MAX(created_at) as last_ts
                FROM timeseries
                WHERE submodel_name = ? AND created_at >= ?
                """,
                (submodel, since),
            )
            row = cur.fetchone()

        if not row or row[0] == 0:
            result["warning"] = "Nenhum registro encontrado no período especificado"
            return result

        total, first_ts, last_ts = row
        t_first = datetime.fromisoformat(first_ts)
        t_last  = datetime.fromisoformat(last_ts)
        elapsed_s = max((t_last - t_first).total_seconds(), 1)

        # Número de timestamps únicos = número real de ciclos de leitura
        cur2 = conn.execute(
            "SELECT COUNT(DISTINCT created_at) FROM timeseries WHERE submodel_name = ? AND created_at >= ?",
            (submodel, since),
        ) if False else None  # evita reabrir conexão fechada

        with sqlite3.connect(aas_db_path) as conn2:
            cur2 = conn2.execute(
                "SELECT COUNT(DISTINCT created_at) FROM timeseries WHERE submodel_name = ? AND created_at >= ?",
                (submodel, since),
            )
            unique_cycles = cur2.fetchone()[0]

        rate_hz = round(unique_cycles / elapsed_s, 4)
        interval_s = round(elapsed_s / unique_cycles, 4) if unique_cycles > 0 else None

        result.update({
            "total_registros": total,
            "ciclos_unicos": unique_cycles,
            "elapsed_s": round(elapsed_s, 2),
            "taxa_hz": rate_hz,
            "intervalo_medio_s": interval_s,
            "periodo_inicio": first_ts,
            "periodo_fim": last_ts,
        })

    except Exception as e:
        result["error"] = str(e)

    return result


# ==============================================================================
# MÉTRICA 3: Variação de Temperatura vs. Ciclos Operacionais
# ==============================================================================

def metric_temperature_vs_cycles(aas_db_path: str, limit: int = 500,
                                  output_dir: str = DEFAULT_OUTPUT_DIR) -> dict:
    """
    Correlaciona temperatura dos eixos com o contador de operação ao longo do tempo.
    Gera gráfico temperatura × tempo com marcações de status se disponíveis.
    """
    result = {"metric": "Temperatura vs. Ciclos", "grafico": None}
    if not Path(aas_db_path).exists():
        result["error"] = f"Banco não encontrado: {aas_db_path}"
        return result

    probes = [
        "TemperatureData.motorProbe1_temp",
        "TemperatureData.motorProbe2_temp",
        "TemperatureData.motorProbe3_temp",
        "TemperatureData.motorProbe4_temp",
        "TemperatureData.IWtemperature",
    ]

    try:
        with sqlite3.connect(aas_db_path) as conn:
            series = {}
            for probe in probes:
                sm, path = probe.split(".", 1)
                cur = conn.execute(
                    """
                    SELECT created_at, value FROM timeseries
                    WHERE submodel_name = ? AND element_path = ?
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (sm, probe, limit),
                )
                rows = cur.fetchall()
                if rows:
                    series[probe.split(".")[-1]] = [
                        (datetime.fromisoformat(r[0]), r[1]) for r in reversed(rows)
                    ]

        if not series:
            result["warning"] = "Sem dados de temperatura no banco AAS"
            return result

        # Estatísticas descritivas
        stats = {}
        for name, pts in series.items():
            vals = [v for _, v in pts if v is not None]
            if vals:
                stats[name] = {
                    "n": len(vals),
                    "mean": round(statistics.mean(vals), 2),
                    "stdev": round(statistics.stdev(vals), 2) if len(vals) > 1 else 0,
                    "min": round(min(vals), 2),
                    "max": round(max(vals), 2),
                }
        result["estatisticas"] = stats

        # Gráfico
        if HAS_MATPLOTLIB:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            fig, ax = plt.subplots(figsize=(12, 5))
            colors = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db"]
            for i, (name, pts) in enumerate(series.items()):
                times = [t for t, _ in pts]
                vals  = [v for _, v in pts]
                ax.plot(times, vals, label=name, linewidth=1.5, color=colors[i % len(colors)])

            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            fig.autofmt_xdate()
            ax.set_xlabel("Tempo")
            ax.set_ylabel("Temperatura (°C)")
            ax.set_title("Variação de Temperatura dos Eixos do Robô SCARA")
            ax.legend(loc="upper left")
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            out = str(Path(output_dir) / "temperatura_vs_tempo.png")
            fig.savefig(out, dpi=150)
            plt.close(fig)
            result["grafico"] = out
            print(f"  [OK] Gráfico salvo: {out}")

    except Exception as e:
        result["error"] = str(e)

    return result


# ==============================================================================
# MÉTRICA 4: Uptime do Sistema
# ==============================================================================

def metric_uptime(latest_json_path: str) -> dict:
    """
    Calcula o uptime do cliente OPC UA usando RuntimeDiagnostics.StartTime
    e RuntimeDiagnostics.CurrentTime do arquivo latest_data.json.
    """
    result = {"metric": "Uptime do Sistema", "unit": "segundos"}
    try:
        with open(latest_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        diag = data.get("RuntimeDiagnostics", {})
        start_str   = diag.get("StartTime")
        current_str = diag.get("CurrentTime")

        if not start_str or not current_str:
            result["error"] = "StartTime ou CurrentTime ausentes em latest_data.json"
            return result

        def parse_dt(s):
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.astimezone()
            return dt

        start_dt   = parse_dt(start_str)
        current_dt = parse_dt(current_str)
        uptime_s   = max((current_dt - start_dt).total_seconds(), 0)

        hours, rem = divmod(int(uptime_s), 3600)
        minutes, seconds = divmod(rem, 60)

        result.update({
            "start_time": start_str,
            "current_time": current_str,
            "uptime_s": round(uptime_s, 2),
            "uptime_formatado": f"{hours}h {minutes}m {seconds}s",
        })

    except FileNotFoundError:
        result["error"] = f"Arquivo não encontrado: {latest_json_path}"
    except Exception as e:
        result["error"] = str(e)

    return result


# ==============================================================================
# MÉTRICA 5: Throughput da API REST
# ==============================================================================

def metric_api_throughput(api_url: str, endpoint: str = "/api/robot/state/latest",
                           n_requests: int = 20) -> dict:
    """
    Mede latência e throughput do endpoint de estado mais recente.
    Faz N requisições sequenciais e calcula estatísticas de tempo de resposta.
    """
    result = {"metric": "Throughput API REST", "endpoint": endpoint, "n_requisicoes": n_requests}
    if not HAS_REQUESTS:
        result["error"] = "Biblioteca requests não instalada"
        return result

    url = api_url.rstrip("/") + endpoint
    latencies = []

    print(f"  Testando {n_requests} requisições para {url} ...")
    for i in range(n_requests):
        try:
            t0 = time.perf_counter()
            resp = requests.get(url, timeout=5)
            elapsed = (time.perf_counter() - t0) * 1000  # ms
            if resp.status_code == 200:
                latencies.append(elapsed)
            else:
                print(f"  [WARN] Requisição {i+1}: HTTP {resp.status_code}")
        except requests.exceptions.ConnectionError:
            result["error"] = f"Não foi possível conectar a {url}. Backend está rodando?"
            return result
        except Exception as e:
            print(f"  [WARN] Requisição {i+1} falhou: {e}")

    if not latencies:
        result["error"] = "Nenhuma requisição bem-sucedida"
        return result

    result.update({
        "requisicoes_ok": len(latencies),
        "latencia_media_ms": round(statistics.mean(latencies), 2),
        "latencia_min_ms": round(min(latencies), 2),
        "latencia_max_ms": round(max(latencies), 2),
        "latencia_stdev_ms": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0,
        "throughput_rps": round(len(latencies) / (sum(latencies) / 1000), 2),
    })

    return result


# ==============================================================================
# MÉTRICA 6: Estatísticas Descritivas — Juntas e Temperaturas
# ==============================================================================

def metric_descriptive_stats(aas_db_path: str, limit: int = 1000,
                              output_dir: str = DEFAULT_OUTPUT_DIR) -> dict:
    """
    Estatísticas descritivas das posições das juntas e temperaturas.
    Gera box plots e histogramas para uso em artigo.
    """
    result = {"metric": "Estatísticas Descritivas", "graficos": []}
    if not Path(aas_db_path).exists():
        result["error"] = f"Banco não encontrado: {aas_db_path}"
        return result

    targets = {
        "J1 (°)":   ("OperationalData", "OperationalData.JointPosition1"),
        "J2 (°)":   ("OperationalData", "OperationalData.JointPosition2"),
        "J3 (mm)":  ("OperationalData", "OperationalData.JointPosition3"),
        "J4 (°)":   ("OperationalData", "OperationalData.JointPosition4"),
        "Probe1 (°C)": ("TemperatureData", "TemperatureData.motorProbe1_temp"),
        "Probe2 (°C)": ("TemperatureData", "TemperatureData.motorProbe2_temp"),
        "Probe3 (°C)": ("TemperatureData", "TemperatureData.motorProbe3_temp"),
        "Probe4 (°C)": ("TemperatureData", "TemperatureData.motorProbe4_temp"),
    }

    data_collected = {}
    try:
        with sqlite3.connect(aas_db_path) as conn:
            for label, (sm, path) in targets.items():
                cur = conn.execute(
                    """
                    SELECT value FROM timeseries
                    WHERE submodel_name = ? AND element_path = ?
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (sm, path, limit),
                )
                vals = [r[0] for r in cur.fetchall() if r[0] is not None]
                if vals:
                    data_collected[label] = vals

        if not data_collected:
            result["warning"] = "Sem dados de posição/temperatura no banco AAS"
            return result

        # Estatísticas
        stats = {}
        for label, vals in data_collected.items():
            stats[label] = {
                "n": len(vals),
                "mean": round(statistics.mean(vals), 3),
                "stdev": round(statistics.stdev(vals), 3) if len(vals) > 1 else 0,
                "min": round(min(vals), 3),
                "median": round(statistics.median(vals), 3),
                "max": round(max(vals), 3),
            }
        result["estatisticas"] = stats

        if HAS_MATPLOTLIB:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            # Box Plot — Juntas
            joint_labels = [k for k in data_collected if k.startswith("J")]
            joint_data   = [data_collected[k] for k in joint_labels]
            if joint_data:
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.boxplot(joint_data, labels=joint_labels, patch_artist=True,
                           boxprops=dict(facecolor="#3498db", alpha=0.6),
                           medianprops=dict(color="#e74c3c", linewidth=2))
                ax.set_title("Distribuição de Posição das Juntas — Robô SCARA")
                ax.set_ylabel("Posição")
                ax.grid(True, axis="y", alpha=0.3)
                plt.tight_layout()
                out = str(Path(output_dir) / "boxplot_juntas.png")
                fig.savefig(out, dpi=150)
                plt.close(fig)
                result["graficos"].append(out)
                print(f"  [OK] Gráfico salvo: {out}")

            # Box Plot — Temperaturas
            temp_labels = [k for k in data_collected if "Probe" in k or "°C" in k]
            temp_data   = [data_collected[k] for k in temp_labels]
            if temp_data:
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.boxplot(temp_data, labels=temp_labels, patch_artist=True,
                           boxprops=dict(facecolor="#e74c3c", alpha=0.6),
                           medianprops=dict(color="#2c3e50", linewidth=2))
                ax.set_title("Distribuição de Temperatura por Eixo — Robô SCARA")
                ax.set_ylabel("Temperatura (°C)")
                ax.grid(True, axis="y", alpha=0.3)
                plt.tight_layout()
                out = str(Path(output_dir) / "boxplot_temperaturas.png")
                fig.savefig(out, dpi=150)
                plt.close(fig)
                result["graficos"].append(out)
                print(f"  [OK] Gráfico salvo: {out}")

            # Histograma — Temperatura Probe1
            if "Probe1 (°C)" in data_collected:
                vals = data_collected["Probe1 (°C)"]
                fig, ax = plt.subplots(figsize=(7, 4))
                ax.hist(vals, bins=20, color="#e74c3c", alpha=0.75, edgecolor="white")
                ax.axvline(statistics.mean(vals), color="#2c3e50", linestyle="--",
                           linewidth=1.5, label=f"Média: {statistics.mean(vals):.1f}°C")
                ax.set_title("Histograma — Temperatura Eixo 1 (motorProbe1)")
                ax.set_xlabel("Temperatura (°C)")
                ax.set_ylabel("Frequência")
                ax.legend()
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                out = str(Path(output_dir) / "histograma_probe1.png")
                fig.savefig(out, dpi=150)
                plt.close(fig)
                result["graficos"].append(out)
                print(f"  [OK] Gráfico salvo: {out}")

    except Exception as e:
        result["error"] = str(e)

    return result


# ==============================================================================
# Exportar resumo CSV
# ==============================================================================

def export_summary_csv(all_results: list, output_dir: str) -> str:
    """Exporta tabela de métricas para CSV."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    csv_path = str(Path(output_dir) / "metrics_summary.csv")

    rows = []
    for r in all_results:
        metric = r.get("metric", "?")
        for k, v in r.items():
            if k in ("metric", "grafico", "graficos"):
                continue
            if isinstance(v, (str, int, float)):
                rows.append({"metrica": metric, "chave": k, "valor": v})
            elif isinstance(v, dict):
                for kk, vv in v.items():
                    if isinstance(vv, (str, int, float)):
                        rows.append({"metrica": f"{metric} → {k}", "chave": kk, "valor": vv})

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        f.write("metrica,chave,valor\n")
        for row in rows:
            f.write(f"{row['metrica']},{row['chave']},{row['valor']}\n")

    return csv_path


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Coleta métricas do sistema AAS SCARA para artigo acadêmico"
    )
    parser.add_argument("--aas-db",     default=DEFAULT_AAS_DB,      help="Caminho do aas_history.sqlite3")
    parser.add_argument("--backend-db", default=DEFAULT_BACKEND_DB,   help="Caminho do aas_robot_scara.db")
    parser.add_argument("--latest",     default=DEFAULT_LATEST_JSON,  help="Caminho do latest_data.json")
    parser.add_argument("--output",     default=DEFAULT_OUTPUT_DIR,   help="Diretório de saída para gráficos")
    parser.add_argument("--api-url",    default=DEFAULT_API_URL,      help="URL base do backend")
    parser.add_argument("--api-calls",  type=int, default=20,         help="Número de chamadas para teste de throughput")
    parser.add_argument("--limit",      type=int, default=500,        help="Máximo de registros por consulta")
    parser.add_argument("--hours",      type=int, default=1,          help="Janela de tempo para taxa de coleta (horas)")
    args = parser.parse_args()

    sep = "=" * 65
    print(f"\n{sep}")
    print("  METRICAS DO SISTEMA AAS SCARA - ARTIGO ACADEMICO")
    print(f"{sep}\n")

    all_results = []

    # 1. Latencia OPC UA -> JSON
    print("[ 1/6 ] Latencia OPC UA -> JSON")
    r1 = metric_latency(args.latest)
    all_results.append(r1)
    if "error" in r1:
        print(f"  [ERRO] {r1['error']}")
    elif "warning" in r1:
        print(f"  [AVISO] {r1['warning']}")
    else:
        print(f"  Latência atual : {r1.get('latency_ms')} ms  ({r1.get('latency_s')} s)")

    print()

    # 2. Taxa de coleta
    print(f"[ 2/6 ] Taxa de Coleta (ultimas {args.hours}h)")
    r2 = metric_collection_rate(args.aas_db, hours=args.hours)
    all_results.append(r2)
    if "error" in r2:
        print(f"  [ERRO] {r2['error']}")
    elif "warning" in r2:
        print(f"  [AVISO] {r2['warning']}")
    else:
        print(f"  Ciclos únicos  : {r2.get('ciclos_unicos')}")
        print(f"  Período        : {r2.get('elapsed_s')} s")
        print(f"  Taxa real      : {r2.get('taxa_hz')} Hz  (intervalo medio: {r2.get('intervalo_medio_s')} s)")

    print()

    # 3. Temperatura vs. Ciclos
    print("[ 3/6 ] Variação de Temperatura vs. Tempo")
    r3 = metric_temperature_vs_cycles(args.aas_db, limit=args.limit, output_dir=args.output)
    all_results.append(r3)
    if "error" in r3:
        print(f"  [ERRO] {r3['error']}")
    elif "warning" in r3:
        print(f"  [AVISO] {r3['warning']}")
    else:
        for probe, s in (r3.get("estatisticas") or {}).items():
            print(f"  {probe:<20}  media={s['mean']}C  std={s['stdev']}C  [{s['min']}-{s['max']}]")

    print()

    # 4. Uptime
    print("[ 4/6 ] Uptime do Sistema")
    r4 = metric_uptime(args.latest)
    all_results.append(r4)
    if "error" in r4:
        print(f"  [ERRO] {r4['error']}")
    else:
        print(f"  Início         : {r4.get('start_time')}")
        print(f"  Uptime         : {r4.get('uptime_formatado')}  ({r4.get('uptime_s')} s)")

    print()

    # 5. Throughput da API
    print(f"[ 5/6 ] Throughput da API REST ({args.api_calls} requisições)")
    r5 = metric_api_throughput(args.api_url, n_requests=args.api_calls)
    all_results.append(r5)
    if "error" in r5:
        print(f"  [ERRO] {r5['error']}")
    else:
        print(f"  Requisições OK : {r5.get('requisicoes_ok')}/{args.api_calls}")
        print(f"  Latência média : {r5.get('latencia_media_ms')} ms")
        print(f"  Latencia       : min={r5.get('latencia_min_ms')} ms  max={r5.get('latencia_max_ms')} ms  std={r5.get('latencia_stdev_ms')} ms")
        print(f"  Throughput     : {r5.get('throughput_rps')} req/s")

    print()

    # 6. Estatísticas Descritivas
    print("[ 6/6 ] Estatisticas Descritivas - Juntas e Temperaturas")
    r6 = metric_descriptive_stats(args.aas_db, limit=args.limit, output_dir=args.output)
    all_results.append(r6)
    if "error" in r6:
        print(f"  [ERRO] {r6['error']}")
    elif "warning" in r6:
        print(f"  [AVISO] {r6['warning']}")
    else:
        print(f"  {'Variavel':<16} {'N':>6} {'Media':>10} {'Std':>8} {'Min':>8} {'Mediana':>8} {'Max':>8}")
        print("  " + "-" * 68)
        for label, s in (r6.get("estatisticas") or {}).items():
            print(f"  {label:<16} {s['n']:>6} {s['mean']:>10} {s['stdev']:>8} {s['min']:>8} {s['median']:>8} {s['max']:>8}")

    print()

    # Exportar CSV
    csv_path = export_summary_csv(all_results, args.output)
    print(f"\n{sep}")
    print(f"  Resumo exportado para: {csv_path}")
    if HAS_MATPLOTLIB:
        print(f"  Gráficos salvos em:    {args.output}/")
    print(f"{sep}\n")


if __name__ == "__main__":
    main()
