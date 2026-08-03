# ==================================================================================================
#   Benchmark de Injeção de Falhas — AAS Robô SCARA
#
#   Ensaios:
#   1. Desconexão/reconexão OPC UA (simulada via firewall ou kill de conexão)
#   2. Perda de pacotes na rede da célula (simulada via tc/netem ou clumsy no Windows)
#   3. Restart do gateway sob carga (simulada via kill/restart do processo cliente)
#
#   Métricas reportadas:
#   - Tempo de detecção da falha (T_detect - T_inject)
#   - Amostras perdidas durante a falha
#   - Tempo de recuperação (T_recover - T_inject)
#   - Comportamento de fallback (último valor válido mantido? erro propagado?)
#
#   Uso:
#       python benchmarks/fault_injection_benchmark.py --test disconnect --duration 60
#       python benchmarks/fault_injection_benchmark.py --test packet-loss --loss-pct 20
#       python benchmarks/fault_injection_benchmark.py --test gateway-restart
#       python benchmarks/fault_injection_benchmark.py --test all
#
#   ATENÇÃO: Alguns testes requerem privilégios de administrador para manipular
#   regras de firewall ou simular perda de pacotes.
#
#   Requisitos:
#       pip install numpy asyncua
# ==================================================================================================

import argparse
import asyncio
import json
import logging
import os
import subprocess
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
logger = logging.getLogger("fault_injection")

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = str(ROOT_DIR / "acquisition" / "client" / "latest_data.json")
DEFAULT_SERVER = os.getenv("OPCUA_SERVER_URL", "opc.tcp://192.168.0.31:4880/Staubli")
CONFIG_FILE = ROOT_DIR / "acquisition" / "client" / "config_opcua.json"


# ─── Data Classes ────────────────────────────────────────────────────────────────

@dataclass
class FaultEvent:
    """Registro de um evento de falha injetada."""
    test_name: str
    fault_injected_at: float = 0.0       # epoch
    fault_detected_at: float = 0.0       # epoch
    recovery_at: float = 0.0             # epoch
    detection_time_ms: float = 0.0       # T_detect - T_inject
    recovery_time_ms: float = 0.0        # T_recover - T_inject
    samples_lost: int = 0
    samples_before: int = 0
    samples_after: int = 0
    expected_samples_during: int = 0
    last_valid_value: Optional[Any] = None
    first_recovered_value: Optional[Any] = None
    fallback_behavior: str = ""          # "stale_value", "error", "null", "reconnected"
    notes: str = ""


@dataclass
class FaultInjectionResults:
    """Resultados consolidados de um ensaio de injeção de falhas."""
    metadata: Dict[str, Any] = field(default_factory=dict)
    test_name: str = ""
    test_description: str = ""
    n_iterations: int = 0
    fault_duration_s: float = 0.0
    events: List[FaultEvent] = field(default_factory=list)

    # Estatísticas agregadas
    detection_time_mean_ms: float = 0.0
    detection_time_std_ms: float = 0.0
    detection_time_p95_ms: float = 0.0
    detection_time_max_ms: float = 0.0

    recovery_time_mean_ms: float = 0.0
    recovery_time_std_ms: float = 0.0
    recovery_time_p95_ms: float = 0.0
    recovery_time_max_ms: float = 0.0

    total_samples_lost: int = 0
    samples_lost_per_event_mean: float = 0.0
    fallback_behaviors: Dict[str, int] = field(default_factory=dict)


# ─── Utilitários de Monitoramento do Snapshot ─────────────────────────────────────

