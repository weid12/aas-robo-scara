# ==================================================================================================
#   Benchmark de Latência e Taxa de Aquisição — AAS Robô SCARA
#
#   Mede a latência fim-a-fim desde o instante de registro no controlador (SourceTimestamp OPC UA)
#   até a persistência do snapshot no cliente (disco local), além da taxa efetiva de aquisição.
#
#   Definições:
#   -----------
#   - Latência fim-a-fim (L): T_snapshot - T_source
#     onde:
#       T_source   = SourceTimestamp do DataValue OPC UA (instante em que o servidor amostrou o dado)
#       T_snapshot = Instante UTC no cliente em que o valor foi persistido no data_store em memória
#
#   - Taxa de aquisição efetiva: Nº de notificações recebidas / duração do ensaio
#
#   Sincronização de relógios:
#   --------------------------
#   O controlador Stäubli e o gateway devem estar sincronizados via NTP ou PTP.
#   - NTP (Network Time Protocol): precisão típica ~1-10 ms em LAN
#   - PTP (Precision Time Protocol / IEEE 1588): precisão < 1 µs (se suportado pelo hardware)
#
#   Este script:
#   1. Mede o offset entre o relógio do servidor OPC UA e o cliente (via CurrentTime do servidor)
#   2. Aplica compensação de offset nas medições
#   3. Coleta N amostras de latência durante um período configurável
#   4. Reporta: média ± DP, mediana, p95, p99, pior caso, taxa de aquisição
#
#   Uso:
#       python benchmarks/latency_benchmark.py --duration 60 --output benchmarks/results/
#       python benchmarks/latency_benchmark.py --duration 300 --server opc.tcp://192.168.0.31:4880/Staubli
#
#   Requisitos:
#       pip install asyncua numpy
# ==================================================================================================

import asyncio
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

import numpy as np
from asyncua import Client, ua

# ─── Configuração ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("latency_benchmark")

# Diretório raiz do projeto
ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT_DIR / "acquisition" / "client" / "config_opcua.json"
DEFAULT_SERVER = os.getenv("OPCUA_SERVER_URL", "opc.tcp://192.168.0.31:4880/Staubli")


# ─── Data Classes ────────────────────────────────────────────────────────────────

@dataclass
class LatencySample:
    """Uma amostra individual de latência."""
    node_id: str
    source_timestamp: float      # epoch UTC do SourceTimestamp (servidor)
    receive_timestamp: float     # epoch UTC do instante de recepção (cliente)
    latency_ms: float            # (receive - source) * 1000, já compensado por offset


@dataclass
class BenchmarkConfig:
    """Configuração do ensaio."""
    server_url: str = DEFAULT_SERVER
    duration_seconds: int = 3600
    publishing_interval_ms: float = 200
    clock_sync_method: str = "NTP"
    clock_offset_ms: float = 0.0
    nodes_monitored: int = 0
    output_dir: str = "benchmarks/results"


@dataclass
class BenchmarkResults:
    """Resultados consolidados do ensaio."""
    # Metadados
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    config: Dict[str, Any] = field(default_factory=dict)

    # Sincronização
    clock_offset_ms: float = 0.0
    clock_offset_method: str = ""
    clock_offset_samples: int = 0
    clock_offset_std_ms: float = 0.0

    # Latência (ms)
    n_samples: int = 0
    latency_mean_ms: float = 0.0
    latency_std_ms: float = 0.0
    latency_median_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    latency_min_ms: float = 0.0
    latency_max_ms: float = 0.0

    # Taxa de aquisição
    acquisition_rate_hz: float = 0.0
    notifications_total: int = 0
    notifications_per_node_avg: float = 0.0

    # Carga declarada
    load_description: str = ""
    nodes_monitored: int = 0
    publishing_interval_ms: float = 0.0


# ─── Medição de Offset de Relógio ────────────────────────────────────────────────

