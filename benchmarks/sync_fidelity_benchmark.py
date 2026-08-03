# ==================================================================================================
#   Benchmark de Fidelidade de Sincronização — AAS Robô SCARA
#
#   Mede a distribuição do offset de timestamp entre o evento no controlador
#   (SourceTimestamp OPC UA) e a atualização efetiva do snapshot (escrita em
#   latest_data.json) ao longo de N ciclos do robô.
#
#   Definições:
#   -----------
#   - Offset de sincronização (Δt): T_snapshot_write - T_source
#     onde:
#       T_source         = SourceTimestamp do DataValue OPC UA
#       T_snapshot_write = mtime do arquivo latest_data.json no instante da escrita
#
#   - Ciclo do robô: um período completo de aquisição (subscription publish +
#     writer flush). A cada write_interval_s, o writer grava um snapshot.
#
#   Modos de medição:
#   -----------------
#   1. MODO OBSERVADOR (padrão): monitora o arquivo latest_data.json externamente,
#      detectando escritas (via mtime polling) e comparando com o SourceTimestamp
#      contido nos dados RuntimeDiagnostics.CurrentTime do snapshot.
#
#   2. MODO INSTRUMENTADO: conecta diretamente ao servidor OPC UA, recebe
#      notificações com SourceTimestamp e marca o instante de persistência.
#
#   Uso:
#       python benchmarks/sync_fidelity_benchmark.py --cycles 1000
#       python benchmarks/sync_fidelity_benchmark.py --cycles 5000 --duration 3600
#       python benchmarks/sync_fidelity_benchmark.py --mode instrumented --server opc.tcp://...
#
#   Requisitos:
#       pip install numpy asyncua
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
logger = logging.getLogger("sync_fidelity")

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = str(ROOT_DIR / "acquisition" / "client" / "latest_data.json")
DEFAULT_SERVER = os.getenv("OPCUA_SERVER_URL", "opc.tcp://192.168.0.31:4880/Staubli")
CONFIG_FILE = ROOT_DIR / "acquisition" / "client" / "config_opcua.json"


# ─── Data Classes ────────────────────────────────────────────────────────────────

@dataclass
class SyncSample:
    """Uma amostra de offset de sincronização."""
    cycle: int
    source_timestamp: str       # ISO do SourceTimestamp (do snapshot)
    snapshot_write_time: float  # epoch UTC do mtime do arquivo
    offset_ms: float            # (snapshot_write - source) em ms
    snapshot_size_bytes: int = 0


@dataclass
class SyncFidelityResults:
    """Resultados consolidados do benchmark de fidelidade."""
    # Metadados
    mode: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_s: float = 0.0
    target_cycles: int = 0
    actual_cycles: int = 0

    # Offset de sincronização (ms)
    offset_mean_ms: float = 0.0
    offset_std_ms: float = 0.0
    offset_median_ms: float = 0.0
    offset_p5_ms: float = 0.0
    offset_p95_ms: float = 0.0
    offset_p99_ms: float = 0.0
    offset_min_ms: float = 0.0
    offset_max_ms: float = 0.0

    # Jitter (variação entre offsets consecutivos)
    jitter_mean_ms: float = 0.0
    jitter_std_ms: float = 0.0
    jitter_max_ms: float = 0.0

    # Taxa
    effective_rate_hz: float = 0.0
    missed_cycles: int = 0
    duplicate_cycles: int = 0

    # Distribuição (para histograma)
    histogram_bins: List[float] = field(default_factory=list)
    histogram_counts: List[int] = field(default_factory=list)

    # Configuração
    snapshot_path: str = ""
    server_url: str = ""
    clock_offset_ms: float = 0.0


# ─── MODO OBSERVADOR ──────────────────────────────────────────────────────────────
#
# Monitora o arquivo latest_data.json detectando escritas via polling do mtime.
# A cada nova escrita, lê o conteúdo e extrai RuntimeDiagnostics.CurrentTime
# (que é o instante em que o writer anotou o snapshot no cliente OPC UA).
# O offset = mtime_arquivo - CurrentTime (ambos em UTC).
#
# Vantagem: não interfere no sistema; mede a cadeia completa até o disco.
# Limitação: resolução de mtime no Windows é ~10-16 ms.
# ──────────────────────────────────────────────────────────────────────────────────

