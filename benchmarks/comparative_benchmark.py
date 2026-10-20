# ==================================================================================================
#   Benchmark Comparativo — AAS Robô SCARA
#
#   Compara 3 arquiteturas nas mesmas condições de carga:
#     (i)   Cliente OPC UA direto sem camada AAS (baseline)
#     (ii)  Servidor AAS aberto (Eclipse BaSyx ou FA³ST)
#     (iii) Arquitetura proposta com SQLite substituído por InfluxDB/TimescaleDB
#
#   Métricas:
#   - Latência fim-a-fim (SourceTimestamp → disponibilidade no cliente)
#   - Taxa de aquisição efetiva (notificações/s)
#   - Consumo de CPU (% médio e pico)
#   - Consumo de memória (RSS médio e pico)
#   - Tamanho de armazenamento após N amostras
#   - Latência de consulta histórica (last, range 1h, range 24h)
#
#   Uso:
#     python benchmarks/comparative_benchmark.py --scenario baseline --duration 300
#     python benchmarks/comparative_benchmark.py --scenario basyx --duration 300
#     python benchmarks/comparative_benchmark.py --scenario influxdb --duration 300
#     python benchmarks/comparative_benchmark.py --scenario all --duration 300
#     python benchmarks/comparative_benchmark.py --compare results/  (gera tabela comparativa)
#
#   Requisitos:
#     pip install numpy asyncua psutil
#     (para cenário InfluxDB): pip install influxdb-client
#     (para cenário BaSyx): servidor BaSyx rodando + requests
# ==================================================================================================

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ─── Configuração ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("comparative_benchmark")

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SERVER = os.getenv("OPCUA_SERVER_URL", "opc.tcp://192.168.0.31:4880/Staubli")
CONFIG_FILE = ROOT_DIR / "acquisition" / "client" / "config_opcua.json"


# ─── Data Classes ────────────────────────────────────────────────────────────────

@dataclass
class ResourceUsage:
    """Métricas de consumo de recursos durante o ensaio."""
    cpu_mean_pct: float = 0.0
    cpu_max_pct: float = 0.0
    mem_rss_mean_mb: float = 0.0
    mem_rss_max_mb: float = 0.0
    mem_vms_mean_mb: float = 0.0


@dataclass
class LatencyStats:
    """Estatísticas de latência."""
    n_samples: int = 0
    mean_ms: float = 0.0
    std_ms: float = 0.0
    median_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0


@dataclass
class QueryLatency:
    """Latência de uma consulta histórica."""
    query_name: str = ""
    n_executions: int = 0
    mean_ms: float = 0.0
    std_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    rows_returned: int = 0


@dataclass
class ScenarioResult:
    """Resultado de um cenário de benchmark."""
    scenario_name: str = ""
    scenario_description: str = ""
    duration_s: float = 0.0
    start_time: str = ""
    end_time: str = ""

    # Latência de aquisição
    acquisition_latency: Optional[LatencyStats] = None

    # Taxa
    acquisition_rate_hz: float = 0.0
    total_notifications: int = 0

    # Recursos
    resources: Optional[ResourceUsage] = None

    # Armazenamento
    storage_size_bytes: int = 0
    storage_size_mb: float = 0.0
    storage_records: int = 0

    # Consultas históricas
    query_latencies: List[QueryLatency] = field(default_factory=list)

    # Config
    config: Dict[str, Any] = field(default_factory=dict)


# ─── Utilitários ──────────────────────────────────────────────────────────────────

def _extract_nodeids(config: Dict[str, Any]) -> List[str]:
    """Extrai NodeIds do config."""
    nodeids = set()
    def _walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "_client":
                    continue
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)
        elif isinstance(obj, str) and obj.startswith("ns=") and ";" in obj:
            nodeids.add(obj)
    _walk(config)
    return sorted(list(nodeids))


def _compute_latency_stats(latencies: List[float]) -> LatencyStats:
    """Computa estatísticas a partir de lista de latências em ms."""
    if not latencies:
        return LatencyStats()
    arr = np.array(latencies)
    return LatencyStats(
        n_samples=len(arr),
        mean_ms=float(np.mean(arr)),
        std_ms=float(np.std(arr)),
        median_ms=float(np.median(arr)),
        p95_ms=float(np.percentile(arr, 95)),
        p99_ms=float(np.percentile(arr, 99)),
        min_ms=float(np.min(arr)),
        max_ms=float(np.max(arr)),
    )


class ResourceMonitor:
    """Monitora CPU e memória de um processo em background."""

    def __init__(self, pid: Optional[int] = None):
        self._pid = pid or os.getpid()
        self._running = False
        self._cpu_samples: List[float] = []
        self._mem_samples: List[float] = []
        self._mem_vms_samples: List[float] = []

    def start(self):
        self._running = True
        self._cpu_samples = []
        self._mem_samples = []
        self._mem_vms_samples = []

    def sample(self):
        """Coleta uma amostra de CPU e memória."""
        try:
            import psutil
            proc = psutil.Process(self._pid)
            cpu = proc.cpu_percent(interval=None)
            mem = proc.memory_info()
            self._cpu_samples.append(cpu)
            self._mem_samples.append(mem.rss / (1024 * 1024))
            self._mem_vms_samples.append(mem.vms / (1024 * 1024))
        except Exception:
            pass

    def stop(self) -> ResourceUsage:
        self._running = False
        usage = ResourceUsage()
        if self._cpu_samples:
            arr = np.array(self._cpu_samples)
            usage.cpu_mean_pct = float(np.mean(arr))
            usage.cpu_max_pct = float(np.max(arr))
        if self._mem_samples:
            arr = np.array(self._mem_samples)
            usage.mem_rss_mean_mb = float(np.mean(arr))
            usage.mem_rss_max_mb = float(np.max(arr))
        if self._mem_vms_samples:
            usage.mem_vms_mean_mb = float(np.mean(self._mem_vms_samples))
        return usage


