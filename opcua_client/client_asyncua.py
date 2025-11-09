"""
OPC UA Client for Asset Administration Shell (AAS)
================================================

Este módulo implementa um cliente OPC UA que interage com um robô SCARA,
coletando dados e mapeando-os para a estrutura do Asset Administration Shell (AAS).

Funcionalidades Principais:
-------------------------
1. Conexão assíncrona com servidor OPC UA
2. Leitura configurável de nodes OPC UA
3. Mapeamento automático para estrutura AAS
4. Persistência multi-formato (JSON, SQLite)
5. Atualização automática de submodelos AAS

Modos de Execução:
----------------
- Modo Single-Shot (--once): Uma única execução
- Modo Contínuo: Loop com intervalo configurável

Configuração (ordem de precedência):
--------------------------------
1. Argumentos CLI (máxima prioridade)
2. Variáveis de ambiente
3. Arquivo config_opcua.json (mínima prioridade)

Fluxo de Dados:
-------------
1. Conexão OPC UA
2. Leitura de nodes configurados
3. Mapeamento para estrutura AAS
4. Persistência em múltiplos formatos

Autor: [Seu Nome]
Versão: 1.0.0
Data: Novembro 2023
"""

# Standard Library
import asyncio
import json
import datetime
import argparse
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Third Party
from asyncua import Client, ua

# Configuração de Logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("opcua_client")

# Configuração do logging - nível pode ser ajustado via variável de ambiente LOG_LEVEL
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("opcua_client")

try:
    # Importar módulo persist_db do pacote database
    from database.persist_db import save_all_submodels
except ImportError as e:
    logger.warning("Falha ao importar save_all_submodels diretamente: %s", e)
    import sys as _sys
    from pathlib import Path as _Path
    
    # Adiciona o diretório raiz do projeto ao sys.path para resolver imports relativos
    _root = str(_Path(__file__).resolve().parents[1])
    if _root not in _sys.path:
        _sys.path.append(_root)
        logger.info("Adicionado diretório raiz ao path: %s", _root)
    
    try:
        from database.persist_db import save_all_submodels  # type: ignore
        logger.info("Import via fallback bem sucedido após adicionar raiz ao path")
    except ImportError as e:
        logger.error("Falha definitiva ao importar save_all_submodels. Verifique se o diretório 'database' existe e contém persist_db.py")
        raise

# Resolver caminhos relativos ao diretório do pacote deste arquivo para evitar
# problemas ao executar a partir de diretórios de trabalho diferentes.
_ROOT_DIR = Path(__file__).resolve().parents[1]
_OPCUA_CLIENT_DIR = _ROOT_DIR / "opcua_client"

# Configurações - podem ser sobrescritas por variáveis de ambiente
CONFIG_FILE = str(_OPCUA_CLIENT_DIR / "config_opcua.json")
OUTPUT_FILE = str(_OPCUA_CLIENT_DIR / "latest_data.json")
AAS_SUBMODELS_DIR = str(_ROOT_DIR / "aas-submodels")
SERVER_URL = os.getenv("OPCUA_SERVER_URL", "opc.tcp://192.168.0.120:4880")
DB_PATH = str(_ROOT_DIR / "data/aas_history.sqlite3")

