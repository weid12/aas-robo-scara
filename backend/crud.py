"""
Instruções rápidas:
1. Popular o banco: python -m backend.seed_data
2. Iniciar API: uvicorn backend.main:app --reload
3. Iniciar frontend: cd aas_web_template/frontend && npm install && npm run dev
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from . import models, schemas


def get_latest_state(db: Session) -> Optional[models.RobotState]:
    return (
        db.query(models.RobotState)
        .order_by(models.RobotState.timestamp.desc())
        .limit(1)
        .one_or_none()
    )


def get_history(db: Session, limit: int) -> List[models.RobotState]:
    return (
        db.query(models.RobotState)
        .order_by(models.RobotState.timestamp.desc())
        .limit(limit)
        .all()
    )


def _normalize_timestamp(ts: datetime) -> datetime:
    if ts.tzinfo:
        return ts.astimezone(timezone.utc).replace(tzinfo=None)
    return ts


def _safe_average(values):
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def get_summary_metrics(db: Session) -> schemas.RobotSummary:
    now = datetime.now(timezone.utc)
    start_of_day = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    end_of_day = start_of_day + timedelta(days=1)

    rows = (
        db.query(models.RobotState)
        .filter(
            models.RobotState.timestamp >= start_of_day,
            models.RobotState.timestamp < end_of_day,
        )
        .order_by(models.RobotState.timestamp.asc())
        .all()
    )

    operation_seconds = 0.0
    downtime_seconds = 0.0
    energy_kwh = 0.0

    if rows:
        normalized = [_normalize_timestamp(r.timestamp) for r in rows]
        for idx, row in enumerate(rows):
            if idx + 1 < len(rows):
                delta = (normalized[idx + 1] - normalized[idx]).total_seconds()
            else:
                delta = 0.0
            delta = max(delta, 0.0)
            if row.status.lower() == "running":
                operation_seconds += delta
            else:
                downtime_seconds += delta

        first_energy = rows[0].energy_kwh or 0.0
        last_energy = rows[-1].energy_kwh or first_energy
        energy_kwh = max(last_energy - first_energy, 0.0)

    summary = schemas.RobotSummary(
        date=now.date(),
        operation_time_s=operation_seconds,
        downtime_s=downtime_seconds,
        cycles=len(rows),
        energy_kwh=energy_kwh,
        oee_avg=_safe_average([r.oee for r in rows]),
        availability_avg=_safe_average([r.availability for r in rows]),
        performance_avg=_safe_average([r.performance for r in rows]),
        quality_avg=_safe_average([r.quality for r in rows]),
    )
    return summary