# ══════════════════════════════════════════════════════════════════════════════════
# CENÁRIO (i): BASELINE — Cliente OPC UA direto sem camada AAS
# ══════════════════════════════════════════════════════════════════════════════════
#
# Lê dados do servidor OPC UA via subscription e armazena diretamente em memória.
# Sem mapeamento AAS, sem serialização JSON, sem persistência em banco.
# Representa o overhead mínimo possível para comparação.
# ══════════════════════════════════════════════════════════════════════════════════

class BaselineHandler:
    """Handler de subscription puro — só armazena valores em memória."""

    def __init__(self, clock_offset_ms: float = 0.0):
        self.latencies: List[float] = []
        self._clock_offset_ms = clock_offset_ms
        self._active = True

    def datachange_notification(self, node, val, data):
        if not self._active:
            return
        t_receive = time.time()
        try:
            source_ts = None
            if hasattr(data, 'monitored_item') and hasattr(data.monitored_item, 'Value'):
                dv = data.monitored_item.Value
                if hasattr(dv, 'SourceTimestamp') and dv.SourceTimestamp is not None:
                    source_ts = dv.SourceTimestamp.timestamp()
            if source_ts is None and hasattr(data, 'Value'):
                if hasattr(data.Value, 'SourceTimestamp') and data.Value.SourceTimestamp:
                    source_ts = data.Value.SourceTimestamp.timestamp()
            if source_ts is None:
                return
            latency_ms = (t_receive - source_ts) * 1000 - self._clock_offset_ms
            self.latencies.append(latency_ms)
        except Exception:
            pass

    def status_change_notification(self, status):
        pass

    def stop(self):
        self._active = False


async def run_baseline_scenario(
    server_url: str,
    duration_s: float,
    publishing_interval_ms: float = 200,
) -> ScenarioResult:
    """Cenário baseline: OPC UA direto sem AAS."""
    from asyncua import Client

    result = ScenarioResult(
        scenario_name="baseline",
        scenario_description="Cliente OPC UA direto (sem camada AAS, sem persistência)",
    )
    result.config = {
        "server_url": server_url,
        "duration_s": duration_s,
        "publishing_interval_ms": publishing_interval_ms,
    }

    client = Client(url=server_url, timeout=10)
    await client.connect()
    logger.info("[baseline] Conectado ao servidor OPC UA")

    try:
        # Clock offset
        clock_offset = await _measure_clock_offset(client)
        logger.info("[baseline] Clock offset: %.2f ms", clock_offset)

        # Nós
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            nodeids = _extract_nodeids(config)
        else:
            nodeids = ["ns=0;i=2258"]

        # Resource monitor
        res_monitor = ResourceMonitor()
        res_monitor.start()

        # Subscription
        handler = BaselineHandler(clock_offset_ms=clock_offset)
        subscription = await client.create_subscription(
            period=publishing_interval_ms, handler=handler
        )
        nodes = [client.get_node(nid) for nid in nodeids]
        await subscription.subscribe_data_change(nodes)

        # Coleta
        result.start_time = datetime.now(timezone.utc).isoformat()
        start = time.time()
        while (time.time() - start) < duration_s:
            await asyncio.sleep(1.0)
            res_monitor.sample()

        handler.stop()
        result.end_time = datetime.now(timezone.utc).isoformat()
        result.duration_s = time.time() - start

        # Resultados
        result.resources = res_monitor.stop()
        result.acquisition_latency = _compute_latency_stats(handler.latencies)
        result.total_notifications = len(handler.latencies)
        result.acquisition_rate_hz = len(handler.latencies) / result.duration_s
        result.storage_size_bytes = 0  # sem persistência
        result.storage_size_mb = 0.0
        result.storage_records = 0

        try:
            await subscription.delete()
        except Exception:
            pass

    finally:
        await client.disconnect()

    logger.info("[baseline] Concluído: %d notificações em %.1f s",
                result.total_notifications, result.duration_s)
    return result


# ══════════════════════════════════════════════════════════════════════════════════
# CENÁRIO (ii): SERVIDOR AAS ABERTO (Eclipse BaSyx / FA³ST)
# ══════════════════════════════════════════════════════════════════════════════════
#
# Lê dados do OPC UA, publica em um servidor AAS externo (BaSyx ou FA³ST via HTTP),
# e consulta o histórico via API REST do servidor AAS.
#
# Pré-requisito: BaSyx AAS Server rodando em http://localhost:4001
# Ou FA³ST em http://localhost:443
# ══════════════════════════════════════════════════════════════════════════════════

