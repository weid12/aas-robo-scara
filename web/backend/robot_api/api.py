# ------------------------------------------------------------------------------------------------------------------
#   API do Robô SCARA (FastAPI).
#   Define os endpoints para consulta de estado, histórico e métricas do robô.
# ------------------------------------------------------------------------------------------------------------------

"""
API para o hub de dados do robô SCARA.
"""

from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Ajuste de import para o novo local
from . import crud, models, schemas
from .database import engine, get_db
from . import seed_data

models.Base.metadata.create_all(bind=engine)

# Popula o banco de dados se estiver vazio - [DESABILITADO PARA USAR OPC UA COMO FONTE ÚNICA]
# with next(get_db()) as db:
#     if crud.get_latest_state(db) is None:
#         seed_data.seed()

# A variável 'app' agora é 'api' para evitar conflito
api = FastAPI(title="SCARA Hub API", version="1.0.0")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


import json
from pathlib import Path

# Caminhos candidatos para latest_data.json (em ordem de prioridade).
# Suporta o caminho novo (após reorganização) e o antigo como fallback.
REPO_ROOT = Path(__file__).resolve().parents[3]
_CANDIDATE_PATHS = [
    REPO_ROOT / "acquisition" / "client" / "latest_data.json",   # caminho atual
    REPO_ROOT / "opcua_client" / "latest_data.json",              # caminho antigo (fallback)
]


@api.get("/state/latest", response_model=schemas.RobotStateRead)
def read_latest_state(db: Session = Depends(get_db)):
    # 1. Tenta buscar do banco como base (para ter ID e estrutura completa)
    latest = crud.get_latest_state(db)

    # 2. Sobrescreve com dados em tempo real do latest_data.json.
    # Reavalia o caminho a cada chamada para detectar quando o arquivo for criado.
    data_path = next((p for p in _CANDIDATE_PATHS if p.exists()), None)
    if data_path:
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            op_data = data.get("OperationalData", {})
            # JointPosition1 é array de 4 floats em graus: [J1, J2, J3, J4]
            joint_pos = op_data.get("JointPosition1", [])

            if latest and isinstance(joint_pos, list) and len(joint_pos) >= 4:
                latest.joint1_deg = joint_pos[0]
                latest.joint2_deg = joint_pos[1]
                # J3 vem em graus do encoder do parafuso de esferas.
                # O ScaraRobot.jsx espera um valor negativo em mm (faixa: -200 a 0).
                # Mapeamento: 0° → 0mm (topo), 180° → -200mm (fundo).
                j3_angle = max(0.0, min(180.0, float(joint_pos[2])))
                latest.joint3_mm = -(j3_angle / 180.0) * 200.0
                latest.joint4_deg = joint_pos[3]

            if latest:
                latest.mode   = op_data.get("WorkingMode", latest.mode)
                latest.status = op_data.get("RobotStatus", latest.status)
                
                # Se tiver um tick vivo de horário, atualiza o timestamp em memória para a tela não congelar
                diag = data.get("RuntimeDiagnostics", {})
                current_time_str = diag.get("CurrentTime")
                if current_time_str:
                    from datetime import datetime
                    try:
                        latest.timestamp = datetime.fromisoformat(current_time_str)
                    except:
                        pass

                # Calcula o Uptime (tempo desde última conexão OPC UA do cliente)
                from datetime import datetime
                import datetime as dt
                try:
                    # Busca timestamp da última conexão OPC UA no banco
                    import sqlite3 as _sq
                    _conn_db = Path(__file__).resolve().parents[0] / "aas_robot_scara.db"
                    uptime_seconds = 0
                    if _conn_db.exists():
                        with _sq.connect(str(_conn_db)) as _conn:
                            row = _conn.execute(
                                "SELECT connected_at FROM opcua_connections ORDER BY id DESC LIMIT 1"
                            ).fetchone()
                            if row and row[0]:
                                last_conn = datetime.fromisoformat(row[0])
                                now_utc = datetime.now(dt.timezone.utc)
                                # Garante que ambos são aware
                                if last_conn.tzinfo is None:
                                    last_conn = last_conn.replace(tzinfo=dt.timezone.utc)
                                uptime_seconds = (now_utc - last_conn).total_seconds()
                                if uptime_seconds < 0:
                                    uptime_seconds = 0

                    setattr(latest, "uptime_s", uptime_seconds)
                except Exception as e:
                    print("Error computing uptime:", e)

                # Temperatura real por eixo (motorProbe1_temp .. motorProbe4_temp)
                temp_data = data.get("TemperatureData", {})
                latest.motorProbe1_temp = temp_data.get("motorProbe1_temp")
                latest.motorProbe2_temp = temp_data.get("motorProbe2_temp")
                latest.motorProbe3_temp = temp_data.get("motorProbe3_temp")
                latest.motorProbe4_temp = temp_data.get("motorProbe4_temp")
                print("DEBUG motorProbe values:", latest.motorProbe1_temp, latest.motorProbe2_temp, latest.motorProbe3_temp, latest.motorProbe4_temp)
                # IWtemperature → temperatura global exibida nos Eventos Recentes
                latest.temperature_c = temp_data.get("IWtemperature", latest.temperature_c)
        except Exception as e:
            print(f"Erro ao ler {data_path}: {e}")
            # Falha silenciosa — retorna o que tem no banco

    if not latest:
        raise HTTPException(
            status_code=404,
            detail="Nenhum registro encontrado e latest_data.json não disponível"
        )

    return latest


@api.get(
    "/state/history", response_model=List[schemas.RobotStateRead]
)
def read_history(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return crud.get_history(db, limit)


@api.get("/metrics/summary", response_model=schemas.RobotSummary)
def read_summary(db: Session = Depends(get_db)):
    return crud.get_summary_metrics(db)


import sqlite3 as _sqlite3

@api.get("/connections/count")
def get_connection_count():
    """Returns the total number of times the OPC UA client has connected to the robot."""
    db_path = Path(__file__).resolve().parents[0] / "aas_robot_scara.db"
    try:
        if not db_path.exists():
            return {"count": 0}
        with _sqlite3.connect(str(db_path)) as conn:
            # Table may not exist yet if client has never run
            conn.execute('''
                CREATE TABLE IF NOT EXISTS opcua_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    connected_at TEXT NOT NULL
                )
            ''')
            row = conn.execute("SELECT COUNT(*) FROM opcua_connections").fetchone()
            return {"count": row[0] if row else 0}
    except Exception as e:
        return {"count": 0, "error": str(e)}
