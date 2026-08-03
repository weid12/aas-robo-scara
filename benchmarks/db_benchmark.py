# ==================================================================================================
#   Benchmark de Persistência Histórica — AAS Robô SCARA
#
#   Quantifica:
#   1. Período de aquisição dos registros (intervalo entre inserções)
#   2. Taxa de inserção (registros/s)
#   3. Tamanho do banco em disco
#   4. Latência das consultas (views da API)
#
#   Uso:
#       python benchmarks/db_benchmark.py
#       python benchmarks/db_benchmark.py --db persistence/storage/aas_history.sqlite3
#       python benchmarks/db_benchmark.py --output benchmarks/results/
#
#   Requisitos:
#       pip install numpy requests
# ==================================================================================================

import argparse
import json
import os
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Diretório raiz do projeto
ROOT_DIR = Path(__file__).resolve().parents[1]

# Caminhos padrão dos bancos
DEFAULT_AAS_DB = str(ROOT_DIR / "persistence" / "storage" / "aas_history.sqlite3")
DEFAULT_BACKEND_DB = str(ROOT_DIR / "web" / "backend" / "robot_api" / "aas_robot_scara.db")

import logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_benchmark")


# ─── Data Classes ────────────────────────────────────────────────────────────────

@dataclass
class AcquisitionPeriodStats:
    """Estatísticas do período entre inserções."""
    n_records: int = 0
    n_intervals: int = 0
    interval_mean_s: float = 0.0
    interval_std_s: float = 0.0
    interval_median_s: float = 0.0
    interval_min_s: float = 0.0
    interval_max_s: float = 0.0
    interval_p95_s: float = 0.0
    interval_p99_s: float = 0.0
    first_record: str = ""
    last_record: str = ""
    total_duration_s: float = 0.0


@dataclass
class InsertionRateStats:
    """Estatísticas da taxa de inserção."""
    total_records: int = 0
    total_duration_s: float = 0.0
    rate_records_per_s: float = 0.0
    rate_snapshots_per_s: float = 0.0
    tables: Dict[str, int] = field(default_factory=dict)


@dataclass
class DatabaseSizeStats:
    """Tamanho do banco em disco."""
    path: str = ""
    size_bytes: int = 0
    size_kb: float = 0.0
    size_mb: float = 0.0
    page_size: int = 0
    page_count: int = 0
    freelist_count: int = 0
    tables: Dict[str, int] = field(default_factory=dict)


@dataclass
class QueryLatencyStats:
    """Latência de uma consulta específica."""
    query_name: str = ""
    query_description: str = ""
    n_executions: int = 0
    latency_mean_ms: float = 0.0
    latency_std_ms: float = 0.0
    latency_median_ms: float = 0.0
    latency_min_ms: float = 0.0
    latency_max_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    rows_returned: int = 0


@dataclass
class DbBenchmarkResults:
    """Resultado completo do benchmark de banco de dados."""
    metadata: Dict[str, Any] = field(default_factory=dict)
    acquisition_period: Optional[AcquisitionPeriodStats] = None
    insertion_rate: Optional[InsertionRateStats] = None
    database_size: Optional[DatabaseSizeStats] = None
    query_latencies: List[QueryLatencyStats] = field(default_factory=list)


# ─── 1. Período de Aquisição ─────────────────────────────────────────────────────

