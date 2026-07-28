# ------------------------------------------------------------------------------------------------------------------
#   Script para coleta automática de informações do sistema, rede e ambiente de software.
#
#   Coleta:
#   1. Modelo/firmware do controlador (via OPC UA ou submodelo AAS)
#   2. CPU/RAM/SO do gateway (máquina local)
#   3. Topologia e velocidade da rede
#   4. Versões de software (Python, asyncua, FastAPI, Flask, SQLite, React)
#   5. Período de polling / subscription
#   6. Nº de nós monitorados
#   7. Nº de clientes simultâneos (configuração)
#
#   Uso:
#       python collect_system_info.py
#       python collect_system_info.py --output system_info.json
# ------------------------------------------------------------------------------------------------------------------

import json
import platform
import sys
import sqlite3
import subprocess
import os
import argparse
import socket
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Diretório raiz do projeto (este script fica na raiz)
ROOT_DIR = Path(__file__).resolve().parent


def collect_controller_info() -> Dict[str, Any]:
    """Coleta informações do controlador a partir do submodelo Identification."""
    identification_path = ROOT_DIR / "digital_twin" / "submodels" / "Submodel_Identification.json"
    info = {}
    
    if identification_path.exists():
        with open(identification_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        elements = data.get("submodelElements", [])
        for elem in elements:
            id_short = elem.get("idShort", "")
            value = elem.get("value", "")
            if id_short == "Model":
                info["model"] = value
            elif id_short == "Manufacturer":
                info["manufacturer"] = value
            elif id_short == "SN":
                info["serial_number"] = value
            elif id_short == "ProductName":
                info["product_name"] = value
            elif id_short == "SoftwareRevision":
                info["firmware_version"] = value
            elif id_short == "BuildNumber":
                info["build_number"] = value
            elif id_short == "BuildDate":
                info["build_date"] = value
    else:
        info["error"] = f"Arquivo não encontrado: {identification_path}"
    
    return info


def collect_gateway_info() -> Dict[str, Any]:
    """Coleta informações de CPU, RAM e SO da máquina (gateway)."""
    info = {
        "hostname": socket.gethostname(),
        "os": platform.platform(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
    }
    
    # Tenta usar psutil para informações mais detalhadas
    try:
        import psutil
        info["cpu_cores_physical"] = psutil.cpu_count(logical=False)
        info["cpu_cores_logical"] = psutil.cpu_count(logical=True)
        info["cpu_freq_mhz"] = round(psutil.cpu_freq().current, 0) if psutil.cpu_freq() else None
        mem = psutil.virtual_memory()
        info["ram_total_gb"] = round(mem.total / (1024 ** 3), 2)
        info["ram_available_gb"] = round(mem.available / (1024 ** 3), 2)
        info["ram_usage_percent"] = mem.percent
    except ImportError:
        info["nota"] = "Instale 'psutil' para detalhes de CPU/RAM: pip install psutil"
        # Fallback: tenta obter RAM via WMI no Windows
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                ram_bytes = int(result.stdout.strip())
                info["ram_total_gb"] = round(ram_bytes / (1024 ** 3), 2)
        except Exception:
            pass
        
        # Fallback: número de processadores
        info["cpu_cores_logical"] = os.cpu_count()
    
    return info


def collect_network_info() -> Dict[str, Any]:
    """Coleta informações de topologia e velocidade da rede."""
    info = {
        "topology": {},
        "interfaces": []
    }
    
    # Endpoints configurados no projeto
    config_path = ROOT_DIR / "acquisition" / "client" / "config_opcua.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Extrai endpoint do servidor OPC UA real (do código-fonte)
        info["topology"]["opcua_server_real"] = os.getenv(
            "OPCUA_SERVER_URL", "opc.tcp://192.168.0.102:4880/Staubli"
        )
    
    server_config_path = ROOT_DIR / "acquisition" / "server_local" / "config_server.json"
    if server_config_path.exists():
        with open(server_config_path, "r", encoding="utf-8") as f:
            srv_cfg = json.load(f)
        info["topology"]["opcua_server_local"] = srv_cfg.get("endpoint", "opc.tcp://0.0.0.0:4842")
    
    info["topology"]["opcua_server_republish"] = "opc.tcp://0.0.0.0:4881"
    info["topology"]["web_backend"] = "http://localhost:5000"
    info["topology"]["web_frontend"] = "http://localhost:5173"
    
    # Tenta coletar interfaces de rede via psutil
    try:
        import psutil
        net_if = psutil.net_if_stats()
        for iface_name, stats in net_if.items():
            if stats.isup:
                info["interfaces"].append({
                    "name": iface_name,
                    "speed_mbps": stats.speed,
                    "mtu": stats.mtu,
                    "is_up": stats.isup
                })
    except ImportError:
        # Fallback: usa ipconfig no Windows
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
                 "Select-Object Name, LinkSpeed, MacAddress | ConvertTo-Json"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                adapters = json.loads(result.stdout)
                if isinstance(adapters, dict):
                    adapters = [adapters]
                for adapter in adapters:
                    info["interfaces"].append({
                        "name": adapter.get("Name", ""),
                        "speed": adapter.get("LinkSpeed", ""),
                        "mac": adapter.get("MacAddress", "")
                    })
        except Exception:
            info["interfaces_nota"] = "Não foi possível detectar interfaces de rede"
    
    return info


def collect_software_versions() -> Dict[str, Any]:
    """Coleta versões de todos os componentes de software."""
    info = {}
    
    # Python
    info["python"] = sys.version
    
    # SQLite (embutido)
    info["sqlite"] = sqlite3.sqlite_version
    info["sqlite_driver"] = sqlite3.version
    
    # asyncua (OPC UA)
    try:
        import asyncua
        info["asyncua"] = asyncua.__version__
    except (ImportError, AttributeError):
        info["asyncua"] = _get_version_from_requirements("asyncua")
    
    # Flask
    try:
        import flask
        info["flask"] = flask.__version__
    except ImportError:
        info["flask"] = _get_version_from_requirements("flask")
    
    # FastAPI
    try:
        import fastapi
        info["fastapi"] = fastapi.__version__
    except ImportError:
        info["fastapi"] = _get_version_from_requirements("fastapi")
    
    # uvicorn
    try:
        import uvicorn
        info["uvicorn"] = uvicorn.__version__
    except ImportError:
        info["uvicorn"] = _get_version_from_requirements("uvicorn")
    
    # SQLAlchemy
    try:
        import sqlalchemy
        info["sqlalchemy"] = sqlalchemy.__version__
    except ImportError:
        info["sqlalchemy"] = _get_version_from_requirements("sqlalchemy")
    
    # React (do package.json)
    frontend_pkg = ROOT_DIR / "web" / "frontend" / "package.json"
    if frontend_pkg.exists():
        with open(frontend_pkg, "r", encoding="utf-8") as f:
            pkg = json.load(f)
        deps = pkg.get("dependencies", {})
        dev_deps = pkg.get("devDependencies", {})
        info["react"] = deps.get("react", "não encontrado")
        info["react-dom"] = deps.get("react-dom", "não encontrado")
        info["vite"] = dev_deps.get("vite", "não encontrado")
        info["typescript"] = dev_deps.get("typescript", "não encontrado")
    
    # Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            info["nodejs"] = result.stdout.strip()
    except Exception:
        info["nodejs"] = "não detectado"
    
    # npm
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            info["npm"] = result.stdout.strip()
    except Exception:
        info["npm"] = "não detectado"
    
    return info


def _get_version_from_requirements(package: str) -> str:
    """Busca a versão de um pacote nos requirements.txt do projeto."""
    req_files = [
        ROOT_DIR / "requirements.txt",
        ROOT_DIR / "web" / "backend" / "requirements.txt",
    ]
    for req_file in req_files:
        if req_file.exists():
            with open(req_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip().lower()
                    if line.startswith(package.lower()):
                        return line.split("==")[-1].split(">=")[-1].split("<=")[-1].strip()
    return "não encontrado nos requirements"


def collect_polling_config() -> Dict[str, Any]:
    """Coleta configurações de polling/subscription."""
    config_path = ROOT_DIR / "acquisition" / "client" / "config_opcua.json"
    info = {}
    
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        client_cfg = config.get("_client", {})
        info["mode"] = client_cfg.get("mode", "polling")
        info["enabled"] = client_cfg.get("enabled", True)
        info["publishing_interval_ms"] = client_cfg.get("publishing_interval_ms", "N/A")
        info["write_interval_s"] = client_cfg.get("write_interval_s", "N/A")
        info["polling_interval_s"] = client_cfg.get("interval_seconds", "N/A")
        
        if info["mode"] == "subscription":
            info["descricao"] = (
                f"Push-based: servidor envia dados a cada {info['publishing_interval_ms']}ms. "
                f"Escrita em disco/DB a cada {info['write_interval_s']}s."
            )
        else:
            info["descricao"] = (
                f"Polling: cliente lê dados a cada {info['polling_interval_s']}s."
            )
    else:
        info["error"] = "Arquivo config_opcua.json não encontrado"
    
    return info


def collect_monitored_nodes() -> Dict[str, Any]:
    """Conta o número de nós monitorados."""
    info = {}
    
    # Nós no arquivo all_nodes.csv (total descoberto)
    nodes_csv = ROOT_DIR / "acquisition" / "nodes" / "all_nodes.csv"
    if nodes_csv.exists():
        with open(nodes_csv, "r", encoding="utf-8") as f:
            lines = f.readlines()
        info["total_discovered"] = len(lines) - 1  # menos header
    
    # Nós efetivamente monitorados (config_opcua.json)
    config_path = ROOT_DIR / "acquisition" / "client" / "config_opcua.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Extrai todos os NodeIds únicos
        nodeids = set()
        _extract_nodeids(config, nodeids)
        info["actively_monitored"] = len(nodeids)
        info["nodeids"] = sorted(list(nodeids))
    
    return info


def _extract_nodeids(obj: Any, result: set) -> None:
    """Extrai recursivamente todos os NodeIds de uma estrutura."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "_client":
                continue
            _extract_nodeids(v, result)
    elif isinstance(obj, list):
        for item in obj:
            _extract_nodeids(item, result)
    elif isinstance(obj, str) and obj.startswith("ns=") and ";" in obj:
        result.add(obj)


def collect_clients_info() -> Dict[str, Any]:
    """Informações sobre clientes simultâneos."""
    info = {
        "opcua_clients": 1,
        "opcua_clients_nota": "Apenas 1 cliente OPC UA configurado (client_asyncua.py)",
        "web_backend": {
            "framework": "uvicorn + FastAPI + Flask (ASGI/WSGI)",
            "workers": "1 (default, event-loop assíncrono)",
            "max_connections": "sem limite explícito (padrão uvicorn)",
            "nota": "Para limitar, configure --workers e/ou middleware de rate-limiting"
        },
        "web_frontend": {
            "server": "Vite dev server (desenvolvimento) / static build (produção)",
            "nota": "Em produção, servir com nginx/caddy para controle de conexões"
        }
    }
    return info


def main():
    parser = argparse.ArgumentParser(description="Coleta informações do sistema AAS Robô SCARA")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Caminho do arquivo JSON de saída (default: imprime no terminal)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("  Coletando informações do sistema...")
    print("=" * 60)
    print()
    
    report = {
        "_metadata": {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "script": "collect_system_info.py",
            "project": "AAS Robô SCARA"
        },
        "1_controller": collect_controller_info(),
        "2_gateway": collect_gateway_info(),
        "3_network": collect_network_info(),
        "4_software_versions": collect_software_versions(),
        "5_polling_config": collect_polling_config(),
        "6_monitored_nodes": collect_monitored_nodes(),
        "7_simultaneous_clients": collect_clients_info(),
    }
    
    # Saída
    output_json = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"Relatório salvo em: {output_path}")
    else:
        print(output_json)
    
    print()
    print("=" * 60)
    print("  Coleta concluída!")
    print("=" * 60)


if __name__ == "__main__":
    main()
