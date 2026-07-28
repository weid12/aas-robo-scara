# ------------------------------------------------------------------------------------------------------------------
#   Módulo cliente para conectar a um servidor OPC UA, ler dados de um ativo (robô SCARA), mapeá-los para submodelos 
#   do Asset Administration Shell (AAS), e persistir os dados.
#   Este script pode ser executado de duas formas:
#   1. Em modo de ciclo único (--once"), onde ele lê os dados, salva e termina.
#   2. Em modo de loop contínuo, onde ele repete o ciclo de leitura e salvamento em um intervalo configurável.
#   A configuração é carregada de múltiplas fontes com a seguinte ordem de precedência:
#   1. Argumentos de linha de comando (CLI) -
#   2. Variáveis de ambiente.
#   3. Arquivo de configuração JSON (config opcua json").
#   O fluxo principal de dados é:
#   Conectar ao servidor OPC UA;
#   Ler os nós (nodes) OPC UA especificados no arquivo de configuração;
#   Mapear os valores lidos para uma estrutura de dicionário que representa os submodelos AAS;
#   Salvar o snapshot mais recente em um arquivo JSON ("latest_data.json").
# ------------------------------------------------------------------------------------------------------------------

import asyncio
import json
import datetime
import argparse
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    # Importar módulo persist_db do pacote persistence/db
    from persistence.db.persist_db import save_all_submodels
except ImportError as e:
    logger.warning("Falha ao importar save_all_submodels diretamente: %s", e)
    import sys as _sys
    from pathlib import Path as _Path
    
    # Adiciona o diretório raiz do projeto ao sys.path para resolver imports relativos
    # O script está em acquisition/client/, então parents[2] é a raiz do projeto
    _root = str(_Path(__file__).resolve().parents[2])
    if _root not in _sys.path:
        _sys.path.append(_root)
        logger.info("Adicionado diretório raiz ao path: %s", _root)
    
    try:
        from persistence.db.persist_db import save_all_submodels  # type: ignore
        logger.info("Import via fallback bem sucedido após adicionar raiz ao path")
    except ImportError as e:
        logger.error("Falha definitiva ao importar save_all_submodels. Verifique se o diretório 'persistence/db' existe e contém persist_db.py")
        raise

# Resolver caminhos relativos ao diretório do pacote deste arquivo para evitar
# problemas ao executar a partir de diretórios de trabalho diferentes.
# O script está em acquisition/client/, então parents[2] é a raiz do projeto.
_ROOT_DIR = Path(__file__).resolve().parents[2]
_OPCUA_CLIENT_DIR = Path(__file__).resolve().parent

# Configurações - podem ser sobrescritas por variáveis de ambiente
CONFIG_FILE = str(_OPCUA_CLIENT_DIR / "config_opcua.json")
OUTPUT_FILE = str(_OPCUA_CLIENT_DIR / "latest_data.json")
AAS_SUBMODELS_DIR = str(_ROOT_DIR / "digital_twin/submodels")
SERVER_URL = os.getenv("OPCUA_SERVER_URL", "opc.tcp://192.168.0.102:4880/Staubli")
DB_PATH = str(_ROOT_DIR / "persistence/storage/aas_history.sqlite3")

# Caminho para o banco de dados do Backend AAS Web
BACKEND_DB_PATH = str(_ROOT_DIR / "web" / "backend" / "robot_api" / "aas_robot_scara.db")

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
    if isinstance(x, bool):
        return x
    if isinstance(x, float):
        return round(x, 2)
    if isinstance(x, (str, int)):
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
- Resolve valores OPC UA para cada nó
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

    # Injeta data/horário real de execução para que o frontend mostre quando
    # os dados foram coletados, independente do relógio do servidor OPC UA.
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if isinstance(data.get("RuntimeDiagnostics"), dict):
        data["RuntimeDiagnostics"]["CurrentTime"] = now_iso
    else:
        data["RuntimeDiagnostics"] = {"CurrentTime": now_iso}

    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    try:
        write_json_atomic(OUTPUT_FILE, data, indent=4, ensure_ascii=False)
        logger.info("Dados atualizados salvos em: %s", OUTPUT_FILE)
    except Exception as e:
        logger.exception("Falha ao salvar dados em %s", OUTPUT_FILE)
        raise

    # 1. Tenta salvar no SQLite legando (persistence/storage)
    try:
        save_all_submodels(DB_PATH, data)
        logger.info("Snapshots e séries históricas salvos em: %s", DB_PATH)
    except Exception as e:
        logger.exception("Falha ao persistir no banco submodels (AAS): %s", e)

    # 2. Tenta salvar no SQLite do web/backend onde a API do frontend consulta
    try:
        _save_to_backend_db(data, now_iso)
        logger.info("Dados persistidos para web/backend -> aas_robot_scara.db")
    except Exception as e:
        logger.exception("Falha ao persistir no banco web/backend: %s", e)

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


