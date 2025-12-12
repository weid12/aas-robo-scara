# ------------------------------------------------------------------------------------------------------------------
#   Schemas Pydantic para validação e serialização de dados de usuários.
#   Define os modelos de entrada e saída da API (DTOs).
# ------------------------------------------------------------------------------------------------------------------

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class UserRole(str, Enum):
    STAFF = "staff"
    MANAGER = "manager"
    OPERATOR = "operator"
    DIRECTOR = "director"


class ProfileType(str, Enum):
    ADMIN = "admin"
    USER = "user"


class UserCreate(BaseModel):
    """Schema para criação de usuário."""
    username: str = Field(..., min_length=3, max_length=50, description="Nome de usuário único")
    email: EmailStr = Field(..., description="Email válido e único")
    full_name: str = Field(..., min_length=3, max_length=100, description="Nome completo")
    department: Optional[str] = Field(None, description="Departamento do usuário")
    role: UserRole = Field(UserRole.STAFF, description="Cargo do usuário")
    profile_type: ProfileType = Field(ProfileType.USER, description="Tipo de perfil de acesso")
    password: str = Field(..., min_length=8, description="Senha com no mínimo 8 caracteres")


class UserUpdate(BaseModel):
    """Schema para atualização de usuário."""
    full_name: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    role: Optional[UserRole] = None
    profile_type: Optional[ProfileType] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None


class UserRead(BaseModel):
    """Schema para leitura de usuário (sem senha)."""
    id: int
    username: str
    email: str
    full_name: str
    department: Optional[str]
    role: str
    profile_type: str
    created_at: datetime
    is_active: bool

    class Config:
        orm_mode = True


class UserList(BaseModel):
    """Schema para listagem de usuários."""
    users: list[UserRead]
    total: int
