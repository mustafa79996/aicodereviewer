import os
from pathlib import Path

# Base Paths - dynamically resolved to project root regardless of location or OS
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "reviews.db"
CACHE_DIR = BASE_DIR / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Application Settings
APP_TITLE = "AI Code Review & Bug Detection System"
APP_VERSION = "2.0.0"

# Server Host & Port: binds to 0.0.0.0 to support local, LAN, and Cloud deployments (Render/Railway/Docker)
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# Default AI Settings
DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER", "built-in")  # built-in, gemini, openai, ollama, groq, claude
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