async def run_basyx_scenario(
    server_url: str,
    duration_s: float,
    basyx_url: str = "http://localhost:4001",
    publishing_interval_ms: float = 200,
) -> ScenarioResult:
    """Cenário BaSyx/FA³ST: OPC UA → servidor AAS aberto."""
    from asyncua import Client
    import requests

    result = ScenarioResult(
        scenario_name="basyx_aas_server",
        scenario_description=f"OPC UA → Servidor AAS aberto ({basyx_url})",
    )
    result.config = {
        "server_url": server_url,
        "basyx_url": basyx_url,
        "duration_s": duration_s,
        "publishing_interval_ms": publishing_interval_ms,
    }

    # Verifica se BaSyx está acessível
    try:
        resp = requests.get(f"{basyx_url}/shells", timeout=5)
        if resp.status_code != 200:
            logger.warning("[basyx] Servidor AAS não acessível em %s (status %d)",
                          basyx_url, resp.status_code)
            result.scenario_description += " [SERVIDOR NÃO DISPONÍVEL]"
            return result
    except requests.exceptions.ConnectionError:
        logger.warning("[basyx] Servidor AAS não acessível em %s", basyx_url)
        result.scenario_description += " [SERVIDOR NÃO DISPONÍVEL]"
        return result

    client = Client(url=server_url, timeout=10)
    await client.connect()
    logger.info("[basyx] Conectado ao OPC UA e BaSyx")

    try:
        clock_offset = await _measure_clock_offset(client)

        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            nodeids = _extract_nodeids(config)
        else:
            nodeids = ["ns=0;i=2258"]

        res_monitor = ResourceMonitor()
        res_monitor.start()

        latencies: List[float] = []
        write_latencies: List[float] = []
        notifications = 0

        class BaSyxHandler:
            def __init__(self):
                self._active = True

            def datachange_notification(self, node, val, data):
                nonlocal notifications
                if not self._active:
                    return
                t_receive = time.time()
                try:
                    source_ts = None
                    if hasattr(data, 'monitored_item') and hasattr(data.monitored_item, 'Value'):
                        dv = data.monitored_item.Value
                        if hasattr(dv, 'SourceTimestamp') and dv.SourceTimestamp:
                            source_ts = dv.SourceTimestamp.timestamp()
                    if source_ts is None:
                        return

                    latency_ms = (t_receive - source_ts) * 1000 - clock_offset
                    latencies.append(latency_ms)
                    notifications += 1

                    # Publica no BaSyx via PUT (submodel element value)
                    t_write_start = time.perf_counter()
                    nodeid_str = node.nodeid.to_string()
                    payload = {"value": str(val)}
                    try:
                        requests.put(
                            f"{basyx_url}/submodels/operational/submodel-elements/{nodeid_str}/$value",
                            json=payload, timeout=2
                        )
                    except Exception:
                        pass
                    t_write_end = time.perf_counter()
                    write_latencies.append((t_write_end - t_write_start) * 1000)

                except Exception:
                    pass

            def status_change_notification(self, status):
                pass

        handler = BaSyxHandler()
        subscription = await client.create_subscription(
            period=publishing_interval_ms, handler=handler
        )
        nodes = [client.get_node(nid) for nid in nodeids]
        await subscription.subscribe_data_change(nodes)

        result.start_time = datetime.now(timezone.utc).isoformat()
        start = time.time()
        while (time.time() - start) < duration_s:
            await asyncio.sleep(1.0)
            res_monitor.sample()

        handler._active = False
        result.end_time = datetime.now(timezone.utc).isoformat()
        result.duration_s = time.time() - start
        result.resources = res_monitor.stop()
        result.acquisition_latency = _compute_latency_stats(latencies)
        result.total_notifications = notifications
        result.acquisition_rate_hz = notifications / result.duration_s if result.duration_s > 0 else 0

        # Consulta histórica via API BaSyx
        result.query_latencies = _benchmark_basyx_queries(basyx_url)

        try:
            await subscription.delete()
        except Exception:
            pass

    finally:
        await client.disconnect()

    logger.info("[basyx] Concluído: %d notificações", result.total_notifications)
    return result


def _benchmark_basyx_queries(basyx_url: str, n_exec: int = 50) -> List[QueryLatency]:
    """Mede latência de consultas ao servidor BaSyx."""
    import requests
    results = []
    queries = [
        ("basyx_get_submodel", f"{basyx_url}/submodels/operational"),
        ("basyx_get_all_shells", f"{basyx_url}/shells"),
    ]
    for name, url in queries:
        latencies = []
        rows = 0
        for i in range(n_exec):
            try:
                t0 = time.perf_counter()
                resp = requests.get(url, timeout=5)
                t1 = time.perf_counter()
                latencies.append((t1 - t0) * 1000)
                if i == 0 and resp.status_code == 200:
                    data = resp.json()
                    rows = len(data) if isinstance(data, list) else 1
            except Exception:
                break
        if latencies:
            arr = np.array(latencies)
            results.append(QueryLatency(
                query_name=name, n_executions=len(latencies),
                mean_ms=float(np.mean(arr)), std_ms=float(np.std(arr)),
                p95_ms=float(np.percentile(arr, 95)),
                p99_ms=float(np.percentile(arr, 99)),
                rows_returned=rows,
            ))
    return results


# ══════════════════════════════════════════════════════════════════════════════════
# CENÁRIO (iii): ARQUITETURA PROPOSTA COM InfluxDB/TimescaleDB
# ══════════════════════════════════════════════════════════════════════════════════
#
# Mesmo fluxo da arquitetura proposta, mas com persistência em InfluxDB ao invés
# de SQLite. Mede o overhead de escrita e consulta em banco de séries temporais.
#
# Pré-requisito: InfluxDB 2.x rodando em http://localhost:8086
# Variáveis: INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET
# ══════════════════════════════════════════════════════════════════════════════════

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "my-super-secret-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "aas-scara")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "scara_benchmark")


