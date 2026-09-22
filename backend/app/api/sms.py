from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.sms.parser import parse_sms_reply
from app.sms.encoder import generate_sms
from app.sms.twilio_adapter import send_twilio_message
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/sms", tags=["SMS Fallback"])

class SMSWebhookPayload(BaseModel):
    Body: str
    From: str
    WardId: str = "Ward 7" # Mock default for demo simulator

@router.post("/webhook")
def sms_webhook(payload: SMSWebhookPayload, db: Session = Depends(get_db)):
    """
    Receives incoming SMS, parses deterministically, and triggers citizen report flow.
    """
    category = parse_sms_reply(payload.Body, payload.From, payload.WardId, db)
    if not category:
        return {"status": "ignored", "reason": "unparseable"}
        
    return {"status": "success", "category": category}

class SMSOutboundPayload(BaseModel):
    alert_data: dict
    lang: str = "en"
    to_number: str = "+910000000000"
    is_whatsapp: bool = False

@router.post("/send")
def send_sms(payload: SMSOutboundPayload):
    """
    Encodes an alert and sends via Twilio adapter.
    """
    encoded = generate_sms(payload.alert_data, payload.lang)
    success = send_twilio_message(payload.to_number, encoded["text"], payload.is_whatsapp)
    return {
        "status": "success" if success else "error",
        "encoded": encoded
    }
