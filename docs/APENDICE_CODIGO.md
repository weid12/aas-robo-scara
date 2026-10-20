# Apêndice A — Seções Principais de Código por Camada RAMI 4.0

Este apêndice apresenta a seção de código principal de cada camada do modelo de arquitetura RAMI 4.0 (*Reference Architecture Model Industrie 4.0*) responsável pelo funcionamento do sistema de monitoramento do robô SCARA Stäubli TS2-80. As listagens foram extraídas do código-fonte e reduzidas aos trechos essenciais.

**Quadro A.1 — Camadas RAMI 4.0 e respectivos arquivos-fonte.**

| Camada RAMI 4.0 | Componente | Arquivo-fonte |
|-----------------|------------|---------------|
| 2 — Integration | Mapeamento semântico OPC UA → AAS | `acquisition/client/config_opcua.json` |
| 3 — Communication | Cliente OPC UA (subscription) | `acquisition/client/client_asyncua.py` |
| 4 — Information | Persistência e esquema AAS | `persistence/db/persist_db.py` |
| 5 — Functional | API REST (estado atual) | `web/backend/robot_api/api.py` |
| 6 — Business | Dashboard React | `web/frontend/src/pages/ProductionHub/AAS_ScaraMonitoringHub.tsx` |

---

## A.1 Camada 2 — Integration

Mapeamento configurável entre os elementos do submodelo AAS e os `NodeId` do servidor OPC UA do controlador.

**Listagem A.1 — Extrato do mapeamento semântico (`config_opcua.json`).**

```json
{
  "OperationalData": {
    "JointPosition1": "ns=1;s=Robot:Controller:System:RobotPosition:Joint Position",
    "JointPosition2": "ns=1;s=Robot:Controller:System:RobotPosition:Joint Position",
    "JointPosition3": "ns=1;s=Robot:Controller:System:RobotPosition:Joint Position",
    "JointPosition4": "ns=1;s=Robot:Controller:System:RobotPosition:Joint Position",
    "WorkingMode": "ns=1;s=Robot:Controller:System:WorkingMode:Working Mode",
    "RobotStatus": "ns=1;s=Robot:Controller:System:RobotStatus:Robot Status"
  },
  "_client": {
    "mode": "subscription",
    "publishing_interval_ms": 200,
    "write_interval_s": 0.5
  }
}
```

---

## A.2 Camada 3 — Communication

Aquisição via *subscription* OPC UA: a subscription é criada, os nós são registrados como *MonitoredItems* e uma tarefa de escrita persiste os dados periodicamente.

**Listagem A.2 — Configuração da subscription OPC UA (`client_asyncua.py`).**

```python
async def run_subscription(client: Client, config: Dict[str, Any]) -> None:
    """Monitora nós OPC UA e recebe dados por push."""
    client_cfg = config.get("_client") or {}
    publishing_interval_ms = float(client_cfg.get("publishing_interval_ms", 200))
    write_interval_s = float(client_cfg.get("write_interval_s", 0.5))

    # 1. Poll inicial popula o data_store (valores iniciais + manuais)
    data_store = await map_opcua_to_submodels(client, config)

    # 2. Extrai o mapa NodeId -> caminhos e cria a subscription
    node_map = _extract_nodeid_map(config)
    handler = DataChangeHandler(node_map, data_store)
    subscription = await client.create_subscription(
        period=publishing_interval_ms, handler=handler,
    )

    # 3. Registra os MonitoredItems e dispara a tarefa de escrita
    nodes = [client.get_node(nid) for nid in node_map]
    await subscription.subscribe_data_change(nodes)
    writer = asyncio.ensure_future(_writer_task(handler, config, write_interval_s))
```

---

## A.3 Camada 4 — Information

Persistência transacional do *snapshot* AAS em três representações (JSON completo, normalizada e série temporal).

**Listagem A.3 — Persistência dos submodelos (`persist_db.py`).**

```python
def save_all_submodels(db_path: str, all_data: Dict[str, Any]) -> None:
    """Salva o snapshot em três formatos dentro de uma transação atômica."""
    init_db(db_path)
    created_at = _now_iso()
    with sqlite3.connect(db_path) as con:
        con.execute("BEGIN")
        try:
            for submodel_name, submodel_value in all_data.items():
                # (a) JSON completo do submodelo
                con.execute(
                    "INSERT INTO submodel_snapshots_json(submodel_name, data, created_at) "
                    "VALUES (?,?,?)",
                    (submodel_name, json.dumps(submodel_value, ensure_ascii=False), created_at))

                # (b) Linhas normalizadas idShort/valor
                kv_rows = []
                for path, val in _walk_leafs((), submodel_value):
                    idshort = f"{submodel_name}.{path}" if path else submodel_name
                    vt, vn, vb = _split_value(val)
                    kv_rows.append((submodel_name, idshort, vt, vn, vb, created_at))
                con.executemany(
                    "INSERT INTO submodel_snapshots(submodel_name, idshort, "
                    "value_text, value_num, value_bool, created_at) VALUES (?,?,?,?,?,?)",
                    kv_rows)

                # (c) Pontos numéricos para séries temporais
                rows = list(_walk_numeric((submodel_name,), submodel_value))
                con.executemany(
                    "INSERT INTO timeseries(submodel_name, element_path, value, created_at) "
                    "VALUES (?,?,?,?)",
                    [(submodel_name, path, val, created_at) for path, val in rows])
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
```

---

## A.4 Camada 5 — Functional

*Endpoint* REST que combina o último registro do banco com o *snapshot* em tempo real de `latest_data.json`.

**Listagem A.4 — Endpoint de estado atual (`api.py`).**

```python
@api.get("/state/latest", response_model=schemas.RobotStateRead)
def read_latest_state(db: Session = Depends(get_db)):
    # 1. Base estrutural do banco
    latest = crud.get_latest_state(db)

    # 2. Sobrescreve com o snapshot em tempo real
    data_path = next((p for p in _CANDIDATE_PATHS if p.exists()), None)
    if data_path:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        op_data = data.get("OperationalData", {})
        joint_pos = op_data.get("JointPosition1", [])

        if latest and isinstance(joint_pos, list) and len(joint_pos) >= 4:
            latest.joint1_deg = joint_pos[0]
            latest.joint2_deg = joint_pos[1]
            # J3: encoder do parafuso de esferas (graus) → curso linear (mm)
            j3_angle = max(0.0, min(180.0, float(joint_pos[2])))
            latest.joint3_mm = -(j3_angle / 180.0) * 200.0
            latest.joint4_deg = joint_pos[3]
    return latest
```

---

## A.5 Camada 6 — Business

*Dashboard* que consome a API em paralelo e atualiza os indicadores periodicamente (*polling* de 500 ms).

**Listagem A.5 — Atualização periódica do dashboard (`AAS_ScaraMonitoringHub.tsx`).**

```typescript
const REFRESH_MS = 500;

const fetchData = useCallback(async () => {
  const [latestState, historyState, summaryMetrics, connCount] = await Promise.all([
    getLatestState(),
    getHistory(64),
    getSummaryMetrics(),
    getConnectionCount(),
  ]);
  setLatest(latestState);
  setHistory(historyState);
  setSummary(summaryMetrics);
  setConnectionCount(connCount.count);
}, []);

useEffect(() => {
  fetchData();
  const id = setInterval(fetchData, REFRESH_MS);   // atualização periódica
  return () => clearInterval(id);
}, [fetchData]);
```