async def run_influxdb_scenario(
    server_url: str,
    duration_s: float,
    publishing_interval_ms: float = 200,
) -> ScenarioResult:
    """Cenário InfluxDB: OPC UA → mapeamento AAS → InfluxDB."""
    from asyncua import Client

    result = ScenarioResult(
        scenario_name="influxdb",
        scenario_description=f"Arquitetura proposta + InfluxDB ({INFLUX_URL})",
    )
    result.config = {
        "server_url": server_url,
        "influx_url": INFLUX_URL,
        "duration_s": duration_s,
        "publishing_interval_ms": publishing_interval_ms,
    }

    # Verifica se InfluxDB está acessível
    try:
        from influxdb_client import InfluxDBClient, Point
        from influxdb_client.client.write_api import SYNCHRONOUS
    except ImportError:
        logger.warning("[influxdb] Módulo 'influxdb-client' não instalado. "
                       "Instale com: pip install influxdb-client")
        result.scenario_description += " [MÓDULO NÃO INSTALADO]"
        return result

    try:
        influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        health = influx_client.health()
        if health.status != "pass":
            logger.warning("[influxdb] InfluxDB não saudável: %s", health.message)
            result.scenario_description += " [INFLUXDB NÃO DISPONÍVEL]"
            return result
    except Exception as e:
        logger.warning("[influxdb] InfluxDB não acessível: %s", e)
        result.scenario_description += " [INFLUXDB NÃO DISPONÍVEL]"
        return result

    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    query_api = influx_client.query_api()

    client = Client(url=server_url, timeout=10)
    await client.connect()
    logger.info("[influxdb] Conectado ao OPC UA e InfluxDB")

    try:
        clock_offset = await _measure_clock_offset(client)

        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            nodeids = _extract_nodeids(config)
        else:
            nodeids = ["ns=0;i=2258"]

        res_monitor = ResourceMonitor()
        res_monitor.start()

        latencies: List[float] = []
        write_latencies: List[float] = []
        notifications = 0
        records_written = 0

        class InfluxHandler:
            def __init__(self):
                self._active = True

            def datachange_notification(self, node, val, data):
                nonlocal notifications, records_written
                if not self._active:
                    return
                t_receive = time.time()
                try:
                    source_ts = None
                    if hasattr(data, 'monitored_item') and hasattr(data.monitored_item, 'Value'):
                        dv = data.monitored_item.Value
                        if hasattr(dv, 'SourceTimestamp') and dv.SourceTimestamp:
                            source_ts = dv.SourceTimestamp.timestamp()
                    if source_ts is None:
                        return

                    latency_ms = (t_receive - source_ts) * 1000 - clock_offset
                    latencies.append(latency_ms)
                    notifications += 1

                    # Escreve no InfluxDB
                    nodeid_str = node.nodeid.to_string()
                    try:
                        value = float(val) if val is not None else 0.0
                    except (TypeError, ValueError):
                        value = 0.0

                    t_w0 = time.perf_counter()
                    point = (
                        Point("scara_measurement")
                        .tag("node_id", nodeid_str)
                        .field("value", value)
                    )
                    try:
                        write_api.write(bucket=INFLUX_BUCKET, record=point)
                        records_written += 1
                    except Exception:
                        pass
                    t_w1 = time.perf_counter()
                    write_latencies.append((t_w1 - t_w0) * 1000)

                except Exception:
                    pass

            def status_change_notification(self, status):
                pass

        handler = InfluxHandler()
        subscription = await client.create_subscription(
            period=publishing_interval_ms, handler=handler
        )
        nodes = [client.get_node(nid) for nid in nodeids]
        await subscription.subscribe_data_change(nodes)

        result.start_time = datetime.now(timezone.utc).isoformat()
        start = time.time()
        while (time.time() - start) < duration_s:
            await asyncio.sleep(1.0)
            res_monitor.sample()

        handler._active = False
        result.end_time = datetime.now(timezone.utc).isoformat()
        result.duration_s = time.time() - start
        result.resources = res_monitor.stop()
        result.acquisition_latency = _compute_latency_stats(latencies)
        result.total_notifications = notifications
        result.acquisition_rate_hz = notifications / result.duration_s if result.duration_s > 0 else 0
        result.storage_records = records_written

        # Consulta histórica no InfluxDB
        result.query_latencies = _benchmark_influx_queries(query_api)

        # Tamanho de armazenamento (aproximado via contagem)
        # InfluxDB não expõe tamanho por bucket facilmente; usamos estimativa
        result.storage_size_bytes = records_written * 80  # ~80 bytes/ponto típico
        result.storage_size_mb = result.storage_size_bytes / (1024 * 1024)

        try:
            await subscription.delete()
        except Exception:
            pass

    finally:
        await client.disconnect()
        influx_client.close()

    logger.info("[influxdb] Concluído: %d notificações, %d escritas",
                result.total_notifications, records_written)
    return result


def _benchmark_influx_queries(query_api, n_exec: int = 50) -> List[QueryLatency]:
    """Mede latência de consultas Flux no InfluxDB."""
    results = []
    queries = [
        ("influx_last_value",
         f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1m) |> last()'),
        ("influx_range_1h",
         f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h) '
         f'|> filter(fn: (r) => r._measurement == "scara_measurement")'),
        ("influx_range_24h",
         f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -24h) '
         f'|> filter(fn: (r) => r._measurement == "scara_measurement") |> limit(n: 500)'),
    ]
    for name, flux_query in queries:
        latencies = []
        rows = 0
        for i in range(n_exec):
            try:
                t0 = time.perf_counter()
                tables = query_api.query(flux_query)
                t1 = time.perf_counter()
                latencies.append((t1 - t0) * 1000)
                if i == 0:
                    rows = sum(len(t.records) for t in tables)
            except Exception:
                break
        if latencies:
            arr = np.array(latencies)
            results.append(QueryLatency(
                query_name=name, n_executions=len(latencies),
                mean_ms=float(np.mean(arr)), std_ms=float(np.std(arr)),
                p95_ms=float(np.percentile(arr, 95)),
                p99_ms=float(np.percentile(arr, 99)),
                rows_returned=rows,
            ))
    return results


# ─── Clock Offset (compartilhado) ────────────────────────────────────────────────

async def _measure_clock_offset(client, n_samples: int = 20) -> float:
    """Mede offset via half-RTT."""
    server_time_node = client.get_node("ns=0;i=2258")
    offsets = []
    for _ in range(n_samples):
        t_before = time.time()
        server_time = await server_time_node.read_value()
        t_after = time.time()
        if server_time is None or not isinstance(server_time, datetime):
            continue
        t_server = server_time.timestamp()
        t_client_mid = (t_before + t_after) / 2
        offsets.append((t_client_mid - t_server) * 1000)
        await asyncio.sleep(0.05)
    if not offsets:
        return 0.0
    arr = np.array(offsets)
    mean = np.mean(arr)
    std = np.std(arr)
    filtered = arr[np.abs(arr - mean) < 2 * std]
    return float(np.mean(filtered)) if len(filtered) >= 3 else float(mean)


