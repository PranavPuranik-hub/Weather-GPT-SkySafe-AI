"""
API router package initialization.
"""
from app.api.admin import router as admin_router
from app.api.alerts import router as alerts_router
from app.api.health import router as health_router
from app.api.compose import compose_router
from app.api.voice import voice_router, languages_router
from app.api.chat import chat_router

__all__ = ["admin_router", "alerts_router", "health_router", "compose_router", "voice_router", "languages_router", "chat_router"]
