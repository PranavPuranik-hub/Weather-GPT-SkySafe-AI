"""
Pydantic Models for Voice API requests and responses.
"""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class VoiceRequest(BaseModel):
    alert_id: str = Field(..., description="Unique CAP alert identifier")
    persona: str = Field(default="general", description="Target recipient persona")
    lang: str = Field(default="en", description="ISO 639-1 language code")


class VoiceResponse(BaseModel):
    alert_id: str
    persona: str
    lang: str
    audio_url: Optional[str] = None
    transcript: str
    sms_text: str
    sms_metadata: Dict[str, Any]
    claim_ledger: Dict[str, Any]
    duration_sec: float
    file_size_bytes: int
    audio_available: bool = True
    browser_speech: bool = False
    browser_script: str
    path_used: str
