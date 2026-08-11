"""
E.V. Agent Web — Configuration
All settings are loaded from environment variables or .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ===== Project Paths =====
PROJECT_ROOT = Path(__file__).parent.resolve()
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DB_PATH = str(DATA_DIR / "chroma_db")
SQLITE_DB_PATH = str(DATA_DIR / "ev_memory.db")

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "chroma_db").mkdir(exist_ok=True)

# ===== LLM: OpenRouter =====
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001").strip()
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()

# ===== LLM: DeepSeek =====
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()

# ===== LLM: Fallback =====
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# ===== TTS =====
DEFAULT_TTS_ENGINE = os.getenv("DEFAULT_TTS_ENGINE", "edge")
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "vi-VN-HoaiMyNeural")
TTS_VOICE = os.getenv("TTS_VOICE", EDGE_TTS_VOICE)
TTS_RATE = os.getenv("TTS_RATE", "+0%")
TTS_PITCH = os.getenv("TTS_PITCH", "+0Hz")

# ===== Memory =====
MAX_SHORT_TERM_MESSAGES = int(os.getenv("MAX_SHORT_TERM_MESSAGES", "10"))
MEMORY_TOP_K = int(os.getenv("MEMORY_TOP_K", "3"))

# ===== Safety =====
ALLOWED_DIRECTORIES = os.getenv(
    "ALLOWED_DIRECTORIES",
    str(Path.home() / "Documents") + ";" + str(Path.home() / "Desktop")
).split(";")
DANGEROUS_COMMANDS = [
    "rm -rf", "format", "del /f /s", "shutdown", "restart",
    "rmdir /s", "reg delete", "bcdedit", "diskpart"
]
MAX_REACT_ITERATIONS = int(os.getenv("MAX_REACT_ITERATIONS", "3"))
TOOL_EXECUTION_TIMEOUT = int(os.getenv("TOOL_EXECUTION_TIMEOUT", "30"))

# ===== Web Server =====
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# ===== E.V. Persona =====
EV_NAME = "E.V."
EV_PERSONALITY = "cheerful"


def validate_config():
    """Validate that required configuration is set."""
    errors = []
    if not (OPENROUTER_API_KEY or GROQ_API_KEY or GEMINI_API_KEY or DEEPSEEK_API_KEY):
        errors.append("No API key set. Please set OPENROUTER_API_KEY or another LLM API key in .env file.")
    return errors