# ─── Tabela Comparativa ───────────────────────────────────────────────────────────

def generate_comparison_table(results: List[ScenarioResult]) -> str:
    """Gera tabela comparativa entre cenários."""
    lines = []
    lines.append("")
    lines.append("=" * 90)
    lines.append("  TABELA COMPARATIVA — BENCHMARKS AAS ROBÔ SCARA")
    lines.append("=" * 90)
    lines.append("")

    # Header
    header = f"{'Métrica':<35}"
    for r in results:
        header += f" │ {r.scenario_name:<18}"
    lines.append(header)
    lines.append("─" * 35 + ("─┼─" + "─" * 18) * len(results))

    # Latência
    def _lat_str(r):
        if r.acquisition_latency and r.acquisition_latency.n_samples > 0:
            return f"{r.acquisition_latency.mean_ms:.1f}±{r.acquisition_latency.std_ms:.1f}"
        return "N/A"

    def _lat_p95(r):
        if r.acquisition_latency and r.acquisition_latency.n_samples > 0:
            return f"{r.acquisition_latency.p95_ms:.1f}"
        return "N/A"

    def _lat_p99(r):
        if r.acquisition_latency and r.acquisition_latency.n_samples > 0:
            return f"{r.acquisition_latency.p99_ms:.1f}"
        return "N/A"

    row = f"{'Latência média±DP (ms)':<35}"
    for r in results:
        row += f" │ {_lat_str(r):<18}"
    lines.append(row)

    row = f"{'Latência P95 (ms)':<35}"
    for r in results:
        row += f" │ {_lat_p95(r):<18}"
    lines.append(row)

    row = f"{'Latência P99 (ms)':<35}"
    for r in results:
        row += f" │ {_lat_p99(r):<18}"
    lines.append(row)

    # Taxa
    row = f"{'Taxa aquisição (Hz)':<35}"
    for r in results:
        row += f" │ {r.acquisition_rate_hz:<18.2f}"
    lines.append(row)

    row = f"{'Notificações totais':<35}"
    for r in results:
        row += f" │ {r.total_notifications:<18}"
    lines.append(row)

    # Recursos
    row = f"{'CPU média (%)':<35}"
    for r in results:
        cpu = r.resources.cpu_mean_pct if r.resources else 0
        row += f" │ {cpu:<18.1f}"
    lines.append(row)

    row = f"{'CPU pico (%)':<35}"
    for r in results:
        cpu = r.resources.cpu_max_pct if r.resources else 0
        row += f" │ {cpu:<18.1f}"
    lines.append(row)

    row = f"{'Memória RSS média (MB)':<35}"
    for r in results:
        mem = r.resources.mem_rss_mean_mb if r.resources else 0
        row += f" │ {mem:<18.1f}"
    lines.append(row)

    row = f"{'Memória RSS pico (MB)':<35}"
    for r in results:
        mem = r.resources.mem_rss_max_mb if r.resources else 0
        row += f" │ {mem:<18.1f}"
    lines.append(row)

    # Armazenamento
    row = f"{'Armazenamento (MB)':<35}"
    for r in results:
        row += f" │ {r.storage_size_mb:<18.2f}"
    lines.append(row)

    row = f"{'Registros armazenados':<35}"
    for r in results:
        row += f" │ {r.storage_records:<18}"
    lines.append(row)

    # Consultas históricas
    lines.append("")
    lines.append("─" * 90)
    lines.append("  Latência de consulta histórica (ms):")
    lines.append("─" * 90)

    # Coleta todas as queries únicas
    all_query_names = set()
    for r in results:
        for ql in r.query_latencies:
            all_query_names.add(ql.query_name)

    for qname in sorted(all_query_names):
        row = f"  {qname:<33}"
        for r in results:
            ql = next((q for q in r.query_latencies if q.query_name == qname), None)
            if ql:
                row += f" │ {ql.mean_ms:.2f}±{ql.std_ms:.2f}"
            else:
                row += f" │ {'N/A':<18}"
        lines.append(row)

    lines.append("")
    lines.append("=" * 90)

    report = "\n".join(lines)
    print(report)
    return report


# ─── Salvar Resultados ────────────────────────────────────────────────────────────

def save_scenario_result(result: ScenarioResult, output_dir: str) -> None:
    """Salva resultado de um cenário."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_file = out_path / f"comparative_{result.scenario_name}_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2, ensure_ascii=False, default=str)
    logger.info("Resultado salvo: %s", json_file)


def save_comparison(results: List[ScenarioResult], output_dir: str) -> None:
    """Salva tabela comparativa e resultados consolidados."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON consolidado
    json_file = out_path / f"comparative_all_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=2, ensure_ascii=False, default=str)

    # Tabela comparativa
    report = generate_comparison_table(results)
    txt_file = out_path / f"comparative_table_{timestamp}.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info("Tabela comparativa salva em: %s", txt_file)


def load_and_compare(results_dir: str) -> None:
    """Carrega resultados anteriores e gera tabela comparativa."""
    results_path = Path(results_dir)
    results = []

    for json_file in sorted(results_path.glob("comparative_*.json")):
        if "all" in json_file.name or "table" in json_file.name:
            continue
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Reconstroi ScenarioResult básico para a tabela
            r = ScenarioResult()
            r.scenario_name = data.get("scenario_name", json_file.stem)
            r.scenario_description = data.get("scenario_description", "")
            r.duration_s = data.get("duration_s", 0)
            r.total_notifications = data.get("total_notifications", 0)
            r.acquisition_rate_hz = data.get("acquisition_rate_hz", 0)
            r.storage_size_mb = data.get("storage_size_mb", 0)
            r.storage_records = data.get("storage_records", 0)

            lat_data = data.get("acquisition_latency")
            if lat_data:
                r.acquisition_latency = LatencyStats(**lat_data)

            res_data = data.get("resources")
            if res_data:
                r.resources = ResourceUsage(**res_data)

            ql_data = data.get("query_latencies", [])
            r.query_latencies = [QueryLatency(**q) for q in ql_data]

            results.append(r)
        except Exception as e:
            logger.warning("Erro ao carregar %s: %s", json_file, e)

    if results:
        generate_comparison_table(results)
    else:
        logger.warning("Nenhum resultado encontrado em %s", results_dir)


