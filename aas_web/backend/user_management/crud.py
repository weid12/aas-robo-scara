# ------------------------------------------------------------------------------------------------------------------
#   Camada de acesso a dados (CRUD) para gerenciamento de usuários.
#   Contém funções para criar, ler e gerenciar usuários.
# ------------------------------------------------------------------------------------------------------------------

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import bcrypt
from typing import Optional

from . import models, schemas


def hash_password(password: str) -> str:
    """
    Gera hash bcrypt da senha.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha corresponde ao hash.
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Busca usuário por username."""
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Busca usuário por email."""
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    """Busca usuário por ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()


def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[models.User]:
    """Lista todos os usuários."""
    return db.query(models.User).offset(skip).limit(limit).all()


def count_users(db: Session) -> int:
    """Conta total de usuários."""
    return db.query(models.User).count()


def create_user(db: Session, user_data: schemas.UserCreate) -> models.User:
    """
    Cria novo usuário.
    """
    # Verifica duplicatas
    if get_user_by_username(db, user_data.username):
        raise ValueError("Username já está em uso")
    
    if get_user_by_email(db, user_data.email):
        raise ValueError("Email já está em uso")
    
    # Cria usuário com senha hasheada
    db_user = models.User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        department=user_data.department,
        role=user_data.role.value,
        profile_type=user_data.profile_type.value,
        password_hash=hash_password(user_data.password)
    )
    
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise ValueError("Erro ao criar usuário: dados duplicados")


def update_user(db: Session, user_id: int, user_data: schemas.UserUpdate) -> Optional[models.User]:
    """
    Atualiza dados de um usuário.
    """
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    update_data = user_data.dict(exclude_unset=True)
    
    # Se estiver atualizando senha, faz o hash
    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))
        
    # Se estiver atualizando role ou profile_type, converte enum para valor
    if "role" in update_data and hasattr(update_data["role"], "value"):
        update_data["role"] = update_data["role"].value
        
    if "profile_type" in update_data and hasattr(update_data["profile_type"], "value"):
        update_data["profile_type"] = update_data["profile_type"].value
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
        
    try:
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise ValueError("Erro ao atualizar usuário: dados inválidos")