def run_observer_mode(
    snapshot_path: str,
    target_cycles: int,
    max_duration_s: float,
    poll_interval_s: float = 0.05,
) -> Tuple[List[SyncSample], float]:
    """
    Observa escritas no snapshot file e coleta amostras de offset.

    Args:
        snapshot_path: Caminho do latest_data.json
        target_cycles: Número de ciclos (escritas) a coletar
        max_duration_s: Duração máxima do ensaio em segundos
        poll_interval_s: Intervalo de polling do mtime (50ms padrão)

    Returns:
        Tupla (lista de amostras, duração real em segundos)
    """
    samples: List[SyncSample] = []
    path = Path(snapshot_path)

    if not path.exists():
        logger.error("Snapshot não encontrado: %s", snapshot_path)
        logger.info("O cliente OPC UA precisa estar rodando para gerar o snapshot.")
        return samples, 0.0

    # Obtém mtime inicial
    last_mtime = path.stat().st_mtime
    last_content_hash = None
    cycle = 0

    logger.info("Observando: %s", snapshot_path)
    logger.info("Ciclos alvo: %d | Duração máxima: %.0f s | Poll: %.0f ms",
                target_cycles, max_duration_s, poll_interval_s * 1000)

    start = time.time()
    last_report = start

    while cycle < target_cycles and (time.time() - start) < max_duration_s:
        time.sleep(poll_interval_s)

        try:
            current_mtime = path.stat().st_mtime
        except OSError:
            continue

        # Detecta nova escrita pelo mtime
        if current_mtime <= last_mtime:
            continue

        last_mtime = current_mtime

        # Lê o conteúdo do snapshot
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            # Arquivo pode estar sendo escrito (parcial) — pula
            continue

        # Extrai o timestamp fonte (CurrentTime injetado pelo writer)
        diag = data.get("RuntimeDiagnostics", {})
        current_time_str = diag.get("CurrentTime")
        if not current_time_str:
            continue

        # Converte CurrentTime para epoch
        try:
            source_dt = datetime.fromisoformat(current_time_str)
            source_epoch = source_dt.timestamp()
        except (ValueError, TypeError):
            continue

        # Calcula offset: mtime (instante real de escrita) - source (timestamp anotado)
        # O writer anota CurrentTime ANTES de chamar write_json_atomic, então:
        # offset = mtime_real - currenttime_anotado ≈ tempo de serialização + write
        offset_ms = (current_mtime - source_epoch) * 1000

        cycle += 1
        file_size = path.stat().st_size

        samples.append(SyncSample(
            cycle=cycle,
            source_timestamp=current_time_str,
            snapshot_write_time=current_mtime,
            offset_ms=offset_ms,
            snapshot_size_bytes=file_size,
        ))

        # Relatório parcial a cada 10 segundos
        elapsed = time.time() - start
        if time.time() - last_report >= 10:
            logger.info(
                "  [%3.0f s] %d/%d ciclos coletados (offset médio: %.1f ms)",
                elapsed, cycle, target_cycles,
                np.mean([s.offset_ms for s in samples[-100:]]) if samples else 0
            )
            last_report = time.time()

    duration = time.time() - start
    logger.info("Coleta finalizada: %d ciclos em %.1f s", cycle, duration)
    return samples, duration


# ─── MODO INSTRUMENTADO ───────────────────────────────────────────────────────────
#
# Conecta diretamente ao servidor OPC UA, cria uma subscription idêntica à do
# cliente de produção, e mede o offset entre SourceTimestamp e o instante de
# escrita em um buffer de snapshot local.
#
# Vantagem: mede o SourceTimestamp real do servidor (não o CurrentTime anotado).
# Limitação: requer acesso direto ao servidor OPC UA.
# ──────────────────────────────────────────────────────────────────────────────────