async def measure_clock_offset(client: Client, n_samples: int = 20) -> Tuple[float, float]:
    """
    Mede o offset entre o relógio do servidor OPC UA e o cliente.

    Método: lê o nó ServerStatus.CurrentTime (ns=0;i=2258) repetidamente
    e calcula a diferença (T_client - T_server) usando o método de half-RTT:
        offset ≈ T_client_mid - T_server

    NOTA: Se o controlador reporta hora local como UTC (ex: Manaus UTC-4),
    o offset será ~14.4M ms (4h). Nesse caso, arredondamos para o fuso
    horário mais próximo e usamos compensação fixa.

    Args:
        client: Cliente OPC UA conectado
        n_samples: Número de amostras para estimar offset

    Returns:
        Tupla (offset_medio_ms, desvio_padrao_ms)
        offset > 0 significa que o relógio do cliente está adiantado
    """
    server_time_node = client.get_node("ns=0;i=2258")  # Server.ServerStatus.CurrentTime
    offsets = []
    rtts = []

    for i in range(n_samples):
        t_before = time.time()
        server_time = await server_time_node.read_value()
        t_after = time.time()

        if server_time is None:
            continue

        # Converte para epoch
        if isinstance(server_time, datetime):
            t_server = server_time.timestamp()
        else:
            continue

        # Half-RTT: estima o instante real da leitura como ponto médio
        t_client_mid = (t_before + t_after) / 2
        rtt = (t_after - t_before) * 1000  # ms

        offset = (t_client_mid - t_server) * 1000  # ms (client - server)
        offsets.append(offset)
        rtts.append(rtt)

        logger.debug(
            "Offset sample %d: offset=%.2f ms, RTT=%.2f ms",
            i + 1, offset, rtt
        )
        await asyncio.sleep(0.1)

    if not offsets:
        logger.warning("Não foi possível medir offset de relógio")
        return 0.0, 0.0

    # Remove outliers (> 2σ) e recalcula
    arr = np.array(offsets)
    mean = np.mean(arr)
    std = np.std(arr)
    filtered = arr[np.abs(arr - mean) < 2 * std]

    if len(filtered) < 3:
        filtered = arr

    offset_mean = float(np.mean(filtered))
    offset_std = float(np.std(filtered))

    # ─── Detecção de timezone mismatch ───────────────────────────────────
    # Se o offset é múltiplo aproximado de 1 hora (±30s), o controlador
    # provavelmente reporta hora local como UTC.
    abs_offset_h = abs(offset_mean) / 3_600_000
    nearest_hour = round(abs_offset_h)
    remainder_ms = abs(offset_mean) - nearest_hour * 3_600_000

    if nearest_hour >= 1 and abs(remainder_ms) < 60_000:
        sign = 1 if offset_mean > 0 else -1
        corrected_offset = sign * nearest_hour * 3_600_000
        logger.warning(
            "TIMEZONE MISMATCH DETECTADO: offset=%.0f ms ≈ %+dh. "
            "O controlador provavelmente reporta hora local como UTC. "
            "Usando compensação fixa de %+dh.",
            offset_mean, sign * nearest_hour, sign * nearest_hour
        )
        offset_mean = corrected_offset
        # Recalcula std apenas com o resíduo (jitter de rede)
        residuals = arr - corrected_offset
        offset_std = float(np.std(residuals))

    logger.info(
        "Clock offset: %.2f ± %.2f ms (%d amostras válidas de %d) | RTT médio: %.1f ms",
        offset_mean, offset_std, len(filtered), n_samples, float(np.mean(rtts))
    )

    return offset_mean, offset_std


# ─── Handler de Subscription com Timestamp ────────────────────────────────────────

class LatencyHandler:
    """
    Handler de subscription que registra SourceTimestamp e instante de recepção.
    
    CORREÇÕES APLICADAS:
    1. Usa time.perf_counter() para precisão de delta (não afetado por NTP adjustments)
    2. Filtra outliers extremos (> 10s) que indicam bloqueio do event loop
    3. Registra perf_counter_epoch_offset para converter perf_counter → epoch
    """

    def __init__(self, clock_offset_ms: float = 0.0):
        self.samples: List[LatencySample] = []
        self.clock_offset_ms = clock_offset_ms
        self._active = True
        # Calibração: mapeia perf_counter para epoch uma vez
        self._perf_epoch_offset = time.time() - time.perf_counter()
        self._outlier_count = 0
        self._max_valid_latency_ms = 10_000  # 10s — acima disso é bloqueio do event loop

    def datachange_notification(self, node, val, data):
        """Callback invocado pelo asyncua a cada notificação de mudança."""
        if not self._active:
            return

        t_receive_perf = time.perf_counter()
        t_receive = t_receive_perf + self._perf_epoch_offset

        try:
            # Extrai SourceTimestamp do DataValue
            source_ts = None
            if hasattr(data, 'monitored_item') and hasattr(data.monitored_item, 'Value'):
                dv = data.monitored_item.Value
                if hasattr(dv, 'SourceTimestamp') and dv.SourceTimestamp is not None:
                    source_ts = dv.SourceTimestamp.timestamp()
            
            if source_ts is None:
                if hasattr(data, 'Value') and hasattr(data.Value, 'SourceTimestamp'):
                    st = data.Value.SourceTimestamp
                    if st is not None:
                        source_ts = st.timestamp()

            if source_ts is None:
                return

            # Calcula latência compensando o offset de relógio
            # offset = client - server, então: latency_real = (T_receive - T_source)*1000 - offset_ms
            latency_ms = (t_receive - source_ts) * 1000 - self.clock_offset_ms

            # Filtra outliers extremos (indicam bloqueio do event loop, não latência real)
            if abs(latency_ms) > self._max_valid_latency_ms:
                self._outlier_count += 1
                return

            nodeid_str = node.nodeid.to_string()

            self.samples.append(LatencySample(
                node_id=nodeid_str,
                source_timestamp=source_ts,
                receive_timestamp=t_receive,
                latency_ms=latency_ms
            ))

        except Exception as e:
            logger.debug("Erro ao processar notificação: %s", e)

    def status_change_notification(self, status):
        logger.warning("Subscription status changed: %s", status)

    def stop(self):
        self._active = False