def load_config(path: str) -> Dict[str, Any]:
    """Carrega e valida arquivo de configuração JSON.
    
    Args:
        path: Caminho para o arquivo de configuração
        
    Returns:
        Dict com configuração carregada
        
    Raises:
        FileNotFoundError: Se arquivo não existe
        json.JSONDecodeError: Se JSON é inválido
        ValueError: Se configuração não tem formato esperado
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        if not isinstance(config, dict):
            raise ValueError("Configuração deve ser um objeto JSON")
            
        return config
    except FileNotFoundError:
        logger.error("Arquivo de configuração não encontrado: %s", path)
        raise
    except json.JSONDecodeError as e:
        logger.error("Erro ao parsear JSON de configuração: %s", e)
        raise

def write_json_atomic(filepath: str, data: Any, **kwargs) -> None:
    """Escreve dados em JSON de forma atômica usando arquivo temporário.
    
    Args:
        filepath: Caminho do arquivo final
        data: Dados a serem escritos como JSON
        **kwargs: Argumentos adicionais para json.dump
    """
    directory = os.path.dirname(filepath)
    with tempfile.NamedTemporaryFile(
        mode='w',
        encoding='utf-8',
        prefix='tmp_',
        suffix='.json',
        dir=directory,
        delete=False
    ) as tf:
        json.dump(data, tf, **kwargs)
        tmpname = tf.name
    
    try:
        # Em Windows, os.replace pode falhar se destino existe
        os.replace(tmpname, filepath)
    except:
        # Se falhar, tenta remover destino primeiro
        try:
            os.remove(filepath)
            os.replace(tmpname, filepath)
        except Exception as e:
            logger.exception("Erro ao escrever arquivo %s", filepath)
            try:
                os.remove(tmpname)
            except:
                pass
            raise

# ---------- utilidades de serialização ----------

def _to_builtin(x: Any) -> Any:
    """Converte objetos complexos para tipos básicos serializáveis por JSON."""
    if x is None:
        return None
    if isinstance(x, (str, int, float, bool)):
        return x
    if isinstance(x, bytes):
        return x.decode(errors="ignore")
    if isinstance(x, (list, tuple)):
        return [_to_builtin(i) for i in x]
    if isinstance(x, dict):
        return {str(k): _to_builtin(v) for k, v in x.items()}
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    if isinstance(x, datetime.date):
        return x.isoformat()
    try:
        if isinstance(x, ua.NodeId):
            return x.to_string()
        if isinstance(x, ua.uatypes.LocalizedText):
            return x.Text
        if isinstance(x, ua.uatypes.QualifiedName):
            return x.Name
        if isinstance(x, ua.uatypes.ExtensionObject):
            return _to_builtin(getattr(x, "Body", None))
        d = getattr(x, "__dict__", None)
        if isinstance(d, dict) and d:
            return {k: _to_builtin(v) for k, v in d.items()}
    except Exception as e:
        logger.debug("Erro ao serializar objeto %s: %s", type(x).__name__, e)
    return str(x)

def _is_nodeid(s: Any) -> bool:
    """Verifica se uma string tem formato de NodeId."""
    return isinstance(s, str) and s.startswith("ns=") and ";" in s

# ---------- Leitura ----------

async def _get_access_info(node) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """Obtém informações de acesso de um node: access level, user access level e node class."""
    try:
        acl = await node.read_access_level()
    except Exception as e:
        logger.debug("Erro ao ler access_level: %s", e)
        acl = None
    try:
        uacl = await node.read_user_access_level()
    except Exception as e:
        logger.debug("Erro ao ler user_access_level: %s", e)
        uacl = None
    try:
        nc = await node.read_node_class()
        nclass = ua.NodeClass(nc).name
    except Exception as e:
        logger.debug("Erro ao ler node_class: %s", e)
        nclass = None
    return acl, uacl, nclass

def _has_read(access_level: Optional[int], user_access_level: Optional[int]) -> bool:
    """Verifica se as máscaras de acesso permitem leitura."""
    mask = ua.AccessLevelType.CurrentRead
    ok_acl = True if access_level is None else bool(access_level & mask)
    ok_uacl = True if user_access_level is None else bool(user_access_level & mask)
    return ok_acl and ok_uacl

async def _read_value_safe(client: Client, nodeid: str) -> Tuple[Any, str, Dict[str, Any]]:
    """
    Tenta ler o Value do próprio nó. Se não houver, tenta filhos Variable legíveis.
    
    Args:
        client: Cliente OPC UA conectado
        nodeid: String com NodeId a ser lido
        
    Returns:
        Tupla (valor_serializavel, origem, meta)
        - valor_serializavel: valor convertido para tipo básico ou None
        - origem: "self" se próprio nó, "child:Nome" se filho, "none" se não encontrado
        - meta: dicionário com nodeClass, accessLevel, userAccessLevel
    """
    node = client.get_node(nodeid)
    acl, uacl, nclass = await _get_access_info(node)
    meta = {"nodeClass": nclass, "accessLevel": acl, "userAccessLevel": uacl}

    if nclass == "Variable" and _has_read(acl, uacl):
        try:
            val = await node.read_value()
            return _to_builtin(val), "self", meta
        except Exception as e:
            logger.debug("Erro ao ler valor do nó %s: %s", nodeid, e)
            meta["error"] = type(e).__name__

    try:
        for c in await node.get_children():
            try:
                nc = await c.read_node_class()
                if ua.NodeClass(nc).name != "Variable":
                    continue
                c_acl, c_uacl, _ = await _get_access_info(c)
                if not _has_read(c_acl, c_uacl):
                    continue
                try:
                    val = await c.read_value()
                    bn = await c.read_browse_name()
                    return _to_builtin(val), f"child:{bn.Name}", meta
                except Exception as e:
                    logger.debug("Erro ao ler filho %s: %s", await c.read_browse_name(), e)
                    continue
            except Exception as e:
                logger.debug("Erro ao verificar filho: %s", e)
                continue
    except Exception as e:
        logger.debug("Erro ao listar filhos de %s: %s", nodeid, e)
    return None, "none", meta

def _coerce(value: Any, to_type: Optional[str]) -> Any:
    """Converte valor para tipo básico especificado."""
    if to_type is None:
        return value
    try:
        if to_type == "float":
            return float(value)
        if to_type == "int":
            return int(value)
        if to_type == "str":
            return str(value)
        if to_type == "bool":
            return bool(value)
        return value
    except Exception as e:
        logger.debug("Erro ao converter %s para %s: %s", value, to_type, e)
        return value

# ---------- Solucionador de falhas ----------

async def _resolve_leaf(client: Client, spec: Any) -> Any:
    """
    Resolve um valor folha da configuração.
    
    Args:
        client: Cliente OPC UA conectado
        spec: Especificação do valor, que pode ser:
            1. literal simples (ex: 800)
            2. string NodeId "ns=...;s=..." ou "ns=...;i=..."
            3. objeto {"nodeId": "...", "manual": X, "policy": "...", "transform": "..."}
               policy: prefer-opcua (padrão), manual-only, opcua-only, prefer-manual
    
    Returns:
        Valor resolvido e convertido para tipo básico
    """
    if isinstance(spec, dict) and ("manual" in spec or "nodeId" in spec or "policy" in spec or "transform" in spec):
        nodeid = spec.get("nodeId")
        manual = spec.get("manual", None)
        policy = spec.get("policy", "prefer-opcua")
        transform = spec.get("transform")

        if policy == "manual-only":
            return _coerce(manual, transform)

        if policy == "opcua-only":
            if nodeid:
                v, _, _ = await _read_value_safe(client, nodeid)
                return _coerce(v, transform)
            return None

        if policy == "prefer-manual":
            if manual is not None:
                return _coerce(manual, transform)
            if nodeid:
                v, _, _ = await _read_value_safe(client, nodeid)
                return _coerce(v, transform)
            return None

        if nodeid:
            v, _, _ = await _read_value_safe(client, nodeid)
            if v is not None:
                return _coerce(v, transform)
        return _coerce(manual, transform)

    if _is_nodeid(spec):
        v, _, _ = await _read_value_safe(client, spec)
        return v

    return _to_builtin(spec)

# ==================================================================================================================
# Processamento da Configuração e Mapeamento OPC UA -> AAS
# ==================================================================================================================
"""
Esta seção implementa o mapeamento entre OPC UA e Asset Administration Shell:
- Percorre recursivamente a estrutura de configuração
- Resolve valores OPC UA para cada nó folha
- Mantém a estrutura hierárquica dos submodelos AAS
- Aplica transformações e validações configuradas
"""

async def _walk(client: Client, node: Any) -> Any:
    """Percorre estrutura de dados resolvendo todos os valores folha."""
    if isinstance(node, dict):
        out: Dict[str, Any] = {}
        for k, v in node.items():
            out[k] = await _walk(client, v)
        return out
    if isinstance(node, list):
        return [await _walk(client, i) for i in node]
    return await _resolve_leaf(client, node)

async def map_opcua_to_submodels(client: Client, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mapeia configuração para estrutura de submodelos, resolvendo valores OPC UA.
    
    Args:
        client: Cliente OPC UA conectado
        config: Dicionário com configuração de mapeamento
        
    Returns:
        Dicionário com valores resolvidos
    """
    return await _walk(client, config)