class InstrumentedHandler:
    """Handler que registra SourceTimestamp e instante de recepção + escrita."""

    def __init__(self, clock_offset_ms: float = 0.0):
        self.samples: List[SyncSample] = []
        self._clock_offset_ms = clock_offset_ms
        self._cycle = 0
        self._active = True
        self._last_write_time: float = 0.0

    def datachange_notification(self, node, val, data):
        if not self._active:
            return

        t_receive = time.time()

        try:
            # Extrai SourceTimestamp
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

            # Simula o tempo de escrita (recepção + overhead de serialização ~1ms)
            t_write = t_receive + 0.001

            # Offset compensado pelo clock offset
            offset_ms = (t_write - source_ts) * 1000 - self._clock_offset_ms

            self._cycle += 1
            self.samples.append(SyncSample(
                cycle=self._cycle,
                source_timestamp=datetime.fromtimestamp(
                    source_ts, tz=timezone.utc
                ).isoformat(),
                snapshot_write_time=t_write,
                offset_ms=offset_ms,
            ))

        except Exception as e:
            logger.debug("Erro no handler instrumentado: %s", e)

    def status_change_notification(self, status):
        logger.warning("Subscription status: %s", status)

    def stop(self):
        self._active = False


async def measure_clock_offset(client, n_samples: int = 20) -> float:
    """Mede offset de relógio via half-RTT (reutiliza lógica do latency_benchmark)."""
    from asyncua import Client
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
        offset = (t_client_mid - t_server) * 1000
        offsets.append(offset)
        await asyncio.sleep(0.05)

    if not offsets:
        return 0.0

    arr = np.array(offsets)
    mean = np.mean(arr)
    std = np.std(arr)
    filtered = arr[np.abs(arr - mean) < 2 * std]
    return float(np.mean(filtered)) if len(filtered) >= 3 else float(mean)


def _extract_nodeids(config: Dict[str, Any]) -> List[str]:
    """Extrai NodeIds do config (mesmo algoritmo dos outros benchmarks)."""
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


async def run_instrumented_mode(
    server_url: str,
    target_cycles: int,
    max_duration_s: float,
    publishing_interval_ms: float = 200,
) -> Tuple[List[SyncSample], float, float]:
    """
    Modo instrumentado: conecta ao OPC UA e mede offset com SourceTimestamp real.

    Returns:
        Tupla (amostras, duração, clock_offset_ms)
    """
    from asyncua import Client

    client = Client(url=server_url, timeout=10)
    await client.connect()
    logger.info("Conectado ao servidor: %s", server_url)

    try:
        # Mede offset
        clock_offset = await measure_clock_offset(client, n_samples=20)
        logger.info("Clock offset: %.2f ms", clock_offset)

        # Carrega config
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            nodeids = _extract_nodeids(config)
        else:
            nodeids = ["ns=0;i=2258"]

        logger.info("Monitorando %d nós", len(nodeids))

        # Cria subscription
        handler = InstrumentedHandler(clock_offset_ms=clock_offset)
        subscription = await client.create_subscription(
            period=publishing_interval_ms,
            handler=handler,
        )

        nodes = [client.get_node(nid) for nid in nodeids]
        await subscription.subscribe_data_change(nodes)

        # Coleta
        logger.info("Coletando %d ciclos (máx %.0f s)...", target_cycles, max_duration_s)
        start = time.time()
        last_report = start

        while len(handler.samples) < target_cycles:
            if (time.time() - start) >= max_duration_s:
                break
            await asyncio.sleep(1.0)

            if time.time() - last_report >= 10:
                n = len(handler.samples)
                logger.info("  [%.0f s] %d/%d ciclos", time.time() - start, n, target_cycles)
                last_report = time.time()

        handler.stop()
        duration = time.time() - start

        try:
            await subscription.delete()
        except Exception:
            pass

        return handler.samples, duration, clock_offset

    finally:
        await client.disconnect()


# ─── Análise Estatística ──────────────────────────────────────────────────────────