# ==================================================================================================================
# Modo Subscription (push-based)
# ==================================================================================================================

def _extract_nodeid_map(config: Any, path: tuple = ()) -> Dict[str, list]:
    """
    Percorre o config recursivamente e retorna um mapa:
        { nodeid_string: [ (path_tuple), ... ] }
    para todos os nós com NodeId válido (excluindo _client).
    Suporta múltiplos paths para o mesmo NodeId (ex: JointPosition1-4
    que apontam para o mesmo nó de array no servidor Stäubli).
    """
    result: Dict[str, list] = {}
    if isinstance(config, dict):
        for k, v in config.items():
            if k == "_client":
                continue
            sub = _extract_nodeid_map(v, path + (k,))
            for nid, paths in sub.items():
                result.setdefault(nid, []).extend(paths)
    elif isinstance(config, list):
        for i, v in enumerate(config):
            sub = _extract_nodeid_map(v, path + (i,))
            for nid, paths in sub.items():
                result.setdefault(nid, []).extend(paths)
    elif isinstance(config, str) and _is_nodeid(config):
        result.setdefault(config, []).append(path)
    elif isinstance(config, dict) and "nodeId" in config:
        nid = config["nodeId"]
        if _is_nodeid(nid):
            result.setdefault(nid, []).append(path)
    return result


def _set_nested(d: dict, path: tuple, value: Any) -> None:
    """Atualiza valor em dicionário aninhado usando path como sequência de chaves."""
    for key in path[:-1]:
        if isinstance(key, int):
            while len(d) <= key:
                d.append(None)
            d = d[key]
        else:
            if key not in d:
                d[key] = {}
            d = d[key]
    last = path[-1]
    if isinstance(last, int):
        while len(d) <= last:
            d.append(None)
        d[last] = value
    else:
        d[last] = value


class DataChangeHandler:
    """
    Handler de subscription OPC UA.
    Recebe notificações push do servidor e atualiza o data_store em memória.
    """

    def __init__(self, node_map: Dict[str, list], data_store: dict):
        self._node_map = node_map      # nodeid_str -> [path_tuple, ...]
        self.data_store = data_store   # dict compartilhado (estrutura igual ao latest_data.json)
        self.dirty = False             # flag: houve mudança desde o último write?
        self._nodeid_cache: Dict[Any, str] = {}  # node.nodeid -> nodeid_str

    def datachange_notification(self, node, val, data):
        """Chamado pelo asyncua quando um valor monitorado muda."""
        try:
            nodeid_str = self._nodeid_cache.get(node.nodeid)
            if nodeid_str is None:
                nodeid_str = node.nodeid.to_string()
                self._nodeid_cache[node.nodeid] = nodeid_str

            paths = self._node_map.get(nodeid_str)
            if not paths:
                return

            converted = _to_builtin(val)
            # Atualiza TODOS os paths registrados para este NodeId.
            # Necessário porque JointPosition1–4 usam o mesmo NodeId de array.
            for path in paths:
                _set_nested(self.data_store, path, converted)
            self.dirty = True
            logger.debug("Subscription update: %s = %s (paths: %d)", nodeid_str, converted, len(paths))
        except Exception as e:
            logger.debug("Erro no handler de notificação: %s", e)

    def status_change_notification(self, status):
        """Chamado quando o status da subscription muda (ex: timeout, reconnect)."""
        logger.warning("Status da subscription OPC UA mudou: %s", status)