class SnapshotMonitor:
    """
    Monitora o arquivo latest_data.json para detectar paradas e retomadas.
    Usado como observador externo durante a injeção de falhas.
    """

    def __init__(self, snapshot_path: str, expected_interval_s: float = 0.5):
        self.path = Path(snapshot_path)
        self.expected_interval_s = expected_interval_s
        self.updates: List[Tuple[float, Optional[str]]] = []  # (mtime, current_time)
        self._running = False

    def get_last_mtime(self) -> float:
        """Retorna o mtime atual do arquivo."""
        try:
            return self.path.stat().st_mtime
        except OSError:
            return 0.0

    def read_current_time(self) -> Optional[str]:
        """Lê RuntimeDiagnostics.CurrentTime do snapshot."""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("RuntimeDiagnostics", {}).get("CurrentTime")
        except (json.JSONDecodeError, IOError, OSError):
            return None

    def start_monitoring(self):
        """Inicia a coleta de timestamps de atualização."""
        self._running = True
        self.updates = []

    def record_update(self):
        """Registra uma atualização detectada."""
        mtime = self.get_last_mtime()
        ct = self.read_current_time()
        self.updates.append((mtime, ct))

    def stop_monitoring(self):
        self._running = False

    def detect_gap(self, threshold_factor: float = 3.0) -> Optional[Tuple[float, float]]:
        """
        Detecta lacuna na sequência de atualizações.
        Retorna (gap_start, gap_end) ou None se não houver lacuna.
        threshold_factor: múltiplo do intervalo esperado para considerar gap.
        """
        if len(self.updates) < 2:
            return None

        threshold = self.expected_interval_s * threshold_factor
        for i in range(1, len(self.updates)):
            dt = self.updates[i][0] - self.updates[i - 1][0]
            if dt > threshold:
                return (self.updates[i - 1][0], self.updates[i][0])
        return None

    def count_expected_samples(self, duration_s: float) -> int:
        """Estima quantas amostras deveriam ter sido coletadas em um período."""
        return int(duration_s / self.expected_interval_s)


# ─── TESTE 1: Desconexão/Reconexão OPC UA ────────────────────────────────────────
#
# Simula desconexão bloqueando a porta do servidor OPC UA via regra de firewall.
# Após N segundos, remove a regra e mede o tempo de reconexão.
#
# No Windows: usa netsh advfirewall para bloquear porta 4880 (outbound).
# Requer execução como Administrador.
# ──────────────────────────────────────────────────────────────────────────────────

FIREWALL_RULE_NAME = "AAS_BENCHMARK_BLOCK_OPCUA"


def _get_server_host_port(server_url: str) -> Tuple[str, int]:
    """Extrai host e porta da URL OPC UA."""
    # opc.tcp://192.168.0.31:4880/Staubli → host=192.168.0.31, port=4880
    url_part = server_url.replace("opc.tcp://", "")
    host_port = url_part.split("/")[0]
    if ":" in host_port:
        host, port_str = host_port.rsplit(":", 1)
        return host, int(port_str)
    return host_port, 4880


def block_opcua_port(host: str, port: int) -> bool:
    """Cria regra de firewall para bloquear conexão ao servidor OPC UA."""
    cmd = (
        f'netsh advfirewall firewall add rule name="{FIREWALL_RULE_NAME}" '
        f'dir=out action=block protocol=tcp remoteip={host} remoteport={port}'
    )
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            logger.info("Firewall: porta %d bloqueada para %s", port, host)
            return True
        else:
            logger.error("Falha ao bloquear porta: %s", result.stderr)
            return False
    except Exception as e:
        logger.error("Erro ao executar netsh: %s", e)
        return False


def unblock_opcua_port() -> bool:
    """Remove regra de firewall para restaurar conexão."""
    cmd = f'netsh advfirewall firewall delete rule name="{FIREWALL_RULE_NAME}"'
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            logger.info("Firewall: regra de bloqueio removida")
            return True
        else:
            logger.warning("Falha ao remover regra: %s", result.stderr)
            return False
    except Exception as e:
        logger.error("Erro ao remover regra: %s", e)
        return False


def run_disconnect_test(
    server_url: str,
    snapshot_path: str,
    fault_duration_s: float = 10.0,
    n_iterations: int = 5,
    stabilize_s: float = 10.0,
    write_interval_s: float = 0.5,
) -> FaultInjectionResults:
    """
    Ensaio de desconexão/reconexão OPC UA.

    Protocolo:
    1. Espera estabilização (confirma snapshot atualizando normalmente)
    2. Injeta falha: bloqueia porta OPC UA via firewall
    3. Monitora: detecta quando snapshot para de atualizar
    4. Após fault_duration_s, remove o bloqueio
    5. Mede: tempo até o snapshot voltar a atualizar (reconexão)
    6. Repete n_iterations vezes
    """
    results = FaultInjectionResults()
    results.test_name = "disconnect_reconnect"
    results.test_description = (
        f"Desconexão OPC UA via firewall ({fault_duration_s}s) "
        f"× {n_iterations} iterações"
    )
    results.fault_duration_s = fault_duration_s
    results.n_iterations = n_iterations
    results.metadata = {
        "server_url": server_url,
        "snapshot_path": snapshot_path,
        "fault_duration_s": fault_duration_s,
        "stabilize_s": stabilize_s,
    }

    host, port = _get_server_host_port(server_url)
    monitor = SnapshotMonitor(snapshot_path, expected_interval_s=write_interval_s)

    for iteration in range(1, n_iterations + 1):
        logger.info("")
        logger.info("─── Iteração %d/%d ───", iteration, n_iterations)
        event = FaultEvent(test_name="disconnect_reconnect")

        # 1. Estabilização: confirma que o sistema está ativo
        logger.info("  Aguardando estabilização (%d s)...", stabilize_s)
        last_mtime = monitor.get_last_mtime()
        time.sleep(stabilize_s)
        new_mtime = monitor.get_last_mtime()

        if new_mtime <= last_mtime:
            logger.warning("  Snapshot não está atualizando. Sistema inativo?")
            event.notes = "Sistema inativo antes da injeção"
            results.events.append(event)
            continue

        event.last_valid_value = monitor.read_current_time()
        samples_before_mtime = new_mtime

        # 2. Injetar falha
        logger.info("  Injetando falha: bloqueando porta %d...", port)
        t_inject = time.time()
        event.fault_injected_at = t_inject

        if not block_opcua_port(host, port):
            event.notes = "Falha ao bloquear porta (requer admin?)"
            results.events.append(event)
            continue

        # 3. Monitorar: detectar quando snapshot para
        logger.info("  Monitorando detecção da falha...")
        detect_timeout = fault_duration_s + 30
        poll_start = time.time()
        detected = False
        last_check_mtime = monitor.get_last_mtime()

        while (time.time() - poll_start) < detect_timeout:
            time.sleep(0.1)
            current_mtime = monitor.get_last_mtime()

            # Se mtime parou de mudar por > 3× o intervalo esperado, detectamos
            if (time.time() - max(current_mtime, last_check_mtime)) > (write_interval_s * 3):
                if not detected:
                    event.fault_detected_at = time.time()
                    event.detection_time_ms = (event.fault_detected_at - t_inject) * 1000
                    detected = True
                    logger.info("  Falha detectada em %.0f ms", event.detection_time_ms)

            if current_mtime > last_check_mtime:
                last_check_mtime = current_mtime

            # Após fault_duration_s, remover bloqueio
            if (time.time() - t_inject) >= fault_duration_s:
                break

        # 4. Remover falha
        logger.info("  Removendo falha (desbloqueando porta)...")
        unblock_opcua_port()
        t_unblock = time.time()

        # 5. Medir recuperação: esperar snapshot voltar a atualizar
        logger.info("  Aguardando recuperação...")
        recovery_timeout = 60.0  # máximo 60s para reconectar
        recovery_start = time.time()
        recovered = False
        last_recovery_mtime = monitor.get_last_mtime()

        while (time.time() - recovery_start) < recovery_timeout:
            time.sleep(0.2)
            current_mtime = monitor.get_last_mtime()
            if current_mtime > last_recovery_mtime:
                event.recovery_at = time.time()
                event.recovery_time_ms = (event.recovery_at - t_inject) * 1000
                event.first_recovered_value = monitor.read_current_time()
                recovered = True
                logger.info("  Recuperação em %.0f ms (desde injeção)", event.recovery_time_ms)
                break

        if not recovered:
            event.recovery_time_ms = recovery_timeout * 1000
            event.notes += " Timeout de recuperação atingido."
            logger.warning("  Timeout de recuperação!")

        # 6. Calcular amostras perdidas
        event.expected_samples_during = monitor.count_expected_samples(fault_duration_s)
        # Amostras reais durante a falha = 0 (snapshot não atualizou)
        event.samples_lost = event.expected_samples_during

        # Determinar comportamento de fallback
        current_value = monitor.read_current_time()
        if current_value == event.last_valid_value:
            event.fallback_behavior = "stale_value"
        elif current_value is None:
            event.fallback_behavior = "null"
        elif recovered:
            event.fallback_behavior = "reconnected"
        else:
            event.fallback_behavior = "error"

        results.events.append(event)
        logger.info("  Fallback: %s | Perdidas: %d amostras",
                    event.fallback_behavior, event.samples_lost)

        # Pausa entre iterações
        if iteration < n_iterations:
            logger.info("  Pausa entre iterações (5s)...")
            time.sleep(5)

    # Cleanup: garantir que a regra foi removida
    unblock_opcua_port()
    return results


