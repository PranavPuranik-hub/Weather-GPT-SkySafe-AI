"""
Data models for the Citizen Chat Conversational Agent.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    user_id: Optional[str] = None
    phone: Optional[str] = Field(default=None, description="Citizen phone number (hashed immediately)")
    language: str = Field(default="en", description="Preferred ISO 639-1 language code")
    persona: str = Field(default="general", description="Persona type: general, farmer, fisherman, elderly_alone, pregnant_infants")
    location: str = Field(default="Cuttack", description="Home village, town or district")
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
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    message: str = Field(..., description="Citizen message text or speech transcript")
    location: Optional[str] = Field(default=None, description="Optional location override or shared pin coords")
    lat: Optional[float] = None
    lon: Optional[float] = None
    lang: Optional[str] = None
    persona: Optional[str] = None


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
    session_id: Optional[str] = None
    location: str
    incident_type: str  # waterlogging, tree_fall, road_blocked, power_outage, other
    description: str
    phone: Optional[str] = None
