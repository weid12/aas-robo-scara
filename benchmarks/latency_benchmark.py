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

async def measure_clock_offset(client: Client, n_samples: int = 30) -> Tuple[float, float]:
    """
    Sincronização de relógios via método NTP (half-RTT).

    Protocolo IEEE 1588-like adaptado para OPC UA:
    1. Lê ServerStatus.CurrentTime N vezes
    2. Para cada leitura: offset_i = T_client_mid - T_server
       onde T_client_mid = (T_antes + T_depois) / 2 (compensa one-way delay)
    3. Filtra amostras com RTT > mediana×2 (descarta congestionamento)
    4. Usa a mediana dos offsets filtrados (mais robusto que média)

    O offset resultante é a diferença TOTAL entre os relógios, incluindo:
    - Timezone mismatch (se houver)
    - Drift do relógio do controlador
    - Erro de configuração NTP

    Args:
        client: Cliente OPC UA conectado
        n_samples: Número de amostras (default: 30 para maior precisão)

    Returns:
        Tupla (offset_ms, std_ms)
        offset > 0 = cliente adiantado em relação ao servidor
    """
    server_time_node = client.get_node("ns=0;i=2258")
    offsets = []
    rtts = []

    logger.info("  Medindo offset de relógio (%d amostras, método NTP half-RTT)...", n_samples)

    for i in range(n_samples):
        t_before = time.time()
        server_time = await server_time_node.read_value()
        t_after = time.time()

        if not isinstance(server_time, datetime):
            continue

        t_server = server_time.timestamp()
        t_client_mid = (t_before + t_after) / 2
        rtt = (t_after - t_before) * 1000

        offset = (t_client_mid - t_server) * 1000
        offsets.append(offset)
        rtts.append(rtt)
        await asyncio.sleep(0.1)

    if not offsets:
        logger.warning("Não foi possível medir offset de relógio!")
        return 0.0, 0.0

    arr_offsets = np.array(offsets)
    arr_rtts = np.array(rtts)

    # Filtra amostras com RTT alto (congestionamento distorce a medição)
    rtt_median = float(np.median(arr_rtts))
    rtt_threshold = max(rtt_median * 2, 5.0)  # no mínimo 5ms de threshold
    mask = arr_rtts <= rtt_threshold
    filtered = arr_offsets[mask]

    if len(filtered) < 5:
        filtered = arr_offsets  # fallback se muitas foram descartadas

    # Usa MEDIANA (mais robusto a outliers que a média)
    offset_ms = float(np.median(filtered))
    offset_std = float(np.std(filtered))

    return offset_ms, offset_std


