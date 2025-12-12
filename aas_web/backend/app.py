# ------------------------------------------------------------------------------------------------------------------
#   Ponto de entrada principal da aplicação Backend.
#   Integra rotas Flask (legado/compatibilidade) e FastAPI (novo padrão) em um servidor ASGI único.
#   Gerencia configurações de CORS, inicialização de banco de dados e rotas de API.
# ------------------------------------------------------------------------------------------------------------------

from flask import Flask, jsonify
from flask_cors import CORS
from config import CORS_ORIGINS, PORT
from login import login_bp
from data_routes import data_bp

# --- Imports para integração ASGI/WSGI ---
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware

# --- Import da API do Robô ---
from robot_api.api import api as robot_api_app

# --- Import da API de Usuários ---
from user_management.api import api as user_api_app

# 1. Cria a aplicação Flask como antes
flask_app = Flask(__name__)

# Configura o CORS para o Flask
if CORS_ORIGINS:
    CORS(flask_app, supports_credentials=True, origins=CORS_ORIGINS)
else:
    CORS(flask_app)

# Registra os Blueprints do Flask (removido hr_bp)
flask_app.register_blueprint(login_bp)
flask_app.register_blueprint(data_bp)

# Healthcheck do Flask
@flask_app.route('/')
def health():
    return jsonify({"status": "ok"})

@flask_app.route('/api/health')
def api_health():
    return jsonify({"ok": True})

# 2. Cria a aplicação FastAPI principal que será o ponto de entrada ASGI
app = FastAPI(title="Servidor Principal Integrado")

# 3. Monta a API do robô (FastAPI) no prefixo /api/robot
# As rotas da API ficarão em /api/robot/state/latest, /api/robot/state/history, etc.
app.mount("/api/robot", robot_api_app)

# 4. Monta a API de usuários (FastAPI) no prefixo /api/users
# As rotas ficarão em /api/users/register, /api/users/users, etc.
app.mount("/api/users", user_api_app)

# 5. Monta a aplicação Flask na raiz
# Todas as requisições que não correspondem a /robot ou /users serão encaminhadas para o Flask
app.mount("/", WSGIMiddleware(flask_app))


# O bloco de execução principal agora usa uvicorn para iniciar o servidor ASGI
if __name__ == '__main__':
    debug_mode = os.getenv("DEBUG", "False").lower() == "true"
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=debug_mode)
