"""
Admin API Endpoints: Simulation Injection and System Diagnostics.
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.channels.broadcast import deliver_broadcast
from app.core.config import settings
from app.core.db import SessionLocal
from app.ingest.service import ingest_service

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/simulate/{scenario}", response_model=dict[str, Any])
def simulate_scenario(
    scenario: str,
    lang: str = Query(default="en"),
    persona: str = Query(default="General"),
    district: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Inject a simulated drill scenario alert into the system as if newly received,
    and trigger the broadcast delivery pipeline (ActionPlan, Grounding, Voice, Latency).
    Strictly forbidden in live mode.
    """
    if settings.MODE != "fixtures":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulation injection is only allowed in fixtures/demo mode.",
        )

    alert = ingest_service.simulate_scenario(scenario, district=district, db=db)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario}' not found. Available: kerala_flood, odisha_cyclone, rajasthan_heatwave, bihar_thunderstorm, tamilnadu_high_wave, uttarakhand_landslide, andhra_cyclone, cyclone_t24, cyclone_t12, cyclone_t3, flood, heatwave.",
        )

    # Execute end-to-end broadcast delivery pipeline
    broadcast_result = deliver_broadcast(alert, lang=lang, persona=persona)

    # Return full alert dict enriched with broadcast delivery data
    alert_dict = alert.to_dict()
    alert_dict.update({
        "broadcast": broadcast_result,
        "message": broadcast_result["message"],
        "voice_script": broadcast_result["voice_script"],
        "audio_url": broadcast_result["audio_url"],
        "claim_ledger": broadcast_result["claim_ledger"],
        "delivery_latency_ms": broadcast_result["delivery_latency_ms"],
        "quick_replies": broadcast_result["quick_replies"],
        "action_plan": broadcast_result["action_plan"],
        "intent": "simulated_alert",
    })

    return alert_dict