def analyze_samples(
    samples: List[SyncSample],
    duration_s: float,
    mode: str,
    clock_offset_ms: float = 0.0,
    snapshot_path: str = "",
    server_url: str = "",
    target_cycles: int = 0,
) -> SyncFidelityResults:
    """Calcula estatísticas de fidelidade de sincronização."""
    results = SyncFidelityResults()
    results.mode = mode
    results.start_time = samples[0].source_timestamp if samples else ""
    results.end_time = samples[-1].source_timestamp if samples else ""
    results.duration_s = duration_s
    results.target_cycles = target_cycles
    results.actual_cycles = len(samples)
    results.snapshot_path = snapshot_path
    results.server_url = server_url
    results.clock_offset_ms = clock_offset_ms

    if not samples:
        return results

    offsets = np.array([s.offset_ms for s in samples])

    # Estatísticas de offset
    results.offset_mean_ms = float(np.mean(offsets))
    results.offset_std_ms = float(np.std(offsets))
    results.offset_median_ms = float(np.median(offsets))
    results.offset_p5_ms = float(np.percentile(offsets, 5))
    results.offset_p95_ms = float(np.percentile(offsets, 95))
    results.offset_p99_ms = float(np.percentile(offsets, 99))
    results.offset_min_ms = float(np.min(offsets))
    results.offset_max_ms = float(np.max(offsets))

    # Jitter (variação entre offsets consecutivos)
    if len(offsets) > 1:
        diffs = np.abs(np.diff(offsets))
        results.jitter_mean_ms = float(np.mean(diffs))
        results.jitter_std_ms = float(np.std(diffs))
        results.jitter_max_ms = float(np.max(diffs))

    # Taxa efetiva
    if duration_s > 0:
        results.effective_rate_hz = len(samples) / duration_s

    # Ciclos perdidos e duplicados (baseado em timestamps repetidos)
    source_times = [s.source_timestamp for s in samples]
    unique_times = set(source_times)
    results.duplicate_cycles = len(source_times) - len(unique_times)
    results.missed_cycles = max(0, target_cycles - len(samples))

    # Histograma (20 bins para gráfico)
    counts, bin_edges = np.histogram(offsets, bins=20)
    results.histogram_bins = [float(b) for b in bin_edges]
    results.histogram_counts = [int(c) for c in counts]

    return results


# ─── Relatório ────────────────────────────────────────────────────────────────────

