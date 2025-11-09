# ------------------------------------------------------------------------------------------------------------------
#   Módulo de persistência de dados para o Asset Administration Shell (AAS).
#   
#   Este módulo é responsável por:
#   1. Gerenciar o esquema do banco de dados SQLite
#   2. Persistir snapshots dos submodelos AAS
#   3. Manter séries temporais de valores numéricos
#   4. Fornecer consultas históricas dos dados
#   
#   Estrutura do banco:
#   1. submodel_snapshots_json: Snapshots JSON completos dos submodelos
#   2. submodel_snapshots: Versão normalizada com valores individuais
#   3. timeseries: Séries temporais de valores numéricos
#   
#   O módulo suporta:
#   - Persistência atômica (transações SQLite)
#   - Migração automática de dados legados
#   - Tratamento especial para arrays de posição das juntas
#   - Conversão automática de tipos para armazenamento otimizado
# ------------------------------------------------------------------------------------------------------------------

import json
import sqlite3
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple
from datetime import datetime, timezone

# Configuração do logging
logger = logging.getLogger(__name__)

# ---------- Utilitários de data/hora ----------

def _now_iso() -> str:
    """Retorna timestamp UTC atual em formato ISO."""
    return datetime.now(timezone.utc).isoformat()


def _table_info(con: sqlite3.Connection, table: str) -> Dict[str, Dict[str, Any]]:
    """
    Obtém informações sobre colunas de uma tabela.
    
    Args:
        con: Conexão SQLite
        table: Nome da tabela
        
    Returns:
        Dicionário com metadata das colunas
    """
    try:
        cur = con.execute(f"PRAGMA table_info('{table}')")
        cols: Dict[str, Dict[str, Any]] = {}
        for cid, name, ctype, notnull, dflt, pk in cur.fetchall():
            cols[name] = {
                "cid": cid,
                "type": ctype,
                "notnull": notnull,
                "default": dflt,
                "pk": pk,
            }
        return cols
    except sqlite3.OperationalError as e:
        logger.debug(f"Tabela {table} não existe: {e}")
        return {}


def _rename_table_columns(
    con: sqlite3.Connection, table: str, mapping: Dict[str, str]
) -> None:
    """
    Renomeia colunas em uma tabela de acordo com o mapeamento.
    
    Args:
        con: Conexão SQLite
        table: Nome da tabela
        mapping: Dicionário {nome_antigo: nome_novo} das colunas
        
    Raises:
        sqlite3.OperationalError: Se houver erro ao renomear tabela/colunas
    """
    try:
        # Obtenha informações de tabelas antigas
        old_cols = _table_info(con, table)
        if not old_cols:
            logger.debug(f"Tabela {table} não existe ou está vazia")
            return

        # Crie uma nova tabela com colunas renomeadas
        new_cols = []
        for old_name, col_info in old_cols.items():
            new_name = mapping.get(old_name, old_name)
            new_cols.append(
                f"{new_name} {col_info['type']}"
                + (" NOT NULL" if col_info["notnull"] else "")
                + (f" DEFAULT {col_info['default']}" if col_info["default"] else "")
                + (" PRIMARY KEY" if col_info["pk"] else "")
            )
        new_cols = ", ".join(new_cols)

        # Crie uma nova tabela com o novo esquema
        tmp_table = f"{table}_tmp"
        con.execute(f"CREATE TABLE {tmp_table} ({new_cols})")

        # Copiar dados da tabela antiga para a nova, renomeando as colunas
        old_names = list(old_cols.keys())
        new_names = [mapping.get(name, name) for name in old_names]
        con.execute(
            f"INSERT INTO {tmp_table} ({', '.join(new_names)}) SELECT {', '.join(old_names)} FROM {table}"
        )

        # Drop the old table
        con.execute(f"DROP TABLE {table}")

        # Rename the new table to the original name
        con.execute(f"ALTER TABLE {tmp_table} RENAME TO {table}")

        logger.debug(f"Renomeadas colunas em {table}: {mapping}")

    except sqlite3.OperationalError as e:
        logger.error(f"Erro ao renomear colunas de {table}: {e}")
        raise