def measure_acquisition_period(db_path: str) -> AcquisitionPeriodStats:
    """
    Analisa o intervalo entre registros consecutivos na tabela timeseries.
    Mede o período real de aquisição (tempo entre inserções no banco).
    """
    stats = AcquisitionPeriodStats()

    if not Path(db_path).exists():
        logger.warning("Banco não encontrado: %s", db_path)
        return stats

    con = sqlite3.connect(db_path)
    try:
        # Detecta qual tabela de timestamps usar
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        if "timeseries" in tables:
            cur = con.execute(
                "SELECT DISTINCT created_at FROM timeseries ORDER BY created_at ASC"
            )
        elif "submodel_snapshots_json" in tables:
            cur = con.execute(
                "SELECT DISTINCT created_at FROM submodel_snapshots_json ORDER BY created_at ASC"
            )
        elif "robot_states" in tables or "robot_state" in tables:
            tbl = "robot_states" if "robot_states" in tables else "robot_state"
            cur = con.execute(
                f"SELECT DISTINCT timestamp FROM [{tbl}] ORDER BY timestamp ASC"
            )
        else:
            logger.warning("Nenhuma tabela de séries temporais encontrada no banco")
            return stats

        timestamps = [row[0] for row in cur.fetchall()]
    finally:
        con.close()

    if len(timestamps) < 2:
        logger.warning("Menos de 2 timestamps encontrados no banco")
        stats.n_records = len(timestamps)
        return stats

    # Converte para epoch
    epochs = []
    for ts in timestamps:
        try:
            dt = datetime.fromisoformat(ts)
            epochs.append(dt.timestamp())
        except Exception:
            continue

    if len(epochs) < 2:
        return stats

    # Calcula intervalos entre registros consecutivos
    intervals = np.diff(epochs)

    # Remove intervalos negativos ou zerados (anomalias)
    intervals = intervals[intervals > 0]

    if len(intervals) == 0:
        return stats

    stats.n_records = len(epochs)
    stats.n_intervals = len(intervals)
    stats.interval_mean_s = float(np.mean(intervals))
    stats.interval_std_s = float(np.std(intervals))
    stats.interval_median_s = float(np.median(intervals))
    stats.interval_min_s = float(np.min(intervals))
    stats.interval_max_s = float(np.max(intervals))
    stats.interval_p95_s = float(np.percentile(intervals, 95))
    stats.interval_p99_s = float(np.percentile(intervals, 99))
    stats.first_record = timestamps[0]
    stats.last_record = timestamps[-1]
    stats.total_duration_s = epochs[-1] - epochs[0]

    logger.info(
        "Período de aquisição: %.3f ± %.3f s (mediana: %.3f s, N=%d)",
        stats.interval_mean_s, stats.interval_std_s,
        stats.interval_median_s, stats.n_intervals
    )

    return stats


# ─── 2. Taxa de Inserção ─────────────────────────────────────────────────────────

def measure_insertion_rate(db_path: str) -> InsertionRateStats:
    """
    Calcula a taxa de inserção efetiva (registros/s) para cada tabela.
    """
    stats = InsertionRateStats()

    if not Path(db_path).exists():
        return stats

    con = sqlite3.connect(db_path)
    try:
        # Detecta tabelas disponíveis
        all_tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        # Conta registros em cada tabela conhecida
        tables = {}
        for table in ["submodel_snapshots_json", "submodel_snapshots", "timeseries", "robot_states", "robot_state"]:
            if table in all_tables:
                try:
                    cur = con.execute(f"SELECT COUNT(*) FROM {table}")
                    tables[table] = cur.fetchone()[0]
                except sqlite3.OperationalError:
                    pass

        stats.tables = tables
        stats.total_records = sum(tables.values())

        # Calcula duração total a partir da tabela mais adequada
        try:
            if "timeseries" in all_tables:
                cur = con.execute(
                    "SELECT MIN(created_at), MAX(created_at) FROM timeseries"
                )
            elif "submodel_snapshots_json" in all_tables:
                cur = con.execute(
                    "SELECT MIN(created_at), MAX(created_at) FROM submodel_snapshots_json"
                )
            elif "robot_states" in all_tables or "robot_state" in all_tables:
                tbl = "robot_states" if "robot_states" in all_tables else "robot_state"
                cur = con.execute(
                    f"SELECT MIN(timestamp), MAX(timestamp) FROM [{tbl}]"
                )
            else:
                cur = None

            if cur:
                row = cur.fetchone()
                if row and row[0] and row[1]:
                    t_min = datetime.fromisoformat(row[0]).timestamp()
                    t_max = datetime.fromisoformat(row[1]).timestamp()
                    stats.total_duration_s = t_max - t_min

                    if stats.total_duration_s > 0:
                        stats.rate_records_per_s = (
                            stats.total_records / stats.total_duration_s
                        )
                        json_count = tables.get("submodel_snapshots_json", 0)
                        stats.rate_snapshots_per_s = (
                            json_count / stats.total_duration_s
                        )
        except Exception as e:
            logger.warning("Erro ao calcular duração: %s", e)
    finally:
        con.close()

    logger.info(
        "Taxa de inserção: %.2f reg/s | snapshots: %.2f/s | total: %d registros",
        stats.rate_records_per_s, stats.rate_snapshots_per_s, stats.total_records
    )

    return stats