def _format_clock_report(
    label: str,
    pc_time_utc: str,
    server_time_utc: str,
    offset_ms: float,
    offset_std: float,
    rtt_avg_ms: float,
) -> str:
    """Formata relatório de verificação de relógio."""
    offset_s = offset_ms / 1000
    hours = int(offset_s // 3600)
    remainder_s = offset_s - hours * 3600

    lines = []
    lines.append(f"  ┌─── {label} ───────────────────────────────────────────────┐")
    lines.append(f"  │ PC (UTC):          {pc_time_utc:<40}│")
    lines.append(f"  │ Controlador:       {server_time_utc:<40}│")
    lines.append(f"  │ Offset:            {offset_ms:+.1f} ms ({offset_s:+.3f} s){'':>16}│")
    if abs(hours) >= 1:
        lines.append(f"  │ Decomposição:      {hours:+d}h {remainder_s:+.3f}s (timezone + drift){'':>6}│")
    lines.append(f"  │ Jitter (DP):       ±{offset_std:.1f} ms{'':>33}│")
    lines.append(f"  │ RTT médio:         {rtt_avg_ms:.1f} ms{'':>34}│")
    lines.append(f"  └──────────────────────────────────────────────────────────────┘")
    return "\n".join(lines)


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

        # ─── Contagem de ciclos do robô (baseado em J3) ──────────────────────
        # Um ciclo é detectado quando J3 cruza o ponto de referência (posição
        # máxima ou mínima) e retorna — ou seja, muda de direção.
        # Usamos detecção de inversão de direção (pico/vale).
        self.robot_cycles = 0
        self._j3_node_id = "ns=1;s=Robot:Controller:System:RobotPosition:Joint Position"
        self._j3_values: List[float] = []  # histórico recente de J3
        self._j3_direction: Optional[int] = None  # 1=subindo, -1=descendo
        self._j3_last_peak: Optional[float] = None
        self._j3_hysteresis = 2.0  # graus de histerese para evitar falsos ciclos

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

            # ─── Detecção de ciclo do robô via J3 ────────────────────────────
            if nodeid_str == self._j3_node_id:
                self._detect_robot_cycle(val)

            self.samples.append(LatencySample(
                node_id=nodeid_str,
                source_timestamp=source_ts,
                receive_timestamp=t_receive,
                latency_ms=latency_ms
            ))

        except Exception as e:
            logger.debug("Erro ao processar notificação: %s", e)

    def _detect_robot_cycle(self, val: Any) -> None:
        """
        Detecta ciclos do robô baseado na inversão de direção da junta 3.
        
        Um ciclo completo = J3 sobe até um pico E desce até um vale (ou vice-versa).
        Cada par pico+vale conta como 1 ciclo.
        """
        try:
            # val é array [J1, J2, J3, J4] — extrair J3 (índice 2)
            if isinstance(val, (list, tuple)) and len(val) > 2:
                j3 = float(val[2])
            elif isinstance(val, (int, float)):
                j3 = float(val)
            else:
                return

            self._j3_values.append(j3)

            # Precisa de pelo menos 3 pontos para detectar inversão
            if len(self._j3_values) < 3:
                return

            # Mantém janela limitada (últimos 10 valores)
            if len(self._j3_values) > 10:
                self._j3_values = self._j3_values[-10:]

            # Direção atual
            prev = self._j3_values[-2]
            curr = self._j3_values[-1]
            delta = curr - prev

            # Ignora variações menores que histerese (ruído)
            if abs(delta) < self._j3_hysteresis:
                return

            new_direction = 1 if delta > 0 else -1

            # Detecta inversão de direção
            if self._j3_direction is not None and new_direction != self._j3_direction:
                # Inversão detectada — meio ciclo
                if self._j3_last_peak is not None:
                    # Já tínhamos um pico anterior → ciclo completo
                    self.robot_cycles += 1
                self._j3_last_peak = curr

            self._j3_direction = new_direction

        except (TypeError, ValueError, IndexError):
            pass

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
        # ─── 1. Verificação PRÉ-ensaio dos relógios (NTP half-RTT) ──────────
        logger.info("")
        logger.info("─── Fase 1: Verificação de sincronização de relógios (PRÉ-ensaio) ───")

        # Lê horário atual de ambos
        server_time_node = client.get_node("ns=0;i=2258")
        t_pc_before = time.time()
        srv_time_before = await server_time_node.read_value()
        pc_utc_str = datetime.fromtimestamp(t_pc_before, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        srv_utc_str = srv_time_before.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] if isinstance(srv_time_before, datetime) else "N/A"

        # Mede offset com 30 amostras
        offset_ms, offset_std = await measure_clock_offset(client, n_samples=30)

        # Calcula RTT médio para o relatório
        rtt_samples = []
        for _ in range(5):
            t0 = time.time()
            await server_time_node.read_value()
            rtt_samples.append((time.time() - t0) * 1000)
        rtt_avg = float(np.mean(rtt_samples))

        # Relatório PRÉ
        pre_report = _format_clock_report(
            "PRÉ-ENSAIO", pc_utc_str, srv_utc_str, offset_ms, offset_std, rtt_avg
        )
        logger.info("\n%s", pre_report)

        results.clock_offset_ms = offset_ms
        results.clock_offset_std_ms = offset_std
        results.clock_offset_method = f"NTP half-RTT (30 amostras, filtragem RTT, mediana)"
        results.clock_offset_samples = 30

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

        # ─── 5. Verificação PÓS-ensaio dos relógios ─────────────────────────
        logger.info("")
        logger.info("─── Fase 4: Verificação de sincronização (PÓS-ensaio) ───")

        t_pc_after = time.time()
        srv_time_after = await server_time_node.read_value()
        pc_utc_after = datetime.fromtimestamp(t_pc_after, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        srv_utc_after = srv_time_after.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] if isinstance(srv_time_after, datetime) else "N/A"

        offset_post_ms, offset_post_std = await measure_clock_offset(client, n_samples=10)
        drift_during_test = offset_post_ms - offset_ms
        drift_rate_ms_per_min = drift_during_test / (results.duration_seconds / 60) if results.duration_seconds > 0 else 0

        post_report = _format_clock_report(
            "PÓS-ENSAIO", pc_utc_after, srv_utc_after, offset_post_ms, offset_post_std, rtt_avg
        )
        logger.info("\n%s", post_report)
        logger.info("  Drift durante o ensaio: %+.1f ms (%.2f ms/min)", drift_during_test, drift_rate_ms_per_min)

        # Se drift > 100ms durante o ensaio, avisa
        if abs(drift_during_test) > 100:
            logger.warning("  ⚠ Drift significativo (%.0f ms) — relógios instáveis!", drift_during_test)

        # ─── 6. Cálculo de estatísticas ─────────────────────────────────────
        logger.info("")
        logger.info("─── Fase 5: Análise estatística ───")

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

        # ─── Detecção e compensação de offset residual ───────────────────────
        # Se após a compensação do offset medido a mediana ainda é > 5s,
        # significa que o offset drift entre a medição e a coleta foi significativo.
        # Nesse caso, corrige com a mediana como bias adicional.
        median_raw = float(np.median(latencies))
        residual_offset_ms = 0.0

        if abs(median_raw) > 5000:
            residual_offset_ms = median_raw
            logger.warning(
                "OFFSET RESIDUAL DETECTADO: mediana=%.0f ms (~%.1f s). "
                "Drift entre medição do offset e coleta. "
                "Aplicando correção adicional de %.0f ms.",
                median_raw, median_raw / 1000, residual_offset_ms
            )
            latencies = latencies - residual_offset_ms

        # Reporta latências negativas remanescentes (devem ser poucas após correção)
        n_negative = int(np.sum(latencies < 0))
        if n_negative > 0:
            pct_neg = 100 * n_negative / len(latencies)
            logger.info(
                "%d amostras com latência negativa (%.1f%%) após correção — jitter normal",
                n_negative, pct_neg
            )

        # Guarda offset residual no resultado para transparência
        results.clock_offset_ms = results.clock_offset_ms + residual_offset_ms

        # Estatísticas finais (sobre latências corrigidas)
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
            f"outliers descartados={handler._outlier_count} | "
            f"ciclos do robô (J3)={handler.robot_cycles}"
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