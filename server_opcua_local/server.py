# ------------------------------------------------------------------------------------------------------------------
#   Módulo servidor OPC UA local que expõe dados do Asset Administration Shell (AAS) via OPC UA.
#   
#   Este servidor realiza as seguintes funções:
#   1. Carrega dados dos submodelos AAS do arquivo latest_data.json
#   2. Cria uma estrutura de nós OPC UA que reflete a hierarquia dos submodelos
#   3. Inicia um servidor OPC UA na porta 4881
#   4. Monitora alterações no arquivo latest_data.json e atualiza os nós dinamicamente
#   
#   Estrutura do servidor:
#   - Nó raiz: SCARA_TS2_80
#     └── Submodelos (TechnicalData, OperationalData, etc.)
#         └── Variáveis com dados do robô
#   
#   O servidor atualiza automaticamente os valores quando o arquivo latest_data.json é modificado,
#   permitindo que clientes OPC UA vejam alterações em tempo real.
# ------------------------------------------------------------------------------------------------------------------

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from asyncua import Server, ua

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("opcua_server")

# ---------- Utilitários de tipo e variantes OPC UA ----------

def _guess_variant_type(value: Any) -> ua.VariantType:
    """
    Mapeia tipos Python para tipos OPC UA apropriados.
    
    Args:
        value: Valor Python a ser convertido
        
    Returns:
        ua.VariantType correspondente ao tipo Python
    """
    if isinstance(value, bool):
        return ua.VariantType.Boolean
    if isinstance(value, int):
        return ua.VariantType.Int64
    if isinstance(value, float):
        return ua.VariantType.Double
    return ua.VariantType.String

# ---------- Funções de construção da árvore de nós ----------

async def _add_recursively(
    parent_node, 
    idx: int, 
    name: str, 
    value: Any, 
    path: List[str],
    leaves: Dict[Tuple[str, ...], Tuple[object, bool]]
) -> None:
    """
    Adiciona nós e variáveis recursivamente na árvore OPC UA.
    
    Args:
        parent_node: Nó pai onde novos nós serão adicionados
        idx: Índice do namespace OPC UA
        name: Nome do nó a ser criado
        value: Valor a ser armazenado (dict, list ou valor simples)
        path: Caminho atual na hierarquia
        leaves: Dicionário que mapeia caminhos para (nó, is_list)
    """
    if isinstance(value, dict):
        obj = await parent_node.add_object(idx, name)
        for k, v in value.items():
            await _add_recursively(obj, idx, k, v, path + [name], leaves)
        return

    full_path = path + [name]
    if isinstance(value, list):
        vtype = ua.VariantType.String if not value else _guess_variant_type(value[0])
        variant = ua.Variant(value, vtype)
        node = await parent_node.add_variable(idx, name, variant)
        leaves[tuple(full_path)] = (node, True)
        return

    vtype = _guess_variant_type(value)
    node = await parent_node.add_variable(idx, name, value, varianttype=vtype)
    leaves[tuple(full_path)] = (node, False)

# ---------- Funções de atualização de dados ----------

def _get_from_path(data: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    """
    Obtém um valor de um dicionário aninhado usando um caminho de chaves.
    
    Args:
        data: Dicionário de dados
        path: Tupla de chaves formando o caminho
        
    Returns:
        Valor encontrado ou None se caminho não existir
    """
    cur: Any = data
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur

async def _apply_updates(
    leaves: Dict[Tuple[str, ...], Tuple[object, bool]],
    data: Dict[str, Any]
) -> None:
    """
    Atualiza os valores das variáveis OPC UA com novos dados.
    
    Args:
        leaves: Dicionário mapeando caminhos para (nó, is_list)
        data: Novos dados a serem aplicados
    """
    for path, (node, is_list) in leaves.items():
        val = _get_from_path(data, path)
        if val is None:
            continue
        try:
            if is_list and isinstance(val, list):
                vtype = ua.VariantType.String if not val else _guess_variant_type(val[0])
                await node.write_value(ua.Variant(val, vtype))
            else:
                await node.write_value(val)
        except Exception as e:
            logger.debug(f"Erro ao atualizar {path}: {e}, tentando com Variant explícito")
            try:
                vtype = _guess_variant_type(val)
                await node.write_value(ua.Variant(val, vtype))
            except Exception as e:
                logger.warning(f"Falha ao atualizar {path}: {e}")

# ---------- Monitor de alterações no arquivo ----------

async def _watch_latest(
    latest_data_path: Path,
    leaves: Dict[Tuple[str, ...], Tuple[object, bool]],
    interval: float = 1.0
) -> None:
    """
    Monitora alterações no arquivo latest_data.json e atualiza variáveis.
    
    Args:
        latest_data_path: Caminho do arquivo a ser monitorado
        leaves: Dicionário de variáveis a serem atualizadas
        interval: Intervalo entre verificações em segundos
    """
    last_mtime: float | None = None
    while True:
        try:
            if latest_data_path.exists():
                mtime = latest_data_path.stat().st_mtime
                if last_mtime is None or mtime > last_mtime:
                    with open(latest_data_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    await _apply_updates(leaves, data)
                    last_mtime = mtime
                    logger.debug("Dados atualizados com sucesso")
        except Exception as e:
            logger.error(f"Falha ao aplicar atualizações: {e}")
        await asyncio.sleep(interval)

# ---------- Função principal ----------

async def main() -> None:
    """Inicializa e executa o servidor OPC UA."""
    # Configuração de caminhos
    latest_data_path = Path(__file__).parent.parent / "opcua_client" / "latest_data.json"

    # Carrega dados iniciais
    with open(latest_data_path, "r", encoding="utf-8") as f:
        all_data = json.load(f)
    
    logger.info(f"Publicando submodelos: {', '.join(all_data.keys())}")

    # Inicializa servidor
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4881/")

    # Configura namespace
    uri = "http://example.com/robot/aas"
    idx = await server.register_namespace(uri)

    # Cria estrutura de nós
    objects = server.get_objects_node()
    robot_node = await objects.add_object(idx, "SCARA_TS2_80")

    # Mapeia variáveis folha para atualização
    leaves: Dict[Tuple[str, ...], Tuple[object, bool]] = {}
    for submodel_name, submodel_value in all_data.items():
        await _add_recursively(robot_node, idx, submodel_name, submodel_value, [], leaves)

    # Inicia servidor e monitor
    await server.start()
    logger.info("Servidor OPC UA iniciado em opc.tcp://0.0.0.0:4881/")

    try:
        await _watch_latest(latest_data_path, leaves, interval=1.0)
    finally:
        await server.stop()
        logger.info("Servidor OPC UA finalizado")

if __name__ == "__main__":
    asyncio.run(main())
