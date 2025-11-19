"""
Instruções rápidas:
1. Popular o banco: python -m backend.seed_data
2. Iniciar API: uvicorn backend.main:app --reload
3. Iniciar frontend: cd aas_web_template/frontend && npm install && npm run dev
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class RobotStateBase(BaseModel):
    timestamp: datetime
    status: str
    mode: str
    cycle_time_s: Optional[float] = None
    joint1_deg: Optional[float] = None
    joint2_deg: Optional[float] = None
    joint3_mm: Optional[float] = None
    joint4_deg: Optional[float] = None
    temperature_c: Optional[float] = None
    energy_kwh: Optional[float] = None
    oee: Optional[float] = None
    availability: Optional[float] = None
    performance: Optional[float] = None
    quality: Optional[float] = None


class RobotStateRead(RobotStateBase):
    id: int

    class Config:
        orm_mode = True


class RobotSummary(BaseModel):
    date: date
    operation_time_s: float
    downtime_s: float
    cycles: int
    energy_kwh: float
    oee_avg: Optional[float] = None
    availability_avg: Optional[float] = None
    performance_avg: Optional[float] = None
    quality_avg: Optional[float] = None
