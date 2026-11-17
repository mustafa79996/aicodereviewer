import os
from pathlib import Path

# Base Paths strictly within D: drive
BASE_DIR = Path("D:/ai-code-reviewer")
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "reviews.db"
CACHE_DIR = BASE_DIR / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Application Settings
APP_TITLE = "AI Code Review & Bug Detection System"
APP_VERSION = "2.0.0"
HOST = "127.0.0.1"
PORT = 8000

# Default AI Settings
DEFAULT_AI_PROVIDER = "built-in"  # built-in, gemini, openai, ollama, groq, claude
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
