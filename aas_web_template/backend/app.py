from flask import Flask, jsonify
from flask_cors import CORS
from config import CORS_ORIGINS, PORT
from login import login_bp
from hr_proxy import hr_bp

app = Flask(__name__)

# CORS dev
if CORS_ORIGINS:
    CORS(app, supports_credentials=True, origins=CORS_ORIGINS)
else:
    CORS(app)

# Blueprints
app.register_blueprint(login_bp)
app.register_blueprint(hr_bp)

# Healthcheck
@app.route('/')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/health')
def api_health():
    return jsonify({"ok": True})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=PORT, debug=True)
