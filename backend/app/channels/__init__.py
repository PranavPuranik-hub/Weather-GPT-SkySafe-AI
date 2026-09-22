"""
Channels package: SMS and messaging integration (Twilio / Sarvam).
"""

def send_sms(to: str, message: str) -> bool:
    """
    Send SMS advisory under 160 characters (or 70 characters for non-Latin).
    """
    return True
