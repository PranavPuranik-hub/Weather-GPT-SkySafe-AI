"""
Application configuration management using pydantic-settings.
"""
from typing import Literal, Optional
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
    DATABASE_URL: Optional[str] = "sqlite:///./skysafe_test.db"
    MODE: Literal["live", "fixtures"] = "fixtures"
    
    # LLM Provider Configuration
    LLM_PROVIDER: Literal["ollama", "gemini", "groq", "null"] = "null"
    OLLAMA_URL: str = "http://localhost:11434"
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    
    # Demo Setup Defaults
    DEMO_DISTRICT: str = "Cuttack"
    
    # Optional External Integrations
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    SARVAM_API_KEY: Optional[str] = None

settings = Settings()