# ==================================================================================================================
# Cliente Principal e Ciclo de Execução
# ==================================================================================================================
"""
Esta seção contém a lógica principal do cliente OPC UA:
1. Configuração e inicialização:
   - Parsing de argumentos CLI
   - Carregamento de configurações (CLI, env, arquivo)
   - Setup de logging

2. Ciclo de execução:
   - Conexão ao servidor OPC UA
   - Leitura periódica de dados
   - Mapeamento para estrutura AAS
   - Persistência em múltiplos destinos

3. Modos de operação:
   - Ciclo único (--once)
   - Loop contínuo com intervalo configurável
"""

def _map_xs_to_coerce(t: Optional[str]) -> Optional[str]:
    """Mapeia tipos xs:... para tipos básicos internos."""
    if not t:
        return None
    t = t.lower()
    if t in ("xs:string", "string"):
        return "str"
    if t in ("xs:boolean", "boolean", "bool"):
        return "bool"
    if t in ("xs:double", "xs:float", "double", "float"):
        return "float"
    if t in ("xs:int", "xs:integer", "int", "integer"):
        return "int"
    return None

def _extract_nodeid_from_qualifiers(elem: Dict[str, Any]) -> Optional[str]:
    """Extrai nodeId de uma lista de qualifiers se houver um do tipo opcua.nodeid."""
    for q in elem.get("qualifiers", []) or []:
        qtype = (q.get("type") or "").lower()
        if "opcua.nodeid" in qtype:  # Simplificado: checa substring
            nodeid = q.get("value")
            if _is_nodeid(nodeid):
                return nodeid
    return None

