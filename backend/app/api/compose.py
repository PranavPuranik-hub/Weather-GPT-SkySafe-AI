"""
Compose API Endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.action_plan import generate_action_plan
from app.core.db import SessionLocal
from app.core.factsheet import build_factsheet
from app.models import Alert
from app.pipeline.composer import compose_message

compose_router = APIRouter(prefix="/api/compose", tags=["compose"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ComposeRequest(BaseModel):
    alert_id: str
    persona: str = "general"
    lang: str = "en"

class ComposeResponse(BaseModel):
    text: str
    voice_script: str
    claim_ledger: dict
    path_used: str

@compose_router.post("", response_model=ComposeResponse)
def compose_message_endpoint(req: ComposeRequest, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.identifier == req.alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert_dict = {
        "identifier": alert.identifier,
        "event": alert.event,
        "severity": alert.severity,
        "urgency": alert.urgency,
        "certainty": alert.certainty,
        "district": alert.district,
        "state": alert.state,
        "headline": alert.headline,
        "description": alert.description,
        "instruction": alert.instruction,
        "expires": alert.expires.isoformat() if alert.expires else None
    }

    # We pass empty open_meteo_data as we might not have it loaded in memory here,
    # or we could fetch it if needed. The FactSheet will still parse alert.
    factsheet = build_factsheet(alert_dict)

    actionplan = generate_action_plan(factsheet, persona=req.persona)

    fs_dict = {"facts": [f.to_dict() for f in factsheet.facts]}
    ap_dict = actionplan.to_dict()

    text_en, voice_en, ledger_en, path_used = compose_message(
        alert_id=req.alert_id,
        factsheet=fs_dict,
        actionplan=ap_dict
    )

    if req.lang.lower() != "en":
        from app.lang.translator import translation_service
        text, voice_script, ledger, path_used = translation_service.translate_message(
            alert_id=req.alert_id,
            factsheet=fs_dict,
            actionplan=ap_dict,
            text_en=text_en,
            voice_en=voice_en,
            lang=req.lang
        )
    else:
        text = text_en
        voice_script = voice_en
        ledger = ledger_en

    return ComposeResponse(
        text=text,
        voice_script=voice_script,
        claim_ledger=ledger.dict() if hasattr(ledger, "dict") else ledger.model_dump(),
        path_used=path_used
    )
