import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Set to "1" or "true" to use built-in chat only (no OpenAI); useful if API key is invalid
USE_BUILTIN_CHAT = os.getenv("USE_BUILTIN_CHAT", "").lower() in ("1", "true", "yes")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# Razorpay (get keys from https://dashboard.razorpay.com/app/keys)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
