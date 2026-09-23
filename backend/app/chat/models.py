"""
Data models for the Citizen Chat Conversational Agent.
Input validation enforced via Pydantic Field(max_length=...) constraints.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.security import detect_prompt_injection, sanitize_user_input


class OnboardingRequest(BaseModel):
    user_id: Optional[str] = None
    phone: Optional[str] = Field(default=None, max_length=20, description="Citizen phone number (hashed immediately, never stored raw)")
    language: str = Field(default="en", max_length=10, description="Preferred ISO 639-1 language code")
    persona: str = Field(default="general", max_length=50, description="Persona type: general, farmer, fisherman, elderly_alone, pregnant_infants")
    location: str = Field(default="Cuttack", max_length=100, description="Home village, town or district")
    consent_alerts: bool = Field(default=True, description="Explicit consent for SMS/Voice emergency alerts")


class OnboardingResponse(BaseModel):
    user_id: str
    phone_hash: Optional[str]
    language: str
    persona: str
    location: Dict[str, Any]
    consent_alerts: bool
    welcome_message: str
    quick_replies: List[str]


class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, max_length=64)
    user_id: Optional[str] = Field(default=None, max_length=64)
    message: str = Field(..., max_length=500, description="Citizen message text or speech transcript")
    location: Optional[str] = Field(default=None, max_length=100, description="Optional location override or shared pin coords")
    lat: Optional[float] = None
    lon: Optional[float] = None
    lang: Optional[str] = Field(default=None, max_length=10)
    persona: Optional[str] = Field(default=None, max_length=50)

    @field_validator("message")
    @classmethod
    def no_prompt_injection(cls, v: str) -> str:
        """Reject messages that attempt to override system instructions."""
        if detect_prompt_injection(v):
            raise ValueError("Message contains disallowed content.")
        return sanitize_user_input(v, max_length=500)


class ChatResponse(BaseModel):
    session_id: str
    message: str
    voice_script: Optional[str] = None
    audio_url: Optional[str] = None
    quick_replies: List[str] = Field(default_factory=list)
    claim_ledger: Optional[Dict[str, Any]] = None
    intent: str
    tools_called: List[str] = Field(default_factory=list)
    location: Optional[Dict[str, Any]] = None
    clarification_needed: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class IncidentReportRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, max_length=64)
    location: str = Field(..., max_length=100)
    incident_type: str = Field(..., max_length=50)  # waterlogging, tree_fall, road_blocked, power_outage, other
    description: str = Field(..., max_length=1000)
    phone: Optional[str] = Field(default=None, max_length=20)

    @field_validator("description")
    @classmethod
    def no_injection_in_description(cls, v: str) -> str:
        if detect_prompt_injection(v):
            raise ValueError("Description contains disallowed content.")
        return sanitize_user_input(v, max_length=1000)

