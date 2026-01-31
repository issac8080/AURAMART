import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Set to "1" or "true" to use built-in chat only (no OpenAI); useful if API key is invalid
USE_BUILTIN_CHAT = os.getenv("USE_BUILTIN_CHAT", "").lower() in ("1", "true", "yes")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
# MySQL for recommend module (e.g. mysql+pymysql://user:password@localhost:3306/auramart)
MYSQL_URI = os.getenv("MYSQL_URI", "")
# Fast mode: set to "1" to skip RAG/Chroma and use only data_store (instant). Default "0" = use RAG.
USE_FAST_RECOMMEND = os.getenv("USE_FAST_RECOMMEND", "0").strip().lower() in ("1", "true", "yes")
USE_FAST_CHAT = os.getenv("USE_FAST_CHAT", "0").strip().lower() in ("1", "true", "yes")
