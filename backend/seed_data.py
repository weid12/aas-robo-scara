"""
Instruções rápidas:
1. Popular o banco: python -m backend.seed_data
2. Iniciar API: uvicorn backend.main:app --reload
3. Iniciar frontend: cd aas_web_template/frontend && npm install && npm run dev
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from backend.database import SessionLocal, engine  # type: ignore
    from backend import models  # type: ignore
else:
    from .database import SessionLocal, engine
    from . import models


STATUSES = ["Running", "Idle", "Alarm"]
MODES = ["Auto", "Manual", "Teach"]


def build_entry(base_time: datetime, idx: int) -> models.RobotState:
    status = random.choices(STATUSES, weights=[0.7, 0.2, 0.1])[0]
    mode = random.choices(MODES, weights=[0.6, 0.3, 0.1])[0]
    cycle_time = random.uniform(2.5, 4.5)
    base_temp = 38 if status == "Running" else 32
    temp = base_temp + random.uniform(-2, 4)
    energy = 120.0 + idx * 0.15
    quality = random.uniform(0.93, 0.99)
    availability = random.uniform(0.9, 0.99)
    performance = random.uniform(0.85, 0.98)
    oee = quality * availability * performance

    return models.RobotState(
        timestamp=base_time,
        status=status,
        mode=mode,
        cycle_time_s=cycle_time,
        joint1_deg=random.uniform(-180, 180),
        joint2_deg=random.uniform(-120, 120),
        joint3_mm=random.uniform(0, 400),
        joint4_deg=random.uniform(-360, 360),
        temperature_c=temp,
        energy_kwh=energy,
        oee=oee,
        availability=availability,
        performance=performance,
        quality=quality,
    )


def seed():
    models.Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        session.query(models.RobotState).delete()
        base_time = datetime.now(timezone.utc) - timedelta(hours=6)
        records = []
        for idx in range(180):
            records.append(build_entry(base_time + timedelta(minutes=2 * idx), idx))
        session.add_all(records)
        session.commit()
        print(f"Seed finalizado com {len(records)} registros.")


if __name__ == "__main__":
    seed()
