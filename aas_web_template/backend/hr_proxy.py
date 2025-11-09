from flask import Blueprint, request, jsonify
import requests
from requests import Timeout
from requests.exceptions import ConnectionError as RequestsConnectionError
from config import AUTH_API_BASE

hr_bp = Blueprint("hr_bp", __name__)


def _auth_base_error():
    if not AUTH_API_BASE:
        return (
            "AUTH_API_BASE nao configurado. "
            "Defina a URL completa no arquivo .env (ex: http://servidor:porta)"
        )
    if not AUTH_API_BASE.startswith(("http://", "https://")):
        return (
            "AUTH_API_BASE deve incluir o esquema http:// ou https://. "
            f"Valor atual: {AUTH_API_BASE}"
        )
    return None


@hr_bp.get("/api/hr/employee")
def hr_employee_get():
    """
    Proxy para HR: GET /api/hr/employee?userName=john.guedes
    Encaminha para {AUTH_API_BASE}/api/hr/employee/get?parameters.userName=<userName>
    """
    try:
        user_name = (request.args.get("userName") or "").strip()
        if not user_name:
            return jsonify({"error": "Parametro userName e obrigatorio"}), 400

        base_error = _auth_base_error()
        if base_error:
            return jsonify({"error": base_error}), 500

        url = f"{AUTH_API_BASE}/api/hr/employee/get"
        response = requests.get(
            url,
            params={"parameters.userName": user_name},
            headers={"Accept": "application/json"},
            timeout=6,
        )

        try:
            data = response.json()
        except Exception:
            return jsonify({"error": "Resposta invalida da HR API"}), 502

        return jsonify(data), response.status_code
    except Timeout:
        return jsonify({"error": "Timeout na HR API"}), 504
    except RequestsConnectionError:
        return jsonify(
            {
                "error": (
                    "Nao foi possivel conectar ao AUTH_API_BASE. "
                    f"Verifique se a URL {AUTH_API_BASE} esta acessivel."
                )
            }
        ), 502
    except Exception as ex:
        return jsonify({"error": f"Falha inesperada: {type(ex).__name__}"}), 500
