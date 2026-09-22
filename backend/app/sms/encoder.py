from typing import Dict, Any

def count_sms_segments(text: str, is_unicode: bool) -> int:
    """Calculates SMS segments. GSM-7 = 160 chars. UCS-2 (Unicode) = 70 chars."""
    if not is_unicode:
        if len(text) <= 160: return 1
        return (len(text) // 153) + 1
    else:
        if len(text) <= 70: return 1
        return (len(text) // 67) + 1

def generate_sms(alert: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
    """
    Deterministic SMS encoder. Extracts fields directly from alert data.
    """
    severity = str(alert.get("severity", "")).upper()
    event = str(alert.get("event") or alert.get("category") or "ALERT").upper()
    district = str(alert.get("district", "")).upper()
    headline = alert.get("headline", "")
    
    # English GSM-7
    if lang == "en":
        text = f"SKYSAFE {severity} {event} {district} {headline}. REPLY 1=SAFE 2=HELP"
        # Truncate headline if > 160
        if len(text) > 160:
            allowed_hl_len = 160 - len(f"SKYSAFE {severity} {event} {district} . REPLY 1=SAFE 2=HELP") - 3
            if allowed_hl_len > 0:
                text = f"SKYSAFE {severity} {event} {district} {headline[:allowed_hl_len]}... REPLY 1=SAFE 2=HELP"
        is_unicode = False
        
    # Hindi UCS-2
    elif lang == "hi":
        severity_hi = {"EXTREME": "अत्यंत", "SEVERE": "गंभीर", "MODERATE": "मध्यम"}.get(severity, severity)
        event_hi = "चक्रवात" if "CYCLONE" in event else event
        text = f"SKYSAFE {severity_hi} {event_hi} {district}. सुरक्षित रहें. उत्तर दें: 1=सुरक्षित 2=मदद"
        is_unicode = True
        
    # Odia UCS-2
    elif lang == "or":
        severity_or = {"EXTREME": "ଅତ୍ୟନ୍ତ", "SEVERE": "ଗମ୍ଭୀର", "MODERATE": "ମଧ୍ୟମ"}.get(severity, severity)
        event_or = "ବାତ୍ୟା" if "CYCLONE" in event else event
        text = f"SKYSAFE {severity_or} {event_or} {district}. ସୁରକ୍ଷିତ ରୁହନ୍ତୁ. ଉତ୍ତର: 1=ସୁରକ୍ଷିତ 2=ସାହାଯ୍ୟ"
        is_unicode = True
        
    else:
        text = f"SKYSAFE {severity} {event} {district}. REPLY 1=SAFE 2=HELP"
        is_unicode = False

    segments = count_sms_segments(text, is_unicode)
    
    return {
        "text": text,
        "length": len(text),
        "segments": segments,
        "is_unicode": is_unicode
    }
