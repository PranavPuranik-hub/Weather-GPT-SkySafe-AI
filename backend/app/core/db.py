"""
Database connection and session factory with SQLite fallback.
"""
import logging
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

logger = logging.getLogger("app.db")

class Base(DeclarativeBase):
    """Base class for ORM models."""

if settings.DATABASE_URL:
    db_url = settings.DATABASE_URL
else:
    # Anchor to project root so tests, CLI, and uvicorn share the exact same DB file
    root_db = Path(__file__).resolve().parents[3] / "app_test.db"
    db_url = f"sqlite:///{root_db.as_posix()}"

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
