# ------------------------------------------------------------------------------------------------------------------
#   Modelos de dados SQLAlchemy para gerenciamento de usuários.
#   Define a estrutura da tabela users.
# ------------------------------------------------------------------------------------------------------------------

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Enum
from datetime import datetime, timezone
import enum

from .database import Base


class UserRole(str, enum.Enum):
    STAFF = "staff"
    MANAGER = "manager"
    OPERATOR = "operator"
    DIRECTOR = "director"


class ProfileType(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class User(Base):
    """Tabela de usuários do sistema."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    department = Column(String(100), nullable=True)
    role = Column(String(50), nullable=False, default=UserRole.STAFF.value)
    profile_type = Column(String(50), nullable=False, default=ProfileType.USER.value)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True, nullable=False)
