import os
import logging

logger = logging.getLogger("app")

TWILIO_ENABLED = os.getenv("TWILIO_ENABLED", "false").lower() == "true"

def send_twilio_message(to_number: str, body: str, is_whatsapp: bool = False) -> bool:
    """
    Adapter for Twilio API (SMS or WhatsApp Business).
    Defaults to returning True in simulation mode if TWILIO_ENABLED is false.
    """
    prefix = "whatsapp:" if is_whatsapp else ""
    target = f"{prefix}{to_number}"
    
    if not TWILIO_ENABLED:
        logger.info(f"[SIMULATED TWILIO] Sending to {target}: {body}")
        return True
        
    try:
        from twilio.rest import Client
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_WHATSAPP_FROM" if is_whatsapp else "TWILIO_SMS_FROM")
        
        if not account_sid or not auth_token:
            logger.error("Twilio credentials missing.")
            return False
            
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=target
        )
        logger.info(f"Twilio message sent: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"Twilio error: {e}")
        return False
