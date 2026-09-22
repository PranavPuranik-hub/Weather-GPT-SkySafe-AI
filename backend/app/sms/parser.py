from typing import Optional
from sqlalchemy.orm import Session
from app.reports.service import submit_report

def parse_sms_reply(reply_text: str, phone_hash: str, ward_id: str, db: Session) -> Optional[str]:
    """
    Deterministically maps numeric SMS replies to report categories.
    Returns the parsed intent/category or None if unparseable.
    """
    text = reply_text.strip()
    
    category = None
    if text == "1":
        category = "Safe"
    elif text == "2":
        category = "Need Help"
    elif text == "3":
        category = "Water Logging"
        
    if category:
        submit_report(
            db=db,
            text=f"SMS Reply: {text} -> {category}",
            lat=0.0,
            lon=0.0,
            user_hash=phone_hash,
            ward_id=ward_id
        )
        return category
        
    return None