async def _update_elem_from_opcua(client: Client, elem: Dict[str, Any]) -> None:
    """Atualiza um elemento AAS lendo valor do OPC UA se houver qualifier apropriado."""
    nodeid = _extract_nodeid_from_qualifiers(elem)
    if nodeid:
        val, _, _ = await _read_value_safe(client, nodeid)
        want = _map_xs_to_coerce(elem.get("valueType"))
        elem["value"] = _coerce(val, want)

    if isinstance(elem.get("value"), list) and elem.get("modelType") in ("SubmodelElementCollection", "Entity"):
        for child in elem["value"]:
            if isinstance(child, dict):
                await _update_elem_from_opcua(client, child)
    for k in ("submodelElements", "elements"):
        if isinstance(elem.get(k), list):
            for child in elem[k]:
                if isinstance(child, dict):
                    await _update_elem_from_opcua(client, child)

async def update_aas_submodels_from_opcua(client: Client, folder: str) -> List[str]:
    """
    Atualiza arquivos JSON de submodelos na pasta, lendo valores do OPC UA.
    
    Args:
        client: Cliente OPC UA conectado
        folder: Caminho da pasta com arquivos Submodel_*.json
        
    Returns:
        Lista de caminhos dos arquivos modificados
    """
    changed: List[str] = []
    base = Path(folder)
    if not base.exists():
        return changed
    for jf in sorted(base.glob("Submodel_*.json")):
        try:
            with open(jf, "r", encoding="utf-8") as f:
                sm = json.load(f)
            for key in ("submodelElements", "elements"):
                if isinstance(sm.get(key), list):
                    for elem in sm[key]:
                        if isinstance(elem, dict):
                            await _update_elem_from_opcua(client, elem)
            
            # Escrita atômica via arquivo temporário
            write_json_atomic(str(jf), sm, indent=2, ensure_ascii=False)
            changed.append(str(jf))
            
        except Exception as e:
            logger.exception("Falha ao atualizar %s", jf)
    return changed

