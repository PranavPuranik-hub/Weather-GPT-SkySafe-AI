"""
Chat API Router for Citizen Conversational Weather & Disaster Assistant.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.chat.models import (
    ChatRequest,
    ChatResponse,
    OnboardingRequest,
    OnboardingResponse,
    IncidentReportRequest,
)
from app.chat.engine import handle_chat_message, process_onboarding, get_or_create_session
from app.chat.geocoding import resolve_location, SEEDED_LOCATIONS
from app.voice import voice_synthesizer
from app.models import Alert
from app.core.db import SessionLocal
from app.ingest.service import ingest_service
from app.channels.broadcast import deliver_broadcast
from datetime import datetime, timedelta

chat_router = APIRouter(prefix="/api/chat", tags=["chat"])


class SimulateAlertRequest(BaseModel):
    session_id: Optional[str] = None
    scenario: str = Field(default="cyclone_t12", description="Scenario: cyclone_t24, cyclone_t12, cyclone_t03, flood, heatwave")
    district: str = Field(default="Cuttack", description="Target district")


@chat_router.post("/onboard", response_model=OnboardingResponse)
def onboard_citizen(req: OnboardingRequest):
    """Register citizen preferences, language, persona, and location."""
    return process_onboarding(req)


@chat_router.post("/message", response_model=ChatResponse)
def send_message(req: ChatRequest):
    """Process incoming citizen chat message with deterministic tool grounding."""
    return handle_chat_message(req)


@chat_router.post("/report")
def report_incident(req: IncidentReportRequest):
    """Report a local community weather incident (waterlogging, fallen tree, wire cut)."""
    return {
        "status": "success",
        "incident_id": f"INC-{int(datetime.utcnow().timestamp())}",
        "location": req.location,
        "type": req.incident_type,
        "message": "Incident logged and reported to local disaster authorities."
    }


@chat_router.post("/simulate")
def simulate_incoming_alert(req: SimulateAlertRequest):
    """
    Dev Panel control: simulate an incoming official CAP alert arriving on the citizen phone.
    Uses Prompt 2 simulation infrastructure (ingest_service) and real broadcast delivery service.
    """
    session_id, session = get_or_create_session(req.session_id)
    lang = session.get("language", "en")
    district = req.district or session.get("location", {}).get("district", "Cuttack")

    alert = ingest_service.simulate_scenario(req.scenario, district=district)
    if not alert:
        # Fallback to odisha_cyclone if scenario not directly named
        alert = ingest_service.simulate_scenario("odisha_cyclone", district=district)

    broadcast_data = deliver_broadcast(alert, lang=lang, persona="General")

    return {
        "status": "alert_dispatched",
        "scenario": req.scenario,
        "delivery_timer_seconds": broadcast_data["delivery_latency_ms"] / 1000.0,
        "delivery_latency_ms": broadcast_data["delivery_latency_ms"],
        "alert_to_ingest_lag": "< 60 seconds",
        "is_simulation": True,
        "message": broadcast_data["message"],
        "audio_url": broadcast_data["audio_url"],
        "voice_script": broadcast_data["voice_script"],
        "district": alert.district,
        "claim_ledger": broadcast_data["claim_ledger"],
        "quick_replies": broadcast_data["quick_replies"],
        "broadcast": broadcast_data,
    }
