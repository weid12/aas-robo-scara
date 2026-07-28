# ------------------------------------------------------------------------------------------------------------------
#   Rotas de autenticação da API.
#   Define os endpoints para login e validação de credenciais, delegando a lógica para o serviço de autenticação.
# ------------------------------------------------------------------------------------------------------------------

from flask import Blueprint, request, jsonify, current_app

from config import AUTH_API_BASE
from .service import authenticate_user

login_bp = Blueprint("login", __name__, url_prefix="/api/auth")


@login_bp.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    # Aceita tanto 'userId' quanto 'username' para compatibilidade
    username = (body.get("userId") or body.get("username") or "").strip()
    password = (body.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "username/userId e password são obrigatórios"}), 400

    result = authenticate_user(username, password, AUTH_API_BASE, current_app.logger)
    return jsonify(result.payload), result.status_code