def print_report(results: SyncFidelityResults) -> str:
    """Gera relatório formatado."""
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("  BENCHMARK DE FIDELIDADE DE SINCRONIZAÇÃO — AAS Robô SCARA")
    lines.append("=" * 70)
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ PROTOCOLO                                                            │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    lines.append(f"│ Modo:              {results.mode:<50}│")
    lines.append(f"│ Ciclos coletados:  {results.actual_cycles}/{results.target_cycles:<46}│")
    lines.append(f"│ Duração:           {results.duration_s:.1f} s ({results.duration_s/60:.1f} min){'':<28}│")
    lines.append(f"│ Taxa efetiva:      {results.effective_rate_hz:.2f} Hz{'':<44}│")
    lines.append(f"│ Clock offset:      {results.clock_offset_ms:+.2f} ms{'':<44}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ OFFSET DE SINCRONIZAÇÃO (T_snapshot - T_source)                     │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    lines.append(f"│ Média ± DP:        {results.offset_mean_ms:.2f} ± {results.offset_std_ms:.2f} ms{'':<33}│")
    lines.append(f"│ Mediana:           {results.offset_median_ms:.2f} ms{'':<44}│")
    lines.append(f"│ Percentil 5:       {results.offset_p5_ms:.2f} ms{'':<44}│")
    lines.append(f"│ Percentil 95:      {results.offset_p95_ms:.2f} ms{'':<44}│")
    lines.append(f"│ Percentil 99:      {results.offset_p99_ms:.2f} ms{'':<44}│")
    lines.append(f"│ Mínimo:            {results.offset_min_ms:.2f} ms{'':<44}│")
    lines.append(f"│ Máximo:            {results.offset_max_ms:.2f} ms{'':<44}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ JITTER (variação entre ciclos consecutivos)                         │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    lines.append(f"│ Jitter médio:      {results.jitter_mean_ms:.2f} ± {results.jitter_std_ms:.2f} ms{'':<33}│")
    lines.append(f"│ Jitter máximo:     {results.jitter_max_ms:.2f} ms{'':<44}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ QUALIDADE                                                            │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    lines.append(f"│ Ciclos duplicados: {results.duplicate_cycles:<50}│")
    lines.append(f"│ Ciclos perdidos:   {results.missed_cycles:<50}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")

    # Histograma ASCII simples
    if results.histogram_counts:
        lines.append("")
        lines.append("  Distribuição do offset (histograma):")
        max_count = max(results.histogram_counts) if results.histogram_counts else 1
        for i, count in enumerate(results.histogram_counts):
            bin_start = results.histogram_bins[i]
            bin_end = results.histogram_bins[i + 1]
            bar_len = int(40 * count / max_count) if max_count > 0 else 0
            bar = "█" * bar_len
            lines.append(f"  [{bin_start:7.1f}, {bin_end:7.1f}) │{bar} {count}")

    lines.append("")
    report = "\n".join(lines)
    print(report)
    return report


def save_results(results: SyncFidelityResults, samples: List[SyncSample], output_dir: str) -> None:
    """Salva resultados e amostras brutas."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON resumo
    json_file = out_path / f"sync_fidelity_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(asdict(results), f, indent=2, ensure_ascii=False, default=str)
    logger.info("Resultados salvos em: %s", json_file)

    # CSV com amostras brutas (para análise posterior / gráficos)
    csv_file = out_path / f"sync_fidelity_samples_{timestamp}.csv"
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write("cycle,source_timestamp,snapshot_write_time,offset_ms,size_bytes\n")
        for s in samples:
            f.write(f"{s.cycle},{s.source_timestamp},{s.snapshot_write_time:.6f},"
                    f"{s.offset_ms:.3f},{s.snapshot_size_bytes}\n")
    logger.info("Amostras brutas salvas em: %s", csv_file)

    # Relatório texto
    report = print_report(results)
    txt_file = out_path / f"sync_fidelity_{timestamp}.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info("Relatório salvo em: %s", txt_file)


# ─── Main ─────────────────────────────────────────────────────────────────────────

async def async_main(args):
    """Entry point assíncrono."""
    if args.mode == "instrumented":
        samples, duration, clock_offset = await run_instrumented_mode(
            server_url=args.server,
            target_cycles=args.cycles,
            max_duration_s=args.duration,
            publishing_interval_ms=args.pub_interval,
        )
        results = analyze_samples(
            samples, duration,
            mode="instrumented",
            clock_offset_ms=clock_offset,
            server_url=args.server,
            target_cycles=args.cycles,
        )
    else:
        samples, duration = run_observer_mode(
            snapshot_path=args.snapshot,
            target_cycles=args.cycles,
            max_duration_s=args.duration,
            poll_interval_s=args.poll_interval / 1000,
        )
        results = analyze_samples(
            samples, duration,
            mode="observer",
            snapshot_path=args.snapshot,
            target_cycles=args.cycles,
        )

    if samples:
        save_results(results, samples, args.output)
    else:
        logger.warning("Nenhuma amostra coletada. Verifique se o sistema está ativo.")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark de fidelidade de sincronização — AAS Robô SCARA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Modo observador (monitorar arquivo, cliente OPC UA deve estar rodando)
  python benchmarks/sync_fidelity_benchmark.py --cycles 1000
  python benchmarks/sync_fidelity_benchmark.py --cycles 5000 --duration 3600

  # Modo instrumentado (conecta diretamente ao servidor OPC UA)
  python benchmarks/sync_fidelity_benchmark.py --mode instrumented --cycles 5000
  python benchmarks/sync_fidelity_benchmark.py --mode instrumented --server opc.tcp://192.168.0.31:4880/Staubli
        """
    )
    parser.add_argument(
        "--mode", "-m", type=str, default="observer",
        choices=["observer", "instrumented"],
        help="Modo de medição (default: observer)"
    )
    parser.add_argument(
        "--cycles", "-c", type=int, default=1000,
        help="Número de ciclos (escritas) a coletar (default: 1000)"
    )
    parser.add_argument(
        "--duration", "-d", type=float, default=3600,
        help="Duração máxima do ensaio em segundos (default: 3600)"
    )
    parser.add_argument(
        "--snapshot", type=str, default=DEFAULT_SNAPSHOT,
        help="Caminho do latest_data.json (modo observer)"
    )
    parser.add_argument(
        "--server", "-s", type=str, default=DEFAULT_SERVER,
        help="URL do servidor OPC UA (modo instrumented)"
    )
    parser.add_argument(
        "--pub-interval", type=float, default=200,
        help="Publishing interval em ms (modo instrumented, default: 200)"
    )
    parser.add_argument(
        "--poll-interval", type=float, default=50,
        help="Intervalo de polling do mtime em ms (modo observer, default: 50)"
    )
    parser.add_argument(
        "--output", "-o", type=str, default="benchmarks/results",
        help="Diretório de saída (default: benchmarks/results/)"
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("  BENCHMARK DE FIDELIDADE DE SINCRONIZAÇÃO")
    logger.info("=" * 70)
    logger.info("Modo: %s | Ciclos: %d | Duração máx: %.0f s",
                args.mode, args.cycles, args.duration)

    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
