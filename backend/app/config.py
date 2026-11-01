import os
from dotenv import load_dotenv

load_dotenv()  # backend/.env থেকে পড়ে

def _list(name, default=""):
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODELS = _list("GEMINI_MODELS", "gemini-2.5-flash,gemini-2.5-flash-lite")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODELS = _list("OPENROUTER_MODELS")
DATABASE_URL = os.getenv("DATABASE_URL")

from pathlib import Path

UPLOAD_DIR = os.getenv("UPLOAD_DIR") or str(Path(__file__).resolve().parent.parent / "uploads")
MAX_UPLOAD_MB = float(os.getenv("MAX_UPLOAD_MB", "200"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))   # একসাথে কটা ফাইল প্রসেস হবে (Gemini free quota বাঁচাতে)
CORS_ORIGINS = _list("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")

EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