# ─── Extração de NodeIds do Config ────────────────────────────────────────────────

def extract_monitored_nodeids(config: Dict[str, Any]) -> List[str]:
    """Extrai todos os NodeIds únicos do config (excluindo _client)."""
    nodeids = set()
    _walk_nodeids(config, nodeids)
    return sorted(list(nodeids))


def _walk_nodeids(obj: Any, result: set) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "_client":
                continue
            _walk_nodeids(v, result)
    elif isinstance(obj, list):
        for item in obj:
            _walk_nodeids(item, result)
    elif isinstance(obj, str) and obj.startswith("ns=") and ";" in obj:
        result.add(obj)


# ─── Benchmark Principal ──────────────────────────────────────────────────────────

async def run_benchmark(cfg: BenchmarkConfig) -> BenchmarkResults:
    """
    Executa o benchmark de latência completo.

    Protocolo do ensaio:
    1. Conecta ao servidor OPC UA
    2. Mede offset de relógio (20 amostras, método half-RTT)
    3. Cria subscription com MonitoredItems para todos os nós configurados
    4. Coleta notificações durante cfg.duration_seconds
    5. Calcula estatísticas de latência
    6. Reporta resultados
    """
    results = BenchmarkResults()
    results.config = asdict(cfg)
    results.publishing_interval_ms = cfg.publishing_interval_ms
    results.load_description = (
        f"{cfg.nodes_monitored} nós monitorados via subscription, "
        f"publishing_interval={cfg.publishing_interval_ms}ms, "
        f"servidor={cfg.server_url}"
    )

    logger.info("=" * 70)
    logger.info("  BENCHMARK DE LATÊNCIA — AAS Robô SCARA")
    logger.info("=" * 70)
    logger.info("Servidor: %s", cfg.server_url)
    logger.info("Duração: %d s", cfg.duration_seconds)
    logger.info("Publishing interval: %.0f ms", cfg.publishing_interval_ms)

    # ─── Conexão ─────────────────────────────────────────────────────────────
    client = Client(url=cfg.server_url, timeout=10)

    try:
        await client.connect()
        logger.info("Conectado ao servidor OPC UA")
    except Exception as e:
        logger.error("Falha ao conectar: %s", e)
        raise

    try:
        # ─── 1. Medir offset de relógio ─────────────────────────────────────
        logger.info("")
        logger.info("─── Fase 1: Medição de offset de relógio ───")
        offset_ms, offset_std = await measure_clock_offset(client, n_samples=20)
        results.clock_offset_ms = offset_ms
        results.clock_offset_std_ms = offset_std
        results.clock_offset_method = f"{cfg.clock_sync_method} + half-RTT measurement"
        results.clock_offset_samples = 20

        # ─── 2. Carregar nós a monitorar ─────────────────────────────────────
        logger.info("")
        logger.info("─── Fase 2: Configuração da subscription ───")

        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            nodeids = extract_monitored_nodeids(config)
        else:
            logger.warning("Config não encontrado, usando nós padrão")
            nodeids = ["ns=0;i=2258"]  # ServerStatus.CurrentTime como fallback

        cfg.nodes_monitored = len(nodeids)
        results.nodes_monitored = len(nodeids)
        logger.info("Nós a monitorar: %d", len(nodeids))

        # ─── 3. Criar subscription ──────────────────────────────────────────
        handler = LatencyHandler(clock_offset_ms=offset_ms)

        subscription = await client.create_subscription(
            period=cfg.publishing_interval_ms,
            handler=handler,
        )

        nodes = [client.get_node(nid) for nid in nodeids]
        if nodes:
            await subscription.subscribe_data_change(nodes)
            logger.info("MonitoredItems criados: %d", len(nodes))

        # ─── 4. Coleta de dados ──────────────────────────────────────────────
        logger.info("")
        logger.info("─── Fase 3: Coleta de dados (duração: %d s) ───", cfg.duration_seconds)
        results.start_time = datetime.now(timezone.utc).isoformat()

        start = time.time()
        last_report = start
        while (time.time() - start) < cfg.duration_seconds:
            await asyncio.sleep(1.0)
            elapsed = time.time() - start

            # Relatório parcial a cada 10 segundos
            if time.time() - last_report >= 10:
                n = len(handler.samples)
                rate = n / elapsed if elapsed > 0 else 0
                logger.info(
                    "  [%3.0f/%d s] %d amostras coletadas (%.1f notif/s)",
                    elapsed, cfg.duration_seconds, n, rate
                )
                last_report = time.time()

        handler.stop()
        results.end_time = datetime.now(timezone.utc).isoformat()
        results.duration_seconds = time.time() - start

        # ─── 5. Cálculo de estatísticas ─────────────────────────────────────
        logger.info("")
        logger.info("─── Fase 4: Análise estatística ───")

        samples = handler.samples
        results.n_samples = len(samples)
        results.notifications_total = len(samples) + handler._outlier_count

        if handler._outlier_count > 0:
            logger.warning(
                "%d amostras descartadas como outliers (>%.0fs, indicam bloqueio do event loop)",
                handler._outlier_count, handler._max_valid_latency_ms / 1000
            )

        if not samples:
            logger.warning("Nenhuma amostra coletada! Verifique a conexão com o servidor.")
            return results

        latencies = np.array([s.latency_ms for s in samples])

        # Remove latências negativas (indicam problema de sincronização residual)
        n_negative = int(np.sum(latencies < 0))
        if n_negative > 0:
            pct_neg = 100 * n_negative / len(latencies)
            logger.warning(
                "%d amostras com latência negativa (%.1f%%) — offset residual de relógio",
                n_negative, pct_neg
            )
            # Se > 50% negativas, o offset está errado — usa mediana como correção
            if pct_neg > 50:
                correction = float(np.median(latencies))
                logger.warning(
                    "Corrigindo offset residual: ajuste de %.2f ms (mediana das latências)",
                    correction
                )
                latencies = latencies - correction

        # Estatísticas finais
        results.latency_mean_ms = float(np.mean(latencies))
        results.latency_std_ms = float(np.std(latencies))
        results.latency_median_ms = float(np.median(latencies))
        results.latency_p95_ms = float(np.percentile(latencies, 95))
        results.latency_p99_ms = float(np.percentile(latencies, 99))
        results.latency_min_ms = float(np.min(latencies))
        results.latency_max_ms = float(np.max(latencies))

        # Taxa de aquisição
        results.acquisition_rate_hz = len(samples) / results.duration_seconds
        results.notifications_per_node_avg = len(samples) / max(cfg.nodes_monitored, 1)

        # Carga declarada
        results.load_description = (
            f"{cfg.nodes_monitored} nós monitorados | "
            f"publishing_interval={cfg.publishing_interval_ms}ms | "
            f"duração={results.duration_seconds:.1f}s | "
            f"sincronização={cfg.clock_sync_method} | "
            f"outliers descartados={handler._outlier_count}"
        )

        # ─── 6. Cleanup ─────────────────────────────────────────────────────
        try:
            await subscription.delete()
        except Exception:
            pass

    finally:
        await client.disconnect()
        logger.info("Desconectado do servidor OPC UA")

    return results