# ─── 3. Tamanho do Banco em Disco ────────────────────────────────────────────────

def measure_database_size(db_path: str) -> DatabaseSizeStats:
    """
    Mede o tamanho do banco de dados em disco e detalhes internos do SQLite.
    """
    stats = DatabaseSizeStats()
    stats.path = db_path

    p = Path(db_path)
    if not p.exists():
        logger.warning("Banco não encontrado: %s", db_path)
        return stats

    stats.size_bytes = p.stat().st_size
    stats.size_kb = stats.size_bytes / 1024
    stats.size_mb = stats.size_bytes / (1024 * 1024)

    con = sqlite3.connect(db_path)
    try:
        # PRAGMA para detalhes internos
        stats.page_size = con.execute("PRAGMA page_size").fetchone()[0]
        stats.page_count = con.execute("PRAGMA page_count").fetchone()[0]
        stats.freelist_count = con.execute("PRAGMA freelist_count").fetchone()[0]

        # Detecta e conta registros por tabela
        all_tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        for table in all_tables:
            if not table.startswith("sqlite_"):
                try:
                    cur = con.execute(f"SELECT COUNT(*) FROM [{table}]")
                    stats.tables[table] = cur.fetchone()[0]
                except sqlite3.OperationalError:
                    stats.tables[table] = 0
    finally:
        con.close()

    logger.info(
        "Tamanho do banco: %.2f MB (%d bytes) | pages: %d × %d bytes",
        stats.size_mb, stats.size_bytes, stats.page_count, stats.page_size
    )

    return stats


# ─── 4. Latência das Consultas (Views) ───────────────────────────────────────────

def _benchmark_query(
    con: sqlite3.Connection,
    query_name: str,
    description: str,
    sql: str,
    params: tuple = (),
    n_executions: int = 100,
) -> QueryLatencyStats:
    """
    Executa uma consulta SQL N vezes e mede a latência de cada execução.
    """
    stats = QueryLatencyStats()
    stats.query_name = query_name
    stats.query_description = description
    stats.n_executions = n_executions

    latencies = []
    rows_returned = 0

    for i in range(n_executions):
        t_start = time.perf_counter()
        cur = con.execute(sql, params)
        rows = cur.fetchall()
        t_end = time.perf_counter()

        latency_ms = (t_end - t_start) * 1000
        latencies.append(latency_ms)

        if i == 0:
            rows_returned = len(rows)

    arr = np.array(latencies)
    stats.latency_mean_ms = float(np.mean(arr))
    stats.latency_std_ms = float(np.std(arr))
    stats.latency_median_ms = float(np.median(arr))
    stats.latency_min_ms = float(np.min(arr))
    stats.latency_max_ms = float(np.max(arr))
    stats.latency_p95_ms = float(np.percentile(arr, 95))
    stats.latency_p99_ms = float(np.percentile(arr, 99))
    stats.rows_returned = rows_returned

    logger.info(
        "  [%s] %.3f ± %.3f ms (p95: %.3f, p99: %.3f, max: %.3f) | %d rows",
        query_name, stats.latency_mean_ms, stats.latency_std_ms,
        stats.latency_p95_ms, stats.latency_p99_ms, stats.latency_max_ms,
        rows_returned
    )

    return stats