# ─── Main ─────────────────────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════════════════
# CENÁRIO (ii) SIMULADO: OVERHEAD DE SERVIDOR AAS (HTTP + JSON serialization)
# ══════════════════════════════════════════════════════════════════════════════════
#
# Simula o overhead de publicar cada notificação em um servidor AAS via HTTP PUT.
# Usa um servidor HTTP local em thread para medir o custo real de:
# - Serialização JSON do valor
# - Requisição HTTP PUT (loopback)
# - Parsing e armazenamento no servidor
# ══════════════════════════════════════════════════════════════════════════════════

async def run_basyx_simulated_scenario(
    server_url: str,
    duration_s: float,
    publishing_interval_ms: float = 200,
) -> ScenarioResult:
    """Cenário BaSyx simulado: mede overhead de HTTP+JSON por notificação."""
    from asyncua import Client
    import http.server
    import threading
    import json as _json
    import urllib.request

    result = ScenarioResult(
        scenario_name="basyx_simulated",
        scenario_description="OPC UA + overhead HTTP PUT simulado (loopback localhost)",
    )
    result.config = {
        "server_url": server_url,
        "duration_s": duration_s,
        "publishing_interval_ms": publishing_interval_ms,
        "simulation": "HTTP PUT to localhost:4999 per notification",
    }

    # Mini HTTP server para receber PUTs
    class SimplePutHandler(http.server.BaseHTTPRequestHandler):
        def do_PUT(self):
            length = int(self.headers.get('Content-Length', 0))
            self.rfile.read(length)
            self.send_response(204)
            self.end_headers()
        def log_message(self, format, *args):
            pass  # silencia logs

    httpd = http.server.HTTPServer(('127.0.0.1', 4999), SimplePutHandler)
    http_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    http_thread.start()

    client = Client(url=server_url, timeout=10)
    await client.connect()
    logger.info("[basyx-sim] Conectado ao OPC UA + HTTP server local na porta 4999")

    try:
        clock_offset = await _measure_clock_offset(client)
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            nodeids = _extract_nodeids(config)
        else:
            nodeids = ["ns=0;i=2258"]

        res_monitor = ResourceMonitor()
        res_monitor.start()

        latencies: List[float] = []
        write_latencies: List[float] = []
        notifications = 0

        class BaSyxSimHandler:
            def __init__(self):
                self._active = True
                self._perf_offset = time.time() - time.perf_counter()

            def datachange_notification(self, node, val, data):
                nonlocal notifications
                if not self._active:
                    return
                t_receive = time.perf_counter() + self._perf_offset
                try:
                    source_ts = None
                    if hasattr(data, 'monitored_item') and hasattr(data.monitored_item, 'Value'):
                        dv = data.monitored_item.Value
                        if hasattr(dv, 'SourceTimestamp') and dv.SourceTimestamp:
                            source_ts = dv.SourceTimestamp.timestamp()
                    if source_ts is None:
                        return

                    latency_ms = (t_receive - source_ts) * 1000 - clock_offset
                    if abs(latency_ms) < 10000:
                        latencies.append(latency_ms)
                    notifications += 1

                    # Simula PUT HTTP ao servidor AAS
                    t_w0 = time.perf_counter()
                    payload = _json.dumps({"value": str(val), "node": node.nodeid.to_string()}).encode()
                    req = urllib.request.Request(
                        "http://127.0.0.1:4999/submodel/value",
                        data=payload, method='PUT',
                        headers={'Content-Type': 'application/json'}
                    )
                    try:
                        urllib.request.urlopen(req, timeout=1)
                    except Exception:
                        pass
                    t_w1 = time.perf_counter()
                    write_latencies.append((t_w1 - t_w0) * 1000)
                except Exception:
                    pass

            def status_change_notification(self, status):
                pass

        handler = BaSyxSimHandler()
        subscription = await client.create_subscription(
            period=publishing_interval_ms, handler=handler
        )
        nodes = [client.get_node(nid) for nid in nodeids]
        await subscription.subscribe_data_change(nodes)

        result.start_time = datetime.now(timezone.utc).isoformat()
        start = time.time()
        while (time.time() - start) < duration_s:
            await asyncio.sleep(1.0)
            res_monitor.sample()

        handler._active = False
        result.end_time = datetime.now(timezone.utc).isoformat()
        result.duration_s = time.time() - start
        result.resources = res_monitor.stop()
        result.acquisition_latency = _compute_latency_stats(latencies)
        result.total_notifications = notifications
        result.acquisition_rate_hz = notifications / result.duration_s if result.duration_s > 0 else 0

        # Query latencies (simula GET ao servidor AAS)
        q_latencies = []
        for _ in range(50):
            t0 = time.perf_counter()
            try:
                urllib.request.urlopen("http://127.0.0.1:4999/submodel/value", timeout=1)
            except Exception:
                pass
            t1 = time.perf_counter()
            q_latencies.append((t1 - t0) * 1000)
        if q_latencies:
            arr = np.array(q_latencies)
            result.query_latencies = [QueryLatency(
                query_name="http_get_simulated", n_executions=len(q_latencies),
                mean_ms=float(np.mean(arr)), std_ms=float(np.std(arr)),
                p95_ms=float(np.percentile(arr, 95)), p99_ms=float(np.percentile(arr, 99)),
            )]

        # Write overhead
        if write_latencies:
            arr_w = np.array(write_latencies)
            result.storage_size_bytes = int(notifications * 100)  # ~100 bytes per PUT
            result.storage_size_mb = result.storage_size_bytes / (1024*1024)
            logger.info("[basyx-sim] HTTP PUT overhead: %.2f ± %.2f ms",
                        float(np.mean(arr_w)), float(np.std(arr_w)))

        try:
            await subscription.delete()
        except Exception:
            pass

    finally:
        await client.disconnect()
        httpd.shutdown()

    logger.info("[basyx-sim] Concluído: %d notificações", result.total_notifications)
    return result


