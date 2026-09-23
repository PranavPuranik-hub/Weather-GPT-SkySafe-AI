"""
Citizen Chat package.
"""
from app.chat.engine import get_or_create_session, handle_chat_message, process_onboarding
from app.chat.geocoding import resolve_location
from app.chat.models import (
    ChatRequest,
    ChatResponse,
    IncidentReportRequest,
    OnboardingRequest,
    OnboardingResponse,
)
from app.chat.router import classify_intent

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "OnboardingRequest",
    "OnboardingResponse",
    "IncidentReportRequest",
    "handle_chat_message",
    "process_onboarding",
    "get_or_create_session",
    "classify_intent",
    "resolve_location",
]