def measure_query_latencies(
    db_path: str, n_executions: int = 100
) -> List[QueryLatencyStats]:
    """
    Mede a latência das principais consultas/views do sistema.

    Consultas testadas:
    1. latest_snapshot: Último snapshot JSON (simula /state/latest)
    2. history_50: Últimos 50 snapshots (simula /state/history?limit=50)
    3. history_500: Últimos 500 snapshots (carga máxima da API)
    4. timeseries_1h: Série temporal de 1 variável na última hora
    5. timeseries_24h: Série temporal de 1 variável nas últimas 24h
    6. summary_today: Agregação de métricas do dia (simula /metrics/summary)
    7. count_all: Contagem total de registros (monitoramento)
    """
    results: List[QueryLatencyStats] = []

    if not Path(db_path).exists():
        logger.warning("Banco não encontrado: %s", db_path)
        return results

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL")  # Mesmo modo usado em produção
    con.execute("PRAGMA cache_size=-8000")  # 8 MB cache

    logger.info("Medindo latência de consultas (%d execuções cada):", n_executions)

    # Detecta tabelas disponíveis
    all_tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]

    try:
        # ── Consultas para schema AAS (persistence/storage) ──
        if "submodel_snapshots_json" in all_tables:
            # 1. Último snapshot (simula GET /state/latest)
            results.append(_benchmark_query(
                con, "latest_snapshot",
                "Último snapshot JSON completo (GET /state/latest)",
                """SELECT data FROM submodel_snapshots_json
                   WHERE submodel_name = 'OperationalData'
                   ORDER BY created_at DESC LIMIT 1""",
                n_executions=n_executions,
            ))

            # 2. Histórico 50 registros (simula GET /state/history?limit=50)
            results.append(_benchmark_query(
                con, "history_50",
                "Últimos 50 snapshots (GET /state/history?limit=50)",
                """SELECT * FROM submodel_snapshots_json
                   ORDER BY created_at DESC LIMIT 50""",
                n_executions=n_executions,
            ))

            # 3. Histórico 500 registros (carga máxima da API)
            results.append(_benchmark_query(
                con, "history_500",
                "Últimos 500 snapshots (carga máxima da API)",
                """SELECT * FROM submodel_snapshots_json
                   ORDER BY created_at DESC LIMIT 500""",
                n_executions=n_executions,
            ))

        if "timeseries" in all_tables:
            # 4. Série temporal 1h (um elemento específico)
            results.append(_benchmark_query(
                con, "timeseries_1h",
                "Série temporal de motorProbe1_temp na última hora",
                """SELECT created_at, value FROM timeseries
                   WHERE element_path = 'TemperatureData.motorProbe1_temp'
                   AND created_at >= datetime('now', '-1 hour')
                   ORDER BY created_at ASC""",
                n_executions=n_executions,
            ))

            # 5. Série temporal 24h
            results.append(_benchmark_query(
                con, "timeseries_24h",
                "Série temporal de motorProbe1_temp nas últimas 24h",
                """SELECT created_at, value FROM timeseries
                   WHERE element_path = 'TemperatureData.motorProbe1_temp'
                   AND created_at >= datetime('now', '-24 hours')
                   ORDER BY created_at ASC""",
                n_executions=n_executions,
            ))

        if "submodel_snapshots" in all_tables:
            # 6. Agregação diária (simula /metrics/summary)
            results.append(_benchmark_query(
                con, "summary_today",
                "Contagem e agregação de hoje (GET /metrics/summary)",
                """SELECT submodel_name, COUNT(*), AVG(value_num)
                   FROM submodel_snapshots
                   WHERE created_at >= date('now')
                   GROUP BY submodel_name""",
                n_executions=n_executions,
            ))

            # 8. Busca por elemento específico (filtro composto)
            results.append(_benchmark_query(
                con, "filter_element",
                "Busca por elemento específico com filtro submodel+idshort",
                """SELECT value_num, created_at FROM submodel_snapshots
                   WHERE submodel_name = 'TemperatureData'
                   AND idshort = 'TemperatureData.motorProbe1_temp'
                   ORDER BY created_at DESC LIMIT 100""",
                n_executions=n_executions,
            ))

        # ── Consultas para schema backend (robot_states / robot_state) ──
        robot_tbl = None
        if "robot_states" in all_tables:
            robot_tbl = "robot_states"
        elif "robot_state" in all_tables:
            robot_tbl = "robot_state"

        if robot_tbl:
            results.append(_benchmark_query(
                con, "latest_robot_state",
                f"Último estado do robô ({robot_tbl} ORDER BY timestamp DESC)",
                f"""SELECT * FROM [{robot_tbl}]
                   ORDER BY timestamp DESC LIMIT 1""",
                n_executions=n_executions,
            ))

            results.append(_benchmark_query(
                con, "history_robot_50",
                "Últimos 50 estados do robô",
                f"""SELECT * FROM [{robot_tbl}]
                   ORDER BY timestamp DESC LIMIT 50""",
                n_executions=n_executions,
            ))

            results.append(_benchmark_query(
                con, "history_robot_500",
                "Últimos 500 estados do robô",
                f"""SELECT * FROM [{robot_tbl}]
                   ORDER BY timestamp DESC LIMIT 500""",
                n_executions=n_executions,
            ))

        # 7. Contagem total (monitoramento de crescimento) — genérico
        count_parts = []
        for t in all_tables:
            if not t.startswith("sqlite_"):
                count_parts.append(f"(SELECT COUNT(*) FROM [{t}]) as [{t}_count]")
        if count_parts:
            results.append(_benchmark_query(
                con, "count_all",
                "Contagem total de registros em todas as tabelas",
                f"SELECT {', '.join(count_parts)}",
                n_executions=n_executions,
            ))

    finally:
        con.close()

    return results