async def _writer_task(
    handler: DataChangeHandler,
    config: Dict[str, Any],
    write_interval: float,
) -> None:
    """
    Task de escrita: a cada write_interval segundos, se houver mudanças,
    grava latest_data.json, salva no SQLite e atualiza submodelos AAS.
    """
    logger.info("Writer task iniciada (intervalo: %.2fs)", write_interval)
    while True:
        await asyncio.sleep(write_interval)
        handler.dirty = False

        data = dict(handler.data_store)  # cópia rasa para escrita segura
        # Injeta horário real de execução
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if isinstance(data.get("RuntimeDiagnostics"), dict):
            data["RuntimeDiagnostics"]["CurrentTime"] = now_iso
        else:
            data["RuntimeDiagnostics"] = {"CurrentTime": now_iso}

        # Grava latest_data.json
        try:
            Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
            write_json_atomic(OUTPUT_FILE, data, indent=4, ensure_ascii=False)
            logger.info("[subscription] latest_data.json atualizado")
        except Exception as e:
            logger.exception("Falha ao salvar latest_data.json: %s", e)

        # Persiste nos bancos SQLite
        try:
            save_all_submodels(DB_PATH, data)
            logger.debug("[subscription] SQLite AAS history atualizado")
        except Exception as e:
            logger.exception("Falha ao persistir no banco AAS history: %s", e)
            
        try:
            _save_to_backend_db(data, now_iso)
            logger.debug("[subscription] SQLite web backend atualizado")
        except Exception as e:
            logger.exception("Falha ao persistir no banco web backend: %s", e)

async def run_subscription(client: Client, config: Dict[str, Any]) -> None:
    """
    Modo subscription: monitora nós OPC UA e recebe dados por push.

    1. Inicializa o data_store com um poll único (valores iniciais + manual-only)
    2. Cria a subscription no servidor
    3. Adiciona todos os nós como MonitoredItems
    4. Lança o writer_task em paralelo e aguarda indefinidamente
    """
    client_cfg = config.get("_client") or {}
    publishing_interval_ms = float(client_cfg.get("publishing_interval_ms", 200))
    write_interval_s = float(client_cfg.get("write_interval_s", 0.5))

    logger.info("Modo subscription ativo | publishing_interval=%.0fms | write_interval=%.2fs",
                publishing_interval_ms, write_interval_s)

    # 1. Poll inicial para popular o data_store (resolve valores manuais e iniciais)
    logger.info("Realizando poll inicial para inicializar data_store...")
    data_store = await map_opcua_to_submodels(client, config)
    logger.info("Poll inicial concluído. Iniciando subscription.")

    # 2. Extrai mapa de NodeIds
    node_map = _extract_nodeid_map(config)
    logger.info("Monitorando %d nós OPC UA via subscription", len(node_map))

    # 3. Cria handler e subscription
    handler = DataChangeHandler(node_map, data_store)
    subscription = await client.create_subscription(
        period=publishing_interval_ms,
        handler=handler,
    )

    # 4. Adiciona nós como MonitoredItems
    nodes = [client.get_node(nid) for nid in node_map]
    if nodes:
        await subscription.subscribe_data_change(nodes)
        logger.info("MonitoredItems criados com sucesso")

    # 5. Lança writer task e aguarda (a subscription recebe dados em background)
    handler.dirty = True  # força uma escrita inicial imediata
    writer = asyncio.ensure_future(_writer_task(handler, config, write_interval_s))
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        writer.cancel()
        try:
            await subscription.delete()
        except Exception:
            pass

async def main():
    """Função principal - processa argumentos e executa cliente."""
    parser = argparse.ArgumentParser(description="OPC UA AAS Client")
    parser.add_argument("--once", action="store_true", help="Executa apenas um ciclo e sai (modo polling)")
    parser.add_argument("--interval", type=float, default=None, help="Intervalo entre ciclos em segundos")
    parser.add_argument("--enabled", dest="enabled", action="store_true", help="Habilita execução (sobrescreve config)")
    parser.add_argument("--disabled", dest="enabled", action="store_false", help="Desabilita execução (sobrescreve config)")
    parser.add_argument("--subscription", action="store_true",
                        help="Usa OPC UA Subscriptions para receber dados por push (mais rápido que polling)")
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

    # Determina modo: --subscription flag ou config._client.mode == "subscription"
    client_cfg = (config.get("_client") or config.get("client") or {})
    cfg_mode = client_cfg.get("mode", "polling")
    use_subscription = args.subscription or (cfg_mode == "subscription")

    if not cfg_enabled:
        logger.info("Cliente OPC UA desabilitado por configuração")
        return

    if use_subscription:
        logger.info("Modo: SUBSCRIPTION (push-based)")
    else:
        logger.info("Modo: POLLING (ciclo a cada %.2fs)", cfg_interval)

    RETRY_DELAYS = [5, 10, 30, 60]  # segundos antes de cada tentativa de reconexão

    attempt = 0
    while True:
        try:
            async with Client(url=SERVER_URL, timeout=60_000) as client:
                logger.info("Conectado ao servidor OPC UA")
                _record_connection(BACKEND_DB_PATH)
                attempt = 0  # reset ao reconectar com sucesso
                if args.once:
                    await _run_once(client, config)
                    break
                elif use_subscription:
                    await run_subscription(client, config)
                else:
                    logger.info("Execução cíclica habilitada. Intervalo: %.2fs (Ctrl+C para parar)", cfg_interval)
                    while True:
                        await _run_once(client, config)
                        await asyncio.sleep(cfg_interval)
        except KeyboardInterrupt:
            logger.info("Interrompido pelo usuário")
            break
        except OSError as e:
            # Erros de rede (WinError 121, ECONNREFUSED, etc.)
            if args.once:
                logger.exception("Erro fatal durante execução")
                raise
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            logger.warning(
                "Falha de rede ao conectar/manter conexão com o servidor OPC UA: %s. "
                "Tentativa %d — aguardando %ds antes de reconectar...",
                e, attempt + 1, delay
            )
            attempt += 1
            await asyncio.sleep(delay)
        except Exception as e:
            if args.once:
                logger.exception("Erro fatal durante execução")
                raise
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            logger.warning(
                "Erro inesperado: %s. Tentativa %d — aguardando %ds antes de reconectar...",
                e, attempt + 1, delay
            )
            attempt += 1
            await asyncio.sleep(delay)



