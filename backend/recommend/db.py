"""
SQLAlchemy engine and session for MySQL.
Uses MYSQL_URI from env; optional fallback to SQLite for local dev.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Load env from backend/.env
try:
    from dotenv import load_dotenv
    _backend_dir = Path(__file__).resolve().parent.parent
    load_dotenv(_backend_dir / ".env")
except Exception:
    pass

MYSQL_URI = os.getenv("MYSQL_URI", "")
# Fallback SQLite for dev when MySQL not configured
SQLITE_FALLBACK = "sqlite:///" + str(Path(__file__).resolve().parent.parent / "data" / "recommend.db")

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        use_mysql = MYSQL_URI and MYSQL_URI.strip()
        if use_mysql:
            try:
                import pymysql  # noqa: F401
            except ImportError:
                use_mysql = False
        if use_mysql:
            _engine = create_engine(
                MYSQL_URI,
                pool_pre_ping=True,
                echo=False,
            )
        else:
            Path(SQLITE_FALLBACK.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
            _engine = create_engine(
                SQLITE_FALLBACK,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
    return _engine


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal()


def init_db():
    """Create all tables from ORM models."""
    from recommend import models_db  # noqa: F401
    models_db.Base.metadata.create_all(bind=get_engine())