# ─── 5. Benchmark da API HTTP (latência fim-a-fim com rede) ──────────────────────

def measure_api_latencies(
    base_url: str = "http://localhost:5000",
    n_executions: int = 50,
) -> List[QueryLatencyStats]:
    """
    Mede latência das views HTTP da API (inclui overhead de rede + serialização).
    Requer que o backend esteja rodando.
    """
    results: List[QueryLatencyStats] = []

    try:
        import requests
    except ImportError:
        logger.warning("Módulo 'requests' não disponível. Pulando benchmark de API HTTP.")
        return results

    endpoints = [
        ("api_latest", "GET /api/robot/state/latest", "/api/robot/state/latest"),
        ("api_history_50", "GET /api/robot/state/history?limit=50", "/api/robot/state/history?limit=50"),
        ("api_summary", "GET /api/robot/metrics/summary", "/api/robot/metrics/summary"),
        ("api_health", "GET /api/robot/health", "/api/robot/health"),
    ]

    logger.info("Medindo latência da API HTTP (%d execuções cada):", n_executions)

    for name, description, path in endpoints:
        url = f"{base_url}{path}"
        latencies = []
        rows_returned = 0

        for i in range(n_executions):
            try:
                t_start = time.perf_counter()
                resp = requests.get(url, timeout=5)
                t_end = time.perf_counter()

                latency_ms = (t_end - t_start) * 1000
                latencies.append(latency_ms)

                if i == 0 and resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        rows_returned = len(data)
                    else:
                        rows_returned = 1
            except requests.exceptions.ConnectionError:
                if i == 0:
                    logger.warning("  [%s] Backend não acessível em %s", name, url)
                break
            except Exception as e:
                logger.debug("  [%s] Erro: %s", name, e)
                break

        if not latencies:
            continue

        arr = np.array(latencies)
        stats = QueryLatencyStats(
            query_name=name,
            query_description=description,
            n_executions=len(latencies),
            latency_mean_ms=float(np.mean(arr)),
            latency_std_ms=float(np.std(arr)),
            latency_median_ms=float(np.median(arr)),
            latency_min_ms=float(np.min(arr)),
            latency_max_ms=float(np.max(arr)),
            latency_p95_ms=float(np.percentile(arr, 95)),
            latency_p99_ms=float(np.percentile(arr, 99)),
            rows_returned=rows_returned,
        )
        results.append(stats)

        logger.info(
            "  [%s] %.2f ± %.2f ms (p95: %.2f, max: %.2f) | %d rows",
            name, stats.latency_mean_ms, stats.latency_std_ms,
            stats.latency_p95_ms, stats.latency_max_ms, rows_returned
        )

    return results