def _ensure_schema(con: sqlite3.Connection) -> None:
    """
    Configura esquema do banco de dados com 3 tabelas principais:

    1. submodel_snapshots_json:
       - Snapshots JSON completos dos submodelos
       - 1 registro por submodelo/timestamp

    2. submodel_snapshots:
       - Versão normalizada com valores individuais  
       - 1 registro por elemento (idShort path)/timestamp

    3. timeseries:
       - Séries temporais de valores numéricos
       - Otimizada para consultas de evolução temporal

    Inclui migração de snapshots JSON antigos.
    
    Args:
        con: Conexão SQLite para executar DDL
        
    Raises:
        sqlite3.Error: Em caso de erro no DDL
    """
    # Se existir tabela antiga com coluna JSON 'data', renomeia para manter compatibilidade
    sm_cols = _table_info(con, "submodel_snapshots")
    if sm_cols and "data" in sm_cols:
        con.execute("ALTER TABLE submodel_snapshots RENAME TO submodel_snapshots_json;")

    # Table for full JSON snapshots (1 row per submodel per timestamp)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS submodel_snapshots_json (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submodel_name TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )

    # Normalized table: 1 row per element (idShort path) per timestamp
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS submodel_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submodel_name TEXT NOT NULL,
            idshort TEXT NOT NULL,
            value_text TEXT NULL,
            value_num REAL NULL,
            value_bool INTEGER NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    con.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_subsnap_lookup
        ON submodel_snapshots (submodel_name, idshort, created_at);
        """
    )

    # Timeseries table (numeric only)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS timeseries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submodel_name TEXT NOT NULL,
            element_path TEXT NOT NULL,
            value REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    con.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_timeseries_lookup
        ON timeseries (submodel_name, element_path, created_at);
        """
    )


