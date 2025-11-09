from flask import Blueprint, request, jsonify, current_app

from config import AUTH_API_BASE
from .service import authenticate_user

login_bp = Blueprint("login", __name__, url_prefix="/api/auth")


@login_bp.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    user_id = (body.get("userId") or "").strip()
    password = (body.get("password") or "").strip()

    if not user_id or not password:
        return jsonify({"error": "userId e password sao obrigatorios"}), 400

    result = authenticate_user(user_id, password, AUTH_API_BASE, current_app.logger)
    return jsonify(result.payload), result.status_code
