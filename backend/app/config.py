import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
# MySQL for recommend module (e.g. mysql+pymysql://user:password@localhost:3306/auramart)
MYSQL_URI = os.getenv("MYSQL_URI", "")
