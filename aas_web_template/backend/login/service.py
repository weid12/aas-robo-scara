from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from urllib.parse import urlencode

import requests
from requests import Timeout
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    RequestException,
)


@dataclass
class AuthResult:
    payload: Dict
    status_code: int


def _normalize_base_url(base_url: str | None) -> Tuple[str | None, str | None]:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        return None, (
            "AUTH_API_BASE nao configurado. "
            "Defina a URL completa no arquivo .env (ex: http://servidor:porta)"
        )
    if not base.startswith(("http://", "https://")):
        return None, (
            "AUTH_API_BASE deve incluir o esquema http:// ou https://. "
            f"Valor atual: {base_url}"
        )
    return base, None


def _safe_json(response: requests.Response):
    try:
        return response.json()
    except ValueError:
        return None


def _normalize_text(text: str | None) -> Dict:
    raw = (text or "").strip()
    lower = raw.lower()
    if lower in ("true", "false"):
        return {"IsAuthenticated": lower == "true"}
    if raw:
        return {"raw": raw}
    return {}


def _finalize_response(response: requests.Response) -> Dict:
    data = _safe_json(response)
    if data is not None:
        return data
    return _normalize_text(response.text)


def authenticate_user(user_id: str, password: str, base_url: str, logger) -> AuthResult:
    """
    Tenta autenticar o usuario usando diferentes formatos de requisicao.
    Retorna AuthResult contendo payload (dict) e status HTTP a ser devolvido.
    """
    normalized_base, error = _normalize_base_url(base_url)
    if error:
        return AuthResult({"error": error}, 500)

    endpoint = f"{normalized_base}/api/ad/authenticate"
    credentials = {"userId": user_id, "password": password}
    headers = {"Accept": "application/json, text/plain, */*"}

    strategies = (
        (
            "POST JSON",
            {
                "method": "post",
                "url": endpoint,
                "json": credentials,
            },
        ),
        (
            "POST query",
            {
                "method": "post",
                "url": endpoint,
                "params": credentials,
            },
        ),
        (
            "GET query",
            {
                "method": "get",
                "url": endpoint,
                "params": credentials,
            },
        ),
    )

    last_response = None

    for label, request_kwargs in strategies:
        try:
            response = requests.request(
                timeout=8,
                headers=headers,
                **request_kwargs,
            )
            logger.info(
                "[auth:%s] status=%s url=%s",
                label,
                getattr(response, "status_code", "?"),
                request_kwargs.get("url"),
            )
        except Timeout:
            logger.warning("[auth:%s] timeout ao chamar %s", label, request_kwargs.get("url"))
            continue
        except RequestsConnectionError:
            return AuthResult(
                {
                    "error": (
                        "Nao foi possivel conectar ao AUTH_API_BASE. "
                        f"Verifique se a URL {normalized_base} esta acessivel."
                    )
                },
                502,
            )
        except RequestException as ex:
            logger.warning("[auth:%s] erro de requisicao: %s", label, ex)
            continue

        last_response = response

        if response.status_code < 400 or response.status_code in (401, 403):
            payload = _finalize_response(response)
            return AuthResult(payload, response.status_code)

    if last_response is not None:
        payload = _finalize_response(last_response)
        return AuthResult(payload, last_response.status_code)

    return AuthResult(
        {"error": "Nao foi possivel contatar a API de autenticacao"},
        502,
    )
