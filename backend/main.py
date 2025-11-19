"""
Instruções rápidas:
1. Popular o banco: python -m backend.seed_data
2. Iniciar API: uvicorn backend.main:app --reload
3. Iniciar frontend: cd aas_web_template/frontend && npm install && npm run dev
"""

from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SCARA Hub API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


@app.get("/api/robot/state/latest", response_model=schemas.RobotStateRead)
def read_latest_state(db: Session = Depends(get_db)):
    latest = crud.get_latest_state(db)
    if not latest:
        raise HTTPException(status_code=404, detail="Nenhum registro encontrado")
    return latest


@app.get(
    "/api/robot/state/history", response_model=List[schemas.RobotStateRead]
)
def read_history(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return crud.get_history(db, limit)


@app.get("/api/robot/metrics/summary", response_model=schemas.RobotSummary)
def read_summary(db: Session = Depends(get_db)):
    return crud.get_summary_metrics(db)
