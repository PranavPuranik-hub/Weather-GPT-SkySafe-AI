"""
Database connection and session factory with SQLite fallback.
"""
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from skysafe.core.config import settings

logger = logging.getLogger("skysafe.db")

class Base(DeclarativeBase):
    """Base class for ORM models."""

db_url = settings.DATABASE_URL or "sqlite:///./skysafe_test.db"

# Enable sqlite thread check bypass for test simplicity if sqlite
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(db_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_db_health() -> bool:
    """
    Check active database connection status.
    Returns True if healthy, False otherwise.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning(f"Database healthcheck failed: {exc}")
        return False
