"""
Instruções rápidas:
1. Popular o banco: python -m backend.seed_data
2. Iniciar API: uvicorn backend.main:app --reload
3. Iniciar frontend: cd aas_web_template/frontend && npm install && npm run dev
"""

from sqlalchemy import Column, DateTime, Float, Integer, String

from .database import Base


class RobotState(Base):
    """Tabela principal com o estado histórico do robô SCARA."""

    __tablename__ = "robot_state"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(32), nullable=False)
    mode = Column(String(32), nullable=False)
    cycle_time_s = Column(Float, nullable=True)
    joint1_deg = Column(Float, nullable=True)
    joint2_deg = Column(Float, nullable=True)
    joint3_mm = Column(Float, nullable=True)
    joint4_deg = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
    energy_kwh = Column(Float, nullable=True)
    oee = Column(Float, nullable=True)
    availability = Column(Float, nullable=True)
    performance = Column(Float, nullable=True)
    quality = Column(Float, nullable=True)
