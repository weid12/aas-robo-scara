# Persistência de Submodelos (SQLite)

Este diretório contém o módulo de persistência usado para armazenar snapshots dos submodelos e séries históricas numéricas em um banco SQLite local.

Arquivos relevantes:
- `persist_db.py` — funções para inicialização e gravação no banco.
- Banco gerado em tempo de execução: `data/aas_history.sqlite3` (caminho configurável no cliente).

## Esquema do Banco

Tabelas criadas automaticamente:

1) `submodel_snapshots_json`
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `submodel_name` TEXT NOT NULL
- `data` TEXT NOT NULL (JSON completo do submodelo)
- `created_at` TEXT NOT NULL (timestamp ISO-8601 em UTC)

2) `submodel_snapshots` (normalizada: idShort/value em colunas)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `submodel_name` TEXT NOT NULL
- `idshort` TEXT NOT NULL (caminho completo dentro do submodelo, ex.: `OperationalData.JointPosition1.0`)
- `value_text` TEXT NULL (strings, objetos ou listas serializados)
- `value_num` REAL NULL (valores numéricos)
- `value_bool` INTEGER NULL (0/1)
- `created_at` TEXT NOT NULL (timestamp ISO-8601 em UTC)

3) `timeseries`
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `submodel_name` TEXT NOT NULL
- `element_path` TEXT NOT NULL (caminho pontilhado, ex.: `OperationalData.JointPosition1_0`)
- `value` REAL NOT NULL (apenas numérico: int/float)
- `created_at` TEXT NOT NULL (timestamp ISO-8601 em UTC)

Índices:
- `idx_timeseries_lookup` em `(submodel_name, element_path, created_at)`
- `idx_subsnap_lookup` em `(submodel_name, idshort, created_at)`

## Como é preenchido

O cliente (`opcua_client/client_asyncua.py`) chama `save_all_submodels(DB_PATH, data)` após ler os dados do servidor OPC UA. Esse método:
- Insere um snapshot JSON por submodelo em `submodel_snapshots_json`.
- Insere um conjunto de linhas normalizadas por submodelo em `submodel_snapshots` (uma linha por idShort/valor).
- Percorre recursivamente os valores e insere somente valores numéricos (int/float) em `timeseries`, com o caminho completo do elemento.

## Consultas úteis (exemplos)

- Últimos 5 snapshots do submodelo `Identification`:
  ```sql
  SELECT id, submodel_name, created_at, length(data) AS bytes
  FROM submodel_snapshots
  WHERE submodel_name = 'Identification'
  ORDER BY created_at DESC
  LIMIT 5;
  ```

- Série temporal de um ponto específico (ex.: `OperationalData.JointPosition1_0`) na última hora:
  ```sql
  SELECT created_at, value
  FROM timeseries
  WHERE submodel_name = 'OperationalData'
    AND element_path = 'OperationalData.JointPosition1_0'
    AND datetime(created_at) >= datetime('now', '-1 hour')
  ORDER BY created_at ASC;
  ```

- Últimos valores numéricos registrados do submodelo `TemperatureData`:
  ```sql
  SELECT element_path, value, created_at
  FROM timeseries
  WHERE submodel_name = 'TemperatureData'
  ORDER BY created_at DESC
  LIMIT 50;
  ```

- Snapshot mais recente de um submodelo (JSON completo):
  ```sql
  SELECT data
  FROM submodel_snapshots_json
  WHERE submodel_name = 'OperationalData'
  ORDER BY created_at DESC
  LIMIT 1;
  ```

- Últimos valores normalizados (idShort/valor) de um submodelo:
  ```sql
  SELECT idshort,
         COALESCE(value_text, CAST(value_num AS TEXT), CASE value_bool WHEN 1 THEN 'true' WHEN 0 THEN 'false' END) AS value,
         created_at
  FROM submodel_snapshots
  WHERE submodel_name = 'OperationalData'
  ORDER BY created_at DESC
  LIMIT 50;
  ```

## Uso com Dashboards

- Grafana, Superset, Metabase ou apps Python (Streamlit, Dash) podem consumir o SQLite diretamente.
- Para consultas eficientes no tempo, use os filtros por `created_at` e o índice existente.

## Manutenção

- Rotacionar/compactar o banco ocasionalmente pode ser útil em instalações de longa duração:
  - `VACUUM;` para compactar.
  - Mover dados antigos para outro arquivo (partitioning manual) se necessário.

## Configuração

- Caminho do banco é definido no cliente pela constante `DB_PATH` (padrão: `data/aas_history.sqlite3`).