# ─── Relatório ────────────────────────────────────────────────────────────────────

def print_report(results: DbBenchmarkResults) -> str:
    """Gera relatório formatado."""
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("  BENCHMARK DE PERSISTÊNCIA HISTÓRICA — AAS Robô SCARA")
    lines.append("=" * 70)

    # Período de aquisição
    ap = results.acquisition_period
    if ap and ap.n_intervals > 0:
        lines.append("")
        lines.append("┌─────────────────────────────────────────────────────────────────────┐")
        lines.append("│ 1. PERÍODO DE AQUISIÇÃO DOS REGISTROS                               │")
        lines.append("├─────────────────────────────────────────────────────────────────────┤")
        lines.append(f"│ Registros:         {ap.n_records:<50}│")
        lines.append(f"│ Intervalo médio:   {ap.interval_mean_s:.3f} ± {ap.interval_std_s:.3f} s{'':<35}│")
        lines.append(f"│ Mediana:           {ap.interval_median_s:.3f} s{'':<46}│")
        lines.append(f"│ P95:               {ap.interval_p95_s:.3f} s{'':<46}│")
        lines.append(f"│ P99:               {ap.interval_p99_s:.3f} s{'':<46}│")
        lines.append(f"│ Min / Max:         {ap.interval_min_s:.3f} / {ap.interval_max_s:.3f} s{'':<37}│")
        lines.append(f"│ Duração total:     {ap.total_duration_s:.1f} s ({ap.total_duration_s/3600:.2f} h){'':<28}│")
        lines.append(f"│ Primeiro registro: {ap.first_record[:26]:<50}│")
        lines.append(f"│ Último registro:   {ap.last_record[:26]:<50}│")
        lines.append("└─────────────────────────────────────────────────────────────────────┘")

    # Taxa de inserção
    ir = results.insertion_rate
    if ir and ir.total_records > 0:
        lines.append("")
        lines.append("┌─────────────────────────────────────────────────────────────────────┐")
        lines.append("│ 2. TAXA DE INSERÇÃO                                                 │")
        lines.append("├─────────────────────────────────────────────────────────────────────┤")
        lines.append(f"│ Total registros:   {ir.total_records:<50}│")
        lines.append(f"│ Taxa global:       {ir.rate_records_per_s:.2f} registros/s{'':<38}│")
        lines.append(f"│ Taxa snapshots:    {ir.rate_snapshots_per_s:.2f} snapshots/s{'':<38}│")
        for table, count in ir.tables.items():
            lines.append(f"│   {table:<20} {count:<46}│")
        lines.append("└─────────────────────────────────────────────────────────────────────┘")

    # Tamanho do banco
    ds = results.database_size
    if ds and ds.size_bytes > 0:
        lines.append("")
        lines.append("┌─────────────────────────────────────────────────────────────────────┐")
        lines.append("│ 3. TAMANHO DO BANCO EM DISCO                                        │")
        lines.append("├─────────────────────────────────────────────────────────────────────┤")
        lines.append(f"│ Caminho:           {Path(ds.path).name:<50}│")
        lines.append(f"│ Tamanho:           {ds.size_mb:.2f} MB ({ds.size_bytes:,} bytes){'':<24}│")
        lines.append(f"│ Pages:             {ds.page_count} × {ds.page_size} bytes{'':<36}│")
        lines.append(f"│ Freelist:          {ds.freelist_count} páginas livres{'':<38}│")
        for table, count in ds.tables.items():
            lines.append(f"│   {table:<20} {count:,} registros{'':<28}│")
        lines.append("└─────────────────────────────────────────────────────────────────────┘")

    # Latências de consultas
    if results.query_latencies:
        lines.append("")
        lines.append("┌─────────────────────────────────────────────────────────────────────┐")
        lines.append("│ 4. LATÊNCIA DAS CONSULTAS (VIEWS)                                   │")
        lines.append("├─────────────────────────────────────────────────────────────────────┤")
        lines.append("│ Consulta               │ Média±DP (ms) │ P95    │ P99    │ Max     │")
        lines.append("├────────────────────────┼───────────────┼────────┼────────┼─────────┤")
        for ql in results.query_latencies:
            name = ql.query_name[:22]
            mean_std = f"{ql.latency_mean_ms:.2f}±{ql.latency_std_ms:.2f}"
            lines.append(
                f"│ {name:<22} │ {mean_std:<13} │ {ql.latency_p95_ms:>6.2f} │"
                f" {ql.latency_p99_ms:>6.2f} │ {ql.latency_max_ms:>7.2f} │"
            )
        lines.append("└────────────────────────┴───────────────┴────────┴────────┴─────────┘")

    lines.append("")
    report = "\n".join(lines)
    print(report)
    return report