def init_db(db_path: str) -> None:
    """
    Inicializa banco de dados garantindo existência de:
    1. Diretório pai do arquivo
    2. Tabelas e índices definidos em _ensure_schema()

    Args:
        db_path: Caminho do banco SQLite a ser criado/atualizado

    Raises:
        sqlite3.Error: Em caso de erro ao criar/alterar schema
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        _ensure_schema(con)


def _walk_numeric(base_path: Tuple[str, ...], node: Any) -> Iterable[Tuple[str, float]]:
    """
    Percorre estrutura buscando valores numéricos para série temporal.
    
    Args:
        base_path: Caminho atual na árvore (para construir path completo)
        node: Nó atual sendo percorrido
        
    Yields:
        Tuplas (path, valor) para cada valor numérico encontrado.
        Arrays são ignorados (mantidos apenas nos snapshots).
    """
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_numeric(base_path + (str(k),), v)
    elif isinstance(node, list):
        # Ignora listas em séries numéricas (arrays são mantidos apenas nos snapshots)
        return
    else:
        if isinstance(node, (int, float)):
            path = ".".join(base_path)
            yield path, float(node)


def _walk_leafs(base_path: Tuple[str, ...], node: Any) -> Iterable[Tuple[str, Any]]:
    """
    Percorre valores folha e retorna tuplas (caminho, valor):
    - Dict: recursão nas chaves
    - List: entradas indexadas com sufixo numérico
    - Escalares: retorna diretamente
    """
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_leafs(base_path + (str(k),), v)
        return
    if isinstance(node, list):
        # Regra especial: JointPositionN em OperationalData mapeia índice fixo
        if len(base_path) >= 2 and base_path[-2] == "OperationalData" and base_path[-1] in (
            "JointPosition1",
            "JointPosition2",
            "JointPosition3",
            "JointPosition4",
        ):
            idx = {"JointPosition1": 0, "JointPosition2": 1, "JointPosition3": 2, "JointPosition4": 3}[base_path[-1]]
            try:
                val = node[idx]
            except Exception:
                val = None
            path = ".".join(base_path)
            yield (path, val)
            return
        for i, v in enumerate(node):
            yield from _walk_leafs(base_path + (f"{i}",), v)
        return
    path = ".".join(base_path)
    yield (path, node)


def _split_value(v: Any) -> Tuple[Optional[str], Optional[float], Optional[int]]:
    """
    Converte valor para colunas de armazenamento otimizadas.
    
    Args:
        v: Valor a ser convertido (bool, número, None, ou outro)
        
    Returns:
        Tupla (valor_texto, valor_num, valor_bool) onde apenas um campo
        é preenchido conforme o tipo de entrada:
        - bool -> valor_bool (0/1)  
        - número -> valor_num (float)
        - nulo -> todos None
        - outro -> valor_texto (str/json)
    """
    if isinstance(v, bool):
        return None, None, 1 if v else 0
    if isinstance(v, (int, float)):
        return None, float(v), None
    if v is None:
        return None, None, None
    return (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v), None, None)


def save_all_submodels(db_path: str, all_data: Dict[str, Any]) -> None:
    """
    Salva snapshot dos submodelos AAS em múltiplos formatos otimizados.

    Para cada submodelo:
    1. Salva JSON completo (snapshot_json)
    2. Extrai valores individuais normalizados (snapshot) 
    3. Extrai valores numéricos para séries temporais

    Args:
        db_path: Caminho do banco SQLite
        all_data: Dict com submodelos {nome: conteúdo}

    Raises:
        sqlite3.Error: Em caso de erro no banco de dados
        Exception: Em caso de erro ao processar valores 
    """
    init_db(db_path)
    # Backfill único ao migrar de tabela somente JSON antiga
    try:
        backfill_normalized_from_json(db_path)
    except Exception:
        pass
    created_at = _now_iso()
    with sqlite3.connect(db_path) as con:
        con.execute("BEGIN")
        try:
            for submodel_name, submodel_value in all_data.items():
                # Armazena snapshot JSON completo por submodelo
                con.execute(
                    "INSERT INTO submodel_snapshots_json(submodel_name, data, created_at) VALUES (?,?,?)",
                    (submodel_name, json.dumps(submodel_value, ensure_ascii=False), created_at),
                )

                # Armazena linhas normalizadas idShort/valor
                kv_rows = []
                for path, val in _walk_leafs((), submodel_value):
                    # idshort é o caminho completo dentro do submodelo
                    idshort = f"{submodel_name}.{path}" if path else submodel_name
                    vt, vn, vb = _split_value(val)
                    kv_rows.append((submodel_name, idshort, vt, vn, vb, created_at))
                if kv_rows:
                    con.executemany(
                        """
                        INSERT INTO submodel_snapshots(
                            submodel_name, idshort, value_text, value_num, value_bool, created_at
                        ) VALUES (?,?,?,?,?,?)
                        """,
                        kv_rows,
                    )

                # Armazena pontos numéricos para consultas de séries temporais
                rows = list(_walk_numeric((submodel_name,), submodel_value))
                if rows:
                    con.executemany(
                        "INSERT INTO timeseries(submodel_name, element_path, value, created_at) VALUES (?,?,?,?)",
                        [(submodel_name, path, val, created_at) for path, val in rows],
                    )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise


def backfill_normalized_from_json(db_path: str) -> int:
    """
    Migração de snapshots JSON antigos para formato normalizado.
    Executada uma única vez quando a tabela normalizada está vazia.
    
    O processo:
    1. Verifica se tabela normalizada está vazia
    2. Lê snapshots JSON antigos
    3. Converte para formato normalizado
    4. Insere registros normalizados
    5. Mantém ambas as versões

    Args:
        db_path: Caminho do banco SQLite
        
    Returns:
        Número de registros inseridos na tabela normalizada
        
    Raises:
        sqlite3.Error: Em caso de erro no banco de dados
        json.JSONDecodeError: Se JSON inválido
    """
    init_db(db_path)
    inserted = 0
    with sqlite3.connect(db_path) as con:
        cur = con.execute("SELECT COUNT(1) FROM submodel_snapshots")
        if cur.fetchone()[0] > 0:
            return 0
        cur = con.execute("SELECT submodel_name, data, created_at FROM submodel_snapshots_json")
        rows = cur.fetchall()
        con.execute("BEGIN")
        try:
            for submodel_name, data_json, created_at in rows:
                try:
                    submodel_value = json.loads(data_json)
                except Exception:
                    continue
                kv_rows = []
                for path, val in _walk_leafs((), submodel_value):
                    idshort = f"{submodel_name}.{path}" if path else submodel_name
                    vt, vn, vb = _split_value(val)
                    kv_rows.append((submodel_name, idshort, vt, vn, vb, created_at))
                if kv_rows:
                    con.executemany(
                        """
                        INSERT INTO submodel_snapshots(
                            submodel_name, idshort, value_text, value_num, value_bool, created_at
                        )
                        """,
                        kv_rows,
                    )
                    inserted += len(kv_rows)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    return inserted
