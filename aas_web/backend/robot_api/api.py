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

# Popula o banco de dados se estiver vazio
with next(get_db()) as db:
    if crud.get_latest_state(db) is None:
        seed_data.seed()

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


@api.get("/state/latest", response_model=schemas.RobotStateRead)
def read_latest_state(db: Session = Depends(get_db)):
    latest = crud.get_latest_state(db)
    if not latest:
        raise HTTPException(status_code=404, detail="Nenhum registro encontrado")
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
