import os
from dotenv import load_dotenv

load_dotenv()

AUTH_API_BASE = os.getenv("AUTH_API_BASE", "").rstrip("/")
PORT = int(os.getenv("PORT", "5000"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