async def _run_once(client: Client, config: Dict[str, Any]) -> None:
    """Executa um ciclo completo de leitura/atualização."""
    data = await map_opcua_to_submodels(client, config)

    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    try:
        write_json_atomic(OUTPUT_FILE, data, indent=4, ensure_ascii=False)
        logger.info("Dados atualizados salvos em: %s", OUTPUT_FILE)
    except Exception as e:
        logger.exception("Falha ao salvar dados em %s", OUTPUT_FILE)
        raise

    try:
        save_all_submodels(DB_PATH, data)
        logger.info("Snapshots e séries históricas salvos em: %s", DB_PATH)
    except Exception as e:
        logger.exception("Falha ao persistir no banco: %s", e)

    changed = await update_aas_submodels_from_opcua(client, AAS_SUBMODELS_DIR)
    if changed:
        logger.info("Submodelos AAS atualizados:")
        for p in changed:
            logger.info(" - %s", p)
    else:
        logger.info("Nenhum submodelo AAS atualizado (pasta não encontrada ou vazia)")

def _extract_client_settings(config: Dict[str, Any]) -> Tuple[bool, float]:
    """Extrai configurações do cliente do bloco _client/client do config."""
    s = {}
    if isinstance(config, dict):
        s = config.get("_client") or config.get("client") or {}
    enabled = bool(s.get("enabled", True))
    try:
        interval = float(s.get("interval_seconds", 0.1))
    except Exception as e:
        logger.warning("Intervalo inválido no config, usando 0.1s: %s", e)
        interval = 0.1
    return enabled, interval

async def main():
    """Função principal - processa argumentos e executa cliente."""
    parser = argparse.ArgumentParser(description="OPC UA AAS Client")
    parser.add_argument("--once", action="store_true", help="Executa apenas um ciclo e sai")
    parser.add_argument("--interval", type=float, default=None, help="Intervalo entre ciclos em segundos")
    parser.add_argument("--enabled", dest="enabled", action="store_true", help="Habilita execução (sobrescreve config)")
    parser.add_argument("--disabled", dest="enabled", action="store_false", help="Desabilita execução (sobrescreve config)")
    parser.set_defaults(enabled=None)
    args = parser.parse_args()

    try:
        config = load_config(CONFIG_FILE)
    except Exception as e:
        logger.error("Não foi possível carregar configuração: %s", e)
        return

    cfg_enabled, cfg_interval = _extract_client_settings(config)

    env_enabled = os.getenv("OPCUA_CLIENT_ENABLED")
    if env_enabled is not None:
        cfg_enabled = env_enabled.strip().lower() in ("1", "true", "yes", "on")
    env_interval = os.getenv("OPCUA_CLIENT_INTERVAL")
    if env_interval:
        try:
            cfg_interval = float(env_interval)
        except ValueError as e:
            logger.warning("Intervalo inválido em OPCUA_CLIENT_INTERVAL: %s", e)

    if args.enabled is not None:
        cfg_enabled = args.enabled
    if args.interval is not None:
        cfg_interval = args.interval

    if not cfg_enabled:
        logger.info("Cliente OPC UA desabilitado por configuração")
        return

    try:
        async with Client(url=SERVER_URL, timeout=60_000) as client:
            logger.info("Conectado ao servidor OPC UA")
            if args.once:
                await _run_once(client, config)
            else:
                logger.info("Execução cíclica habilitada. Intervalo: %.2fs (Ctrl+C para parar)", cfg_interval)
                while True:
                    await _run_once(client, config)
                    await asyncio.sleep(cfg_interval)
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário")
    except Exception as e:
        logger.exception("Erro fatal durante execução")
        raise

if __name__ == "__main__":
    asyncio.run(main())