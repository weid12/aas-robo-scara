# ------------------------------------------------------------------------------------------------------------------
#   Serviço de lógica de autenticação local.
#   Valida credenciais contra o banco de dados de usuários registrados.
# ------------------------------------------------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
import sys
import os

# Adiciona o diretório pai ao path para importar user_management
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from user_management.database import SessionLocal
from user_management import crud


@dataclass
class AuthResult:
    payload: Dict
    status_code: int


def authenticate_user(username: str, password: str, _base_url=None, logger=None) -> AuthResult:
    """
    Autentica usuário contra o banco de dados local.
    
    Args:
        username: Nome de usuário
        password: Senha em texto plano
        _base_url: Ignorado (mantido para compatibilidade)
        logger: Logger opcional
        
    Returns:
        AuthResult com payload e status code
    """
    if logger:
        logger.info(f"[AUTH] Tentando autenticar usuário: {username}")
    
    db = SessionLocal()
    try:
        # Busca usuário por username
        user = crud.get_user_by_username(db, username)
        
        if not user:
            if logger:
                logger.warning(f"[AUTH] Usuário não encontrado: {username}")
            return AuthResult(
                payload={"IsAuthenticated": False, "error": "Usuário ou senha inválidos"},
                status_code=401
            )
        
        if logger:
            logger.info(f"[AUTH] Usuário encontrado: {username}, verificando senha...")
        
        # Verifica se usuário está ativo
        if not user.is_active:
            if logger:
                logger.warning(f"[AUTH] Usuário inativo: {username}")
            return AuthResult(
                payload={"IsAuthenticated": False, "error": "Usuário inativo"},
                status_code=403
            )
        
        # Verifica senha
        password_valid = crud.verify_password(password, user.password_hash)
        if logger:
            logger.info(f"[AUTH] Verificação de senha para {username}: {'SUCESSO' if password_valid else 'FALHA'}")
        
        if not password_valid:
            if logger:
                logger.warning(f"[AUTH] Senha incorreta para usuário: {username}")
            return AuthResult(
                payload={"IsAuthenticated": False, "error": "Usuário ou senha inválidos"},
                status_code=401
            )
        
        # Autenticação bem-sucedida
        if logger:
            logger.info(f"[AUTH] ✓ Usuário autenticado com sucesso: {username}")
        
        return AuthResult(
            payload={
                "IsAuthenticated": True,
                "userId": user.username,
                "userName": user.full_name,
                "email": user.email,
                "id": user.id,
                "role": user.role,
                "profileType": user.profile_type,
                "department": user.department
            },
            status_code=200
        )
        
    except Exception as e:
        if logger:
            logger.error(f"[AUTH] ✗ Erro ao autenticar usuário {username}: {str(e)}", exc_info=True)
        return AuthResult(
            payload={"IsAuthenticated": False, "error": f"Erro interno: {str(e)}"},
            status_code=500
        )
    finally:
        db.close()
