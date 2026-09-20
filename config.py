import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_FILE)


class Config:
    # Ollama
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "600"))

    # Modèles autorisés
    MODELS = {
        "qwen3:8b",
        "qwen3:14b",
    }

    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen3:14b")

    # Génération
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

    # Limites
    MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "10000"))
    MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "50"))

    # Authentification
    AUTH_USERNAME = os.getenv("AUTH_USERNAME", "")
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    PASSWORD_HASH = os.getenv("PASSWORD_HASH", "")

    # Session
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12  # 12 heures


# Vérifications de sécurité au démarrage
if not Config.SECRET_KEY:
    raise RuntimeError("SECRET_KEY manquante dans .env")

if not Config.AUTH_USERNAME:
    raise RuntimeError("AUTH_USERNAME manquante dans .env")

if not Config.PASSWORD_HASH:
    raise RuntimeError("PASSWORD_HASH manquante dans .env")