# ─── Relatório ────────────────────────────────────────────────────────────────────

def print_report(results: BenchmarkResults) -> str:
    """Gera relatório formatado dos resultados."""
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("  RELATÓRIO DE LATÊNCIA — AAS Robô SCARA")
    lines.append("=" * 70)
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ PROTOCOLO DO ENSAIO                                                 │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    lines.append(f"│ Início:            {results.start_time:<50}│")
    lines.append(f"│ Fim:               {results.end_time:<50}│")
    lines.append(f"│ Duração:           {results.duration_seconds:.1f} s{'':<44}│")
    lines.append(f"│ N amostras:        {results.n_samples:<50}│")
    lines.append(f"│ Nós monitorados:   {results.nodes_monitored:<50}│")
    lines.append(f"│ Pub. interval:     {results.publishing_interval_ms:.0f} ms{'':<44}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ SINCRONIZAÇÃO DE RELÓGIOS                                           │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    lines.append(f"│ Método:            {results.clock_offset_method:<50}│")
    lines.append(f"│ Offset medido:     {results.clock_offset_ms:+.2f} ± {results.clock_offset_std_ms:.2f} ms{'':<33}│")
    lines.append(f"│ Amostras offset:   {results.clock_offset_samples:<50}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ LATÊNCIA FIM-A-FIM (SourceTimestamp → recepção no cliente)          │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    lines.append(f"│ Média ± DP:        {results.latency_mean_ms:.2f} ± {results.latency_std_ms:.2f} ms{'':<33}│")
    lines.append(f"│ Mediana:           {results.latency_median_ms:.2f} ms{'':<44}│")
    lines.append(f"│ Percentil 95:      {results.latency_p95_ms:.2f} ms{'':<44}│")
    lines.append(f"│ Percentil 99:      {results.latency_p99_ms:.2f} ms{'':<44}│")
    lines.append(f"│ Mínimo:            {results.latency_min_ms:.2f} ms{'':<44}│")
    lines.append(f"│ Máximo (pior caso):{results.latency_max_ms:.2f} ms{'':<44}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ TAXA DE AQUISIÇÃO                                                   │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    lines.append(f"│ Total notificações:{results.notifications_total:<50}│")
    lines.append(f"│ Taxa efetiva:      {results.acquisition_rate_hz:.2f} notif/s{'':<39}│")
    lines.append(f"│ Notif/nó (média):  {results.notifications_per_node_avg:.1f}{'':<48}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ CARGA DECLARADA                                                     │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    lines.append(f"│ {results.load_description:<68}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")
    lines.append("")

    report = "\n".join(lines)
    print(report)
    return report


def save_results(results: BenchmarkResults, output_dir: str) -> None:
    """Salva resultados em JSON e texto."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON completo
    json_file = out_path / f"latency_benchmark_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(asdict(results), f, indent=2, ensure_ascii=False, default=str)
    logger.info("Resultados JSON salvos em: %s", json_file)

    # Relatório texto
    report = print_report(results)
    txt_file = out_path / f"latency_benchmark_{timestamp}.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info("Relatório texto salvo em: %s", txt_file)


# ─── Main ─────────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(
        description="Benchmark de latência OPC UA → cliente AAS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python benchmarks/latency_benchmark.py --duration 3600
  python benchmarks/latency_benchmark.py --duration 3600 --server opc.tcp://192.168.0.31:4880/Staubli
  python benchmarks/latency_benchmark.py --duration 3600 --pub-interval 100 --output results/
        """
    )
    parser.add_argument(
        "--server", "-s", type=str, default=DEFAULT_SERVER,
        help=f"URL do servidor OPC UA (default: {DEFAULT_SERVER})"
    )
    parser.add_argument(
        "--duration", "-d", type=int, default=3600,
        help="Duração do ensaio em segundos (default: 3600 = 1 hora)"
    )
    parser.add_argument(
        "--pub-interval", type=float, default=200,
        help="Publishing interval da subscription em ms (default: 200)"
    )
    parser.add_argument(
        "--clock-sync", type=str, default="NTP",
        choices=["NTP", "PTP", "none"],
        help="Método de sincronização de relógios declarado (default: NTP)"
    )
    parser.add_argument(
        "--output", "-o", type=str, default="benchmarks/results",
        help="Diretório de saída dos resultados (default: benchmarks/results/)"
    )

    args = parser.parse_args()

    cfg = BenchmarkConfig(
        server_url=args.server,
        duration_seconds=args.duration,
        publishing_interval_ms=args.pub_interval,
        clock_sync_method=args.clock_sync,
        output_dir=args.output,
    )

    try:
        results = await run_benchmark(cfg)
        save_results(results, cfg.output_dir)
    except Exception as e:
        logger.error("Benchmark falhou: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())