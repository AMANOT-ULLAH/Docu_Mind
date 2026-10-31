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