import sqlite3

def _record_connection(db_path: str) -> None:
    """Persists each successful OPC UA connection event to the aas_robot_scara.db."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS opcua_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    connected_at TEXT NOT NULL
                )
            ''')
            conn.execute(
                "INSERT INTO opcua_connections (connected_at) VALUES (?)",
                (datetime.datetime.now(datetime.timezone.utc).isoformat(),)
            )
            conn.commit()
        logger.info("OPC UA connection recorded in opcua_connections table")
    except Exception as e:
        logger.warning("Failed to record OPC UA connection: %s", e)


def _save_to_backend_db(data: Dict[str, Any], timestamp_iso: str) -> None:
    """Extrai os dados de runtime do SCARA em `data` e indere um RobotState dentro do aas_robot_scara.db do backend."""
    op_data = data.get("OperationalData", {})
    temp_data = data.get("TemperatureData", {})
    
    # Extrai Joints
    joint_pos = op_data.get("JointPosition1", [])
    j1 = joint_pos[0] if len(joint_pos) > 0 else None
    j2 = joint_pos[1] if len(joint_pos) > 1 else None
    
    j3_raw = joint_pos[2] if len(joint_pos) > 2 else None
    j3_mm = None
    if j3_raw is not None:
        # Conversão idêntica ao api.py (0 a 180 = 0mm a -200mm)
        j3_angle = max(0.0, min(180.0, float(j3_raw)))
        j3_mm = -(j3_angle / 180.0) * 200.0
        
    j4 = joint_pos[3] if len(joint_pos) > 3 else None
    
    status = op_data.get("RobotStatus", "Unknown")
    mode = op_data.get("WorkingMode", "Unknown")
    temp_c = temp_data.get("IWtemperature", None)
    
    # Tenta obter ciclo e energia
    cycle_time = op_data.get("CycleTime", "0s")
    cycle_s_str = str(cycle_time).replace("s", "")
    try:
        cycle_s = float(cycle_s_str)
    except:
        cycle_s = None
        
    energy = None # A definir, pode ler algo em PowerData 

    # Certifique que a pasta exista (pra safety apenas)
    Path(BACKEND_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(BACKEND_DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Garante a tabela
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS robot_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                status VARCHAR(32) NOT NULL,
                mode VARCHAR(32) NOT NULL,
                cycle_time_s FLOAT,
                joint1_deg FLOAT,
                joint2_deg FLOAT,
                joint3_mm FLOAT,
                joint4_deg FLOAT,
                temperature_c FLOAT,
                energy_kwh FLOAT,
                oee FLOAT,
                availability FLOAT,
                performance FLOAT,
                quality FLOAT
            )
        ''')

        cursor.execute('SELECT status FROM robot_state ORDER BY id DESC LIMIT 1')
        last_row = cursor.fetchone()
        if last_row is None or last_row[0] != status:
            # O backend api.py mapeia timestamp usando `models.RobotState.timestamp` e ele espera ISO/Datetime string no SQLite
            cursor.execute('''
                INSERT INTO robot_state (
                    timestamp, status, mode, cycle_time_s, joint1_deg, joint2_deg, joint3_mm, joint4_deg, temperature_c, energy_kwh
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp_iso, status, mode, cycle_s, j1, j2, j3_mm, j4, temp_c, energy))
            
            conn.commit()


if __name__ == "__main__":
    asyncio.run(main())
