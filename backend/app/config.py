import os

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
CORS_ORIGINS = [o for o in os.getenv("CORS_ORIGINS", "*").split(",") if o]
APP_VERSION = "0.1.0"
DEFAULT_TIMEZONE = "America/Los_Angeles"  # UW; used until the student's timezone is known
FAST_MODEL = os.getenv("FAST_MODEL", "claude-haiku-5-5")
