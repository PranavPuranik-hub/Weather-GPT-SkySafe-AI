"""
Application configuration management using pydantic-settings.
"""
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    SkySafe settings model enforcing environment variable types and defaults.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "SkySafe AI"
    VERSION: str = "0.1.0"

    # Environment & Database Configuration
    DATABASE_URL: str | None = "sqlite:///./app_test.db"
    MODE: Literal["live", "fixtures"] = "fixtures"

    # LLM Provider Configuration
    LLM_PROVIDER: Literal["ollama", "gemini", "groq", "null"] = "null"
    OLLAMA_URL: str = "http://localhost:11434"
    GEMINI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None

    # Demo Setup Defaults
    DEMO_DISTRICT: str = "Cuttack"

    # Ingest & Feed Configuration
    SACHET_RSS_URL: str = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"
    IMD_RSS_URL: str = "https://mausam.imd.gov.in/backend/assets/rss/imd_rss.xml"
    INGEST_POLL_INTERVAL_SECONDS: int = 60
    DATA_DIR: str = "data"

    # Optional External Integrations
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_PHONE_NUMBER: str | None = None
    SARVAM_API_KEY: str | None = None

settings = Settings()