# ─── TESTE 2: Perda de Pacotes na Rede ───────────────────────────────────────────
#
# Simula perda de pacotes usando clumsy (Windows) ou iptables (Linux).
# No Windows: usa clumsy.exe (deve estar no PATH ou em benchmarks/tools/).
# Alternativa: usa PowerShell + NetQos policy para limitar.
#
# Também pode funcionar em modo "observador puro" — injeta perda via
# desconexão intermitente (on/off rápido do firewall).
# ──────────────────────────────────────────────────────────────────────────────────

def run_packet_loss_test(
    server_url: str,
    snapshot_path: str,
    loss_pct: int = 20,
    fault_duration_s: float = 30.0,
    n_iterations: int = 3,
    write_interval_s: float = 0.5,
) -> FaultInjectionResults:
    """
    Ensaio de perda de pacotes na rede.

    Protocolo:
    1. Estabilização (confirma operação normal)
    2. Simula perda de pacotes via bloqueio/desbloqueio intermitente
       (ciclos de block/unblock no firewall em intervalos aleatórios)
    3. Monitora degradação do snapshot
    4. Remove falha e mede recuperação

    Nota: simulação simplificada via ciclos de firewall on/off.
    Para perda real de pacotes, usar clumsy.exe ou tc/netem.
    """
    results = FaultInjectionResults()
    results.test_name = "packet_loss"
    results.test_description = (
        f"Perda de pacotes simulada (~{loss_pct}%) por {fault_duration_s}s "
        f"× {n_iterations} iterações"
    )
    results.fault_duration_s = fault_duration_s
    results.n_iterations = n_iterations
    results.metadata = {
        "server_url": server_url,
        "loss_pct": loss_pct,
        "method": "intermittent_firewall",
    }

    host, port = _get_server_host_port(server_url)
    monitor = SnapshotMonitor(snapshot_path, expected_interval_s=write_interval_s)

    for iteration in range(1, n_iterations + 1):
        logger.info("")
        logger.info("─── Iteração %d/%d (perda ~%d%%) ───", iteration, n_iterations, loss_pct)
        event = FaultEvent(test_name="packet_loss")

        # 1. Estabilização
        time.sleep(5)
        event.last_valid_value = monitor.read_current_time()

        # 2. Conta amostras antes
        mtime_before = monitor.get_last_mtime()
        t_inject = time.time()
        event.fault_injected_at = t_inject

        # 3. Injeção: ciclos de block/unblock simulando perda
        logger.info("  Injetando perda de pacotes intermitente...")
        block_time = 0.1 * (loss_pct / 100)  # % do tempo bloqueado
        unblock_time = 0.1 * (1 - loss_pct / 100)
        updates_during = 0
        fault_end = t_inject + fault_duration_s

        while time.time() < fault_end:
            # Bloqueia
            block_opcua_port(host, port)
            time.sleep(block_time + np.random.uniform(0, 0.05))
            # Desbloqueia
            unblock_opcua_port()
            time.sleep(unblock_time + np.random.uniform(0, 0.05))
            # Checa se houve atualização
            new_mtime = monitor.get_last_mtime()
            if new_mtime > mtime_before:
                updates_during += 1
                mtime_before = new_mtime

        # 4. Garantir desbloqueio
        unblock_opcua_port()

        # 5. Detectar recuperação total
        logger.info("  Aguardando recuperação completa...")
        recovery_start = time.time()
        last_mtime = monitor.get_last_mtime()
        recovered = False

        for _ in range(100):  # até 10s
            time.sleep(0.1)
            new_mtime = monitor.get_last_mtime()
            if new_mtime > last_mtime:
                event.recovery_at = time.time()
                event.recovery_time_ms = (event.recovery_at - t_inject) * 1000
                event.first_recovered_value = monitor.read_current_time()
                recovered = True
                break

        if not recovered:
            event.recovery_time_ms = (time.time() - t_inject) * 1000
            event.notes = "Recuperação lenta ou timeout"

        # 6. Calcular amostras perdidas
        expected = monitor.count_expected_samples(fault_duration_s)
        event.expected_samples_during = expected
        event.samples_lost = max(0, expected - updates_during)
        event.samples_before = updates_during
        event.detection_time_ms = block_time * 1000  # aproximação

        # Fallback
        if recovered:
            event.fallback_behavior = "partial_loss_then_recovered"
        else:
            event.fallback_behavior = "degraded"

        results.events.append(event)
        logger.info("  Amostras esperadas: %d | Recebidas: %d | Perdidas: %d",
                    expected, updates_during, event.samples_lost)

        if iteration < n_iterations:
            time.sleep(5)

    unblock_opcua_port()
    return results


