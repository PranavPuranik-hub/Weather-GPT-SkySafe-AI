from skysafe.core.config import settings
from skysafe.core.db import check_db_health

def test_core_settings():
    assert settings.PROJECT_NAME == "SkySafe AI"
    assert settings.MODE in ["live", "fixtures"]
    assert settings.LLM_PROVIDER in ["ollama", "gemini", "groq", "null"]

def test_core_db_health():
    # Verify DB health check executes without crashing
    result = check_db_health()
    assert isinstance(result, bool)

def test_postgres_driver_import():
    from sqlalchemy import create_engine
    # Test that create_engine with postgresql:// does not raise ModuleNotFoundError for psycopg2
    postgres_engine = create_engine("postgresql://skysafe:skysafe@localhost:5432/skysafe")
    assert postgres_engine.driver == "psycopg2"