def save_results(results: DbBenchmarkResults, output_dir: str) -> None:
    """Salva resultados em JSON e texto."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON
    json_file = out_path / f"db_benchmark_{timestamp}.json"

    def _serialize(obj):
        if hasattr(obj, '__dict__'):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        return str(obj)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(asdict(results), f, indent=2, ensure_ascii=False, default=_serialize)
    logger.info("Resultados JSON salvos em: %s", json_file)

    # Texto
    report = print_report(results)
    txt_file = out_path / f"db_benchmark_{timestamp}.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info("Relatório texto salvo em: %s", txt_file)


# ─── Main ─────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark de persistência histórica — AAS Robô SCARA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python benchmarks/db_benchmark.py
  python benchmarks/db_benchmark.py --db persistence/storage/aas_history.sqlite3
  python benchmarks/db_benchmark.py --queries 200 --output benchmarks/results/
  python benchmarks/db_benchmark.py --api http://localhost:5000
        """
    )
    parser.add_argument(
        "--db", type=str, default=DEFAULT_AAS_DB,
        help=f"Caminho do banco SQLite (default: {DEFAULT_AAS_DB})"
    )
    parser.add_argument(
        "--backend-db", type=str, default=DEFAULT_BACKEND_DB,
        help="Caminho do banco do backend web"
    )
    parser.add_argument(
        "--queries", "-q", type=int, default=100,
        help="Número de execuções para cada consulta (default: 100)"
    )
    parser.add_argument(
        "--api", type=str, default="http://localhost:5000",
        help="URL base da API para benchmark HTTP (default: http://localhost:5000)"
    )
    parser.add_argument(
        "--skip-api", action="store_true",
        help="Pular benchmark de API HTTP"
    )
    parser.add_argument(
        "--output", "-o", type=str, default="benchmarks/results",
        help="Diretório de saída (default: benchmarks/results/)"
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("  BENCHMARK DE PERSISTÊNCIA HISTÓRICA")
    logger.info("=" * 70)
    logger.info("Banco: %s", args.db)
    logger.info("Queries por teste: %d", args.queries)

    results = DbBenchmarkResults()
    results.metadata = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "db_path": args.db,
        "n_query_executions": args.queries,
        "api_url": args.api,
    }

    # 1. Período de aquisição
    logger.info("")
    logger.info("─── 1. Período de aquisição ───")
    results.acquisition_period = measure_acquisition_period(args.db)

    # 2. Taxa de inserção
    logger.info("")
    logger.info("─── 2. Taxa de inserção ───")
    results.insertion_rate = measure_insertion_rate(args.db)

    # 3. Tamanho do banco
    logger.info("")
    logger.info("─── 3. Tamanho do banco ───")
    results.database_size = measure_database_size(args.db)

    # 4. Latência das consultas SQL diretas
    logger.info("")
    logger.info("─── 4. Latência das consultas (SQL direto) ───")
    results.query_latencies = measure_query_latencies(args.db, args.queries)

    # 5. Latência da API HTTP (opcional)
    if not args.skip_api:
        logger.info("")
        logger.info("─── 5. Latência da API HTTP ───")
        api_results = measure_api_latencies(args.api, min(args.queries, 50))
        results.query_latencies.extend(api_results)

    # Salvar resultados
    save_results(results, args.output)


if __name__ == "__main__":
    main()