# ─── TESTE 3: Restart do Gateway sob Carga ───────────────────────────────────────
#
# Simula restart do processo cliente OPC UA (acquisition/client/client_asyncua.py).
# Mata o processo, espera, reinicia, e mede o tempo de recuperação.
# ──────────────────────────────────────────────────────────────────────────────────

def _find_client_process() -> Optional[int]:
    """Encontra o PID do processo client_asyncua.py."""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-Process python -ErrorAction SilentlyContinue | '
             'Where-Object {$_.CommandLine -like "*client_asyncua*"} | '
             'Select-Object -ExpandProperty Id'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            return int(pids[0].strip())
    except Exception as e:
        logger.debug("Erro ao buscar processo: %s", e)
    return None


def _kill_process(pid: int) -> bool:
    """Mata um processo por PID."""
    try:
        result = subprocess.run(
            ['taskkill', '/F', '/PID', str(pid)],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def _start_client_process() -> Optional[int]:
    """Reinicia o processo do cliente OPC UA."""
    client_script = ROOT_DIR / "acquisition" / "client" / "client_asyncua.py"
    if not client_script.exists():
        logger.error("Script do cliente não encontrado: %s", client_script)
        return None

    try:
        # Inicia em background
        proc = subprocess.Popen(
            [sys.executable, str(client_script)],
            cwd=str(ROOT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("  Cliente reiniciado com PID %d", proc.pid)
        return proc.pid
    except Exception as e:
        logger.error("Erro ao reiniciar cliente: %s", e)
        return None


def run_gateway_restart_test(
    snapshot_path: str,
    fault_duration_s: float = 10.0,
    n_iterations: int = 3,
    write_interval_s: float = 0.5,
) -> FaultInjectionResults:
    """
    Ensaio de restart do gateway (processo cliente OPC UA).

    Protocolo:
    1. Encontra o processo client_asyncua.py
    2. Mata o processo (simula crash do gateway)
    3. Monitora: snapshot para de atualizar
    4. Após fault_duration_s, reinicia o processo
    5. Mede: tempo até o snapshot voltar a atualizar
    """
    results = FaultInjectionResults()
    results.test_name = "gateway_restart"
    results.test_description = (
        f"Kill/restart do cliente OPC UA ({fault_duration_s}s downtime) "
        f"× {n_iterations} iterações"
    )
    results.fault_duration_s = fault_duration_s
    results.n_iterations = n_iterations
    results.metadata = {
        "snapshot_path": snapshot_path,
        "fault_duration_s": fault_duration_s,
    }

    monitor = SnapshotMonitor(snapshot_path, expected_interval_s=write_interval_s)

    for iteration in range(1, n_iterations + 1):
        logger.info("")
        logger.info("─── Iteração %d/%d (gateway restart) ───", iteration, n_iterations)
        event = FaultEvent(test_name="gateway_restart")

        # 1. Encontrar processo
        pid = _find_client_process()
        if pid is None:
            logger.warning("  Processo client_asyncua.py não encontrado!")
            event.notes = "Processo não encontrado — executar manualmente"
            results.events.append(event)
            continue

        logger.info("  Processo encontrado: PID %d", pid)
        event.last_valid_value = monitor.read_current_time()

        # 2. Matar processo
        t_inject = time.time()
        event.fault_injected_at = t_inject

        if not _kill_process(pid):
            event.notes = "Falha ao matar processo"
            results.events.append(event)
            continue

        logger.info("  Processo morto. Aguardando %d s...", fault_duration_s)

        # 3. Monitorar detecção
        last_mtime = monitor.get_last_mtime()
        detect_start = time.time()
        detected = False

        while (time.time() - detect_start) < (fault_duration_s + 5):
            time.sleep(0.2)
            # Detecção: mtime não muda por > 3× intervalo esperado
            if (time.time() - last_mtime) > (write_interval_s * 3) and not detected:
                event.fault_detected_at = time.time()
                event.detection_time_ms = (event.fault_detected_at - t_inject) * 1000
                detected = True
                logger.info("  Falha detectada em %.0f ms", event.detection_time_ms)

            new_mtime = monitor.get_last_mtime()
            if new_mtime > last_mtime:
                last_mtime = new_mtime

            if (time.time() - t_inject) >= fault_duration_s:
                break

        # 4. Reiniciar processo
        logger.info("  Reiniciando cliente...")
        new_pid = _start_client_process()

        # 5. Medir recuperação
        logger.info("  Aguardando recuperação...")
        recovery_timeout = 30.0
        recovery_start = time.time()
        recovered = False
        last_mtime_recovery = monitor.get_last_mtime()

        while (time.time() - recovery_start) < recovery_timeout:
            time.sleep(0.5)
            new_mtime = monitor.get_last_mtime()
            if new_mtime > last_mtime_recovery:
                event.recovery_at = time.time()
                event.recovery_time_ms = (event.recovery_at - t_inject) * 1000
                event.first_recovered_value = monitor.read_current_time()
                recovered = True
                logger.info("  Recuperação em %.0f ms", event.recovery_time_ms)
                break

        if not recovered:
            event.recovery_time_ms = (time.time() - t_inject) * 1000
            event.notes += " Timeout de recuperação"
            logger.warning("  Timeout de recuperação")

        # 6. Métricas
        event.expected_samples_during = monitor.count_expected_samples(fault_duration_s)
        event.samples_lost = event.expected_samples_during  # todas perdidas durante kill
        event.fallback_behavior = "stale_value" if not recovered else "reconnected"

        results.events.append(event)

        if iteration < n_iterations:
            time.sleep(10)  # pausa maior para estabilizar

    return results


# ─── Análise Estatística ──────────────────────────────────────────────────────────

def compute_statistics(results: FaultInjectionResults) -> FaultInjectionResults:
    """Calcula estatísticas agregadas dos eventos."""
    events = results.events
    if not events:
        return results

    # Tempos de detecção
    detect_times = [e.detection_time_ms for e in events if e.detection_time_ms > 0]
    if detect_times:
        arr = np.array(detect_times)
        results.detection_time_mean_ms = float(np.mean(arr))
        results.detection_time_std_ms = float(np.std(arr))
        results.detection_time_p95_ms = float(np.percentile(arr, 95))
        results.detection_time_max_ms = float(np.max(arr))

    # Tempos de recuperação
    recover_times = [e.recovery_time_ms for e in events if e.recovery_time_ms > 0]
    if recover_times:
        arr = np.array(recover_times)
        results.recovery_time_mean_ms = float(np.mean(arr))
        results.recovery_time_std_ms = float(np.std(arr))
        results.recovery_time_p95_ms = float(np.percentile(arr, 95))
        results.recovery_time_max_ms = float(np.max(arr))

    # Amostras perdidas
    results.total_samples_lost = sum(e.samples_lost for e in events)
    if events:
        results.samples_lost_per_event_mean = results.total_samples_lost / len(events)

    # Comportamentos de fallback
    behaviors: Dict[str, int] = {}
    for e in events:
        b = e.fallback_behavior or "unknown"
        behaviors[b] = behaviors.get(b, 0) + 1
    results.fallback_behaviors = behaviors

    return results


# ─── Relatório ────────────────────────────────────────────────────────────────────

def print_report(results: FaultInjectionResults) -> str:
    """Gera relatório formatado."""
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("  BENCHMARK DE INJEÇÃO DE FALHAS — AAS Robô SCARA")
    lines.append("=" * 70)
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ ENSAIO                                                              │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    lines.append(f"│ Teste:             {results.test_name:<50}│")
    lines.append(f"│ Descrição:         {results.test_description[:50]:<50}│")
    lines.append(f"│ Iterações:         {results.n_iterations:<50}│")
    lines.append(f"│ Duração falha:     {results.fault_duration_s:.1f} s{'':<46}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ TEMPO DE DETECÇÃO                                                   │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    lines.append(f"│ Média ± DP:        {results.detection_time_mean_ms:.0f} ± {results.detection_time_std_ms:.0f} ms{'':<35}│")
    lines.append(f"│ P95:               {results.detection_time_p95_ms:.0f} ms{'':<46}│")
    lines.append(f"│ Pior caso:         {results.detection_time_max_ms:.0f} ms{'':<46}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ TEMPO DE RECUPERAÇÃO                                                │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    lines.append(f"│ Média ± DP:        {results.recovery_time_mean_ms:.0f} ± {results.recovery_time_std_ms:.0f} ms{'':<35}│")
    lines.append(f"│ P95:               {results.recovery_time_p95_ms:.0f} ms{'':<46}│")
    lines.append(f"│ Pior caso:         {results.recovery_time_max_ms:.0f} ms{'':<46}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ AMOSTRAS PERDIDAS                                                   │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    lines.append(f"│ Total perdidas:    {results.total_samples_lost:<50}│")
    lines.append(f"│ Média por evento:  {results.samples_lost_per_event_mean:.1f}{'':<48}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")
    lines.append("")
    lines.append("┌─────────────────────────────────────────────────────────────────────┐")
    lines.append("│ COMPORTAMENTO DE FALLBACK                                           │")
    lines.append("├─────────────────────────────────────────────────────────────────────┤")
    for behavior, count in results.fallback_behaviors.items():
        lines.append(f"│   {behavior:<24} {count} ocorrência(s){'':<25}│")
    lines.append("└─────────────────────────────────────────────────────────────────────┘")

    # Detalhe por evento
    lines.append("")
    lines.append("  Detalhes por iteração:")
    lines.append("  ─────────────────────────────────────────────────────")
    lines.append("  # │ Detecção (ms) │ Recuperação (ms) │ Perdidas │ Fallback")
    lines.append("  ──┼───────────────┼──────────────────┼──────────┼──────────────")
    for i, ev in enumerate(results.events, 1):
        lines.append(
            f"  {i:>1} │ {ev.detection_time_ms:>12.0f}  │ {ev.recovery_time_ms:>15.0f}  │"
            f" {ev.samples_lost:>8} │ {ev.fallback_behavior}"
        )
    lines.append("")

    report = "\n".join(lines)
    print(report)
    return report


def save_results(results: FaultInjectionResults, output_dir: str) -> None:
    """Salva resultados."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON
    json_file = out_path / f"fault_injection_{results.test_name}_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(asdict(results), f, indent=2, ensure_ascii=False, default=str)
    logger.info("Resultados salvos em: %s", json_file)

    # Texto
    report = print_report(results)
    txt_file = out_path / f"fault_injection_{results.test_name}_{timestamp}.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info("Relatório salvo em: %s", txt_file)


# ─── Main ─────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark de injeção de falhas — AAS Robô SCARA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ensaios disponíveis:
  disconnect     Desconexão/reconexão OPC UA via bloqueio de firewall
  packet-loss    Perda de pacotes simulada (intermittent firewall)
  gateway-restart  Kill/restart do processo cliente OPC UA
  all            Executa todos os ensaios em sequência

ATENÇÃO: Os testes 'disconnect' e 'packet-loss' requerem execução como
Administrador para manipular regras de firewall.

Exemplos:
  python benchmarks/fault_injection_benchmark.py --test disconnect
  python benchmarks/fault_injection_benchmark.py --test packet-loss --loss-pct 30
  python benchmarks/fault_injection_benchmark.py --test gateway-restart --iterations 5
  python benchmarks/fault_injection_benchmark.py --test all --fault-duration 15
        """
    )
    parser.add_argument(
        "--test", "-t", type=str, required=True,
        choices=["disconnect", "packet-loss", "gateway-restart", "all"],
        help="Tipo de ensaio a executar"
    )
    parser.add_argument(
        "--fault-duration", type=float, default=10.0,
        help="Duração da falha injetada em segundos (default: 10)"
    )
    parser.add_argument(
        "--iterations", "-n", type=int, default=5,
        help="Número de iterações por ensaio (default: 5)"
    )
    parser.add_argument(
        "--loss-pct", type=int, default=20,
        help="Percentual de perda de pacotes para teste packet-loss (default: 20)"
    )
    parser.add_argument(
        "--server", "-s", type=str, default=DEFAULT_SERVER,
        help="URL do servidor OPC UA"
    )
    parser.add_argument(
        "--snapshot", type=str, default=DEFAULT_SNAPSHOT,
        help="Caminho do latest_data.json"
    )
    parser.add_argument(
        "--output", "-o", type=str, default="benchmarks/results",
        help="Diretório de saída (default: benchmarks/results/)"
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("  BENCHMARK DE INJEÇÃO DE FALHAS")
    logger.info("=" * 70)
    logger.info("Teste: %s | Duração falha: %.0f s | Iterações: %d",
                args.test, args.fault_duration, args.iterations)

    tests_to_run = []
    if args.test == "all":
        tests_to_run = ["disconnect", "packet-loss", "gateway-restart"]
    else:
        tests_to_run = [args.test]

    for test in tests_to_run:
        logger.info("")
        logger.info("═" * 70)
        logger.info("  Executando: %s", test)
        logger.info("═" * 70)

        if test == "disconnect":
            results = run_disconnect_test(
                server_url=args.server,
                snapshot_path=args.snapshot,
                fault_duration_s=args.fault_duration,
                n_iterations=args.iterations,
            )
        elif test == "packet-loss":
            results = run_packet_loss_test(
                server_url=args.server,
                snapshot_path=args.snapshot,
                loss_pct=args.loss_pct,
                fault_duration_s=args.fault_duration,
                n_iterations=args.iterations,
            )
        elif test == "gateway-restart":
            results = run_gateway_restart_test(
                snapshot_path=args.snapshot,
                fault_duration_s=args.fault_duration,
                n_iterations=args.iterations,
            )
        else:
            continue

        results = compute_statistics(results)
        save_results(results, args.output)


if __name__ == "__main__":
    main()