# ══════════════════════════════════════════════════════════════════════════════════
# CENÁRIO (iii) SIMULADO: OVERHEAD DE TSDB (SQLite WAL como proxy de InfluxDB)
# ══════════════════════════════════════════════════════════════════════════════════
#
# Simula o overhead de escrever cada notificação em um banco de séries temporais.
# Usa SQLite em modo WAL (Write-Ahead Logging) — comportamento similar ao InfluxDB
# para escritas de pontos individuais. Mede:
# - Tempo de INSERT por ponto
# - Tamanho do banco resultante
# - Latência de consulta range
# ══════════════════════════════════════════════════════════════════════════════════

async def run_influxdb_simulated_scenario(
    server_url: str,
    duration_s: float,
    publishing_interval_ms: float = 200,
) -> ScenarioResult:
    """Cenário InfluxDB simulado: mede overhead de escrita em TSDB (via SQLite WAL)."""
    from asyncua import Client
    import sqlite3
    import tempfile

    result = ScenarioResult(
        scenario_name="influxdb_simulated",
        scenario_description="OPC UA + escrita TSDB simulada (SQLite WAL, 1 INSERT/notificação)",
    )
    result.config = {
        "server_url": server_url,
        "duration_s": duration_s,
        "publishing_interval_ms": publishing_interval_ms,
        "simulation": "SQLite WAL mode, 1 INSERT per notification (proxy InfluxDB)",
    }

    # Cria banco temporário
    tmp_db = tempfile.mktemp(suffix=".sqlite3", prefix="tsdb_bench_")
    con = sqlite3.connect(tmp_db, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("""
        CREATE TABLE measurements (
            id INTEGER PRIMARY KEY,
            ts TEXT NOT NULL,
            node_id TEXT NOT NULL,
            value REAL
        )
    """)
    con.execute("CREATE INDEX idx_ts ON measurements(ts)")
    con.commit()

    client = Client(url=server_url, timeout=10)
    await client.connect()
    logger.info("[influxdb-sim] Conectado ao OPC UA + SQLite WAL em %s", tmp_db)

    try:
        clock_offset = await _measure_clock_offset(client)
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            nodeids = _extract_nodeids(config)
        else:
            nodeids = ["ns=0;i=2258"]

        res_monitor = ResourceMonitor()
        res_monitor.start()

        latencies: List[float] = []
        write_latencies: List[float] = []
        notifications = 0
        records_written = 0

        class InfluxSimHandler:
            def __init__(self):
                self._active = True
                self._perf_offset = time.time() - time.perf_counter()

            def datachange_notification(self, node, val, data):
                nonlocal notifications, records_written
                if not self._active:
                    return
                t_receive = time.perf_counter() + self._perf_offset
                try:
                    source_ts = None
                    if hasattr(data, 'monitored_item') and hasattr(data.monitored_item, 'Value'):
                        dv = data.monitored_item.Value
                        if hasattr(dv, 'SourceTimestamp') and dv.SourceTimestamp:
                            source_ts = dv.SourceTimestamp.timestamp()
                    if source_ts is None:
                        return

                    latency_ms = (t_receive - source_ts) * 1000 - clock_offset
                    if abs(latency_ms) < 10000:
                        latencies.append(latency_ms)
                    notifications += 1

                    # Simula INSERT no TSDB
                    t_w0 = time.perf_counter()
                    try:
                        value = float(val) if val is not None else 0.0
                    except (TypeError, ValueError):
                        value = 0.0
                    nodeid_str = node.nodeid.to_string()
                    ts_str = datetime.fromtimestamp(source_ts, tz=timezone.utc).isoformat()
                    con.execute(
                        "INSERT INTO measurements(ts, node_id, value) VALUES (?,?,?)",
                        (ts_str, nodeid_str, value)
                    )
                    if notifications % 50 == 0:
                        con.commit()
                    records_written += 1
                    t_w1 = time.perf_counter()
                    write_latencies.append((t_w1 - t_w0) * 1000)
                except Exception:
                    pass

            def status_change_notification(self, status):
                pass

        handler = InfluxSimHandler()
        subscription = await client.create_subscription(
            period=publishing_interval_ms, handler=handler
        )
        nodes = [client.get_node(nid) for nid in nodeids]
        await subscription.subscribe_data_change(nodes)

        result.start_time = datetime.now(timezone.utc).isoformat()
        start = time.time()
        while (time.time() - start) < duration_s:
            await asyncio.sleep(1.0)
            res_monitor.sample()

        handler._active = False
        con.commit()
        result.end_time = datetime.now(timezone.utc).isoformat()
        result.duration_s = time.time() - start
        result.resources = res_monitor.stop()
        result.acquisition_latency = _compute_latency_stats(latencies)
        result.total_notifications = notifications
        result.acquisition_rate_hz = notifications / result.duration_s if result.duration_s > 0 else 0
        result.storage_records = records_written

        # Tamanho do banco
        result.storage_size_bytes = Path(tmp_db).stat().st_size
        result.storage_size_mb = result.storage_size_bytes / (1024 * 1024)

        # Query latency (range queries)
        q_results = []
        for name, sql in [
            ("tsdb_last", "SELECT * FROM measurements ORDER BY ts DESC LIMIT 1"),
            ("tsdb_range_100", "SELECT * FROM measurements ORDER BY ts DESC LIMIT 100"),
            ("tsdb_range_1000", "SELECT * FROM measurements ORDER BY ts DESC LIMIT 1000"),
            ("tsdb_count", "SELECT COUNT(*) FROM measurements"),
        ]:
            q_lat = []
            rows = 0
            for i in range(100):
                t0 = time.perf_counter()
                cur = con.execute(sql)
                r = cur.fetchall()
                t1 = time.perf_counter()
                q_lat.append((t1 - t0) * 1000)
                if i == 0:
                    rows = len(r)
            arr = np.array(q_lat)
            q_results.append(QueryLatency(
                query_name=name, n_executions=100,
                mean_ms=float(np.mean(arr)), std_ms=float(np.std(arr)),
                p95_ms=float(np.percentile(arr, 95)), p99_ms=float(np.percentile(arr, 99)),
                rows_returned=rows,
            ))
        result.query_latencies = q_results

        if write_latencies:
            arr_w = np.array(write_latencies)
            logger.info("[influxdb-sim] Write overhead: %.3f ± %.3f ms | DB: %.2f MB | Records: %d",
                        float(np.mean(arr_w)), float(np.std(arr_w)),
                        result.storage_size_mb, records_written)

        try:
            await subscription.delete()
        except Exception:
            pass

    finally:
        await client.disconnect()
        con.close()
        try:
            os.remove(tmp_db)
            os.remove(tmp_db + "-wal")
            os.remove(tmp_db + "-shm")
        except Exception:
            pass

    logger.info("[influxdb-sim] Concluído: %d notificações, %d escritas",
                result.total_notifications, records_written)
    return result


async def async_main(args):
    """Entry point assíncrono."""
    scenarios = []

    if args.scenario in ("baseline", "all"):
        logger.info("═" * 70)
        logger.info("  CENÁRIO (i): BASELINE — OPC UA direto")
        logger.info("═" * 70)
        r = await run_baseline_scenario(
            server_url=args.server, duration_s=args.duration,
            publishing_interval_ms=args.pub_interval,
        )
        scenarios.append(r)
        save_scenario_result(r, args.output)

    if args.scenario in ("basyx", "basyx-sim", "all"):
        logger.info("═" * 70)
        logger.info("  CENÁRIO (ii): SERVIDOR AAS (simulado - overhead HTTP+JSON)")
        logger.info("═" * 70)
        r = await run_basyx_simulated_scenario(
            server_url=args.server, duration_s=args.duration,
            publishing_interval_ms=args.pub_interval,
        )
        scenarios.append(r)
        save_scenario_result(r, args.output)

    if args.scenario in ("influxdb", "influxdb-sim", "all"):
        logger.info("═" * 70)
        logger.info("  CENÁRIO (iii): TSDB (simulado - overhead SQLite write-ahead)")
        logger.info("═" * 70)
        r = await run_influxdb_simulated_scenario(
            server_url=args.server, duration_s=args.duration,
            publishing_interval_ms=args.pub_interval,
        )
        scenarios.append(r)
        save_scenario_result(r, args.output)

    if len(scenarios) > 1:
        save_comparison(scenarios, args.output)


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark comparativo — AAS Robô SCARA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Cenários:
  baseline    Cliente OPC UA direto (sem AAS, sem persistência)
  basyx       OPC UA → servidor AAS aberto (Eclipse BaSyx/FA³ST)
  influxdb    Arquitetura proposta com InfluxDB ao invés de SQLite
  all         Executa todos os cenários em sequência

  --compare DIR   Carrega resultados anteriores e gera tabela comparativa

Pré-requisitos:
  baseline:  Acesso ao servidor OPC UA
  basyx:     Servidor BaSyx/FA³ST rodando (--basyx-url)
  influxdb:  InfluxDB 2.x rodando (env: INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET)
  psutil:    pip install psutil (para métricas de CPU/RAM)

Exemplos:
  python benchmarks/comparative_benchmark.py --scenario baseline --duration 300
  python benchmarks/comparative_benchmark.py --scenario all --duration 300
  python benchmarks/comparative_benchmark.py --compare benchmarks/results/
        """
    )
    parser.add_argument(
        "--scenario", type=str, default=None,
        choices=["baseline", "basyx", "basyx-sim", "influxdb", "influxdb-sim", "all"],
        help="Cenário a executar"
    )
    parser.add_argument(
        "--duration", "-d", type=float, default=300,
        help="Duração de cada cenário em segundos (default: 300 = 5 min)"
    )
    parser.add_argument(
        "--server", "-s", type=str, default=DEFAULT_SERVER,
        help="URL do servidor OPC UA"
    )
    parser.add_argument(
        "--pub-interval", type=float, default=200,
        help="Publishing interval em ms (default: 200)"
    )
    parser.add_argument(
        "--basyx-url", type=str, default="http://localhost:4001",
        help="URL do servidor BaSyx (default: http://localhost:4001)"
    )
    parser.add_argument(
        "--compare", type=str, default=None,
        help="Diretório com resultados anteriores para gerar tabela comparativa"
    )
    parser.add_argument(
        "--output", "-o", type=str, default="benchmarks/results",
        help="Diretório de saída (default: benchmarks/results/)"
    )

    args = parser.parse_args()

    if args.compare:
        load_and_compare(args.compare)
        return

    if args.scenario is None:
        parser.print_help()
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("  BENCHMARK COMPARATIVO — AAS Robô SCARA")
    logger.info("=" * 70)
    logger.info("Cenário: %s | Duração: %.0f s | Server: %s",
                args.scenario, args.duration, args.server)

    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
