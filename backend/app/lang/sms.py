"""
SMS character budgeting and formatting service.
Supports GSM-7 and Unicode (UCS-2) segment calculation per telecom standards.
"""
from typing import Any, Dict

# Standard GSM-7 Basic Character Set + Extension Table
GSM7_BASIC = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
GSM7_EXTENDED = set("|^€{}[~]\\")
GSM7_ALL = GSM7_BASIC | GSM7_EXTENDED


def is_gsm7(text: str) -> bool:
    """Check if all characters in string belong to GSM 7-bit (basic or extended) alphabet."""
    return all(c in GSM7_ALL for c in text)


def calculate_sms_segments(text: str) -> Dict[str, Any]:
    """
    Calculate SMS segment count, encoding type, and character length.
    - GSM-7: 1 segment <= 160 chars; concatenated segments <= 153 chars each.
      Characters from extended table count as 2 septets.
    - Unicode (UCS-2): 1 segment <= 70 chars; concatenated segments <= 67 chars each.
    """
    gsm = is_gsm7(text)

    if gsm:
        # Extended characters count as 2 septets
        effective_len = sum(2 if c in GSM7_EXTENDED else 1 for c in text)
        if effective_len <= 160:
            segments = 1 if effective_len > 0 else 0
        else:
            segments = (effective_len + 152) // 153
        max_single = 160
        max_multi = 153
        char_count = effective_len
    else:
        char_count = len(text)
        if char_count <= 70:
            segments = 1 if char_count > 0 else 0
        else:
            segments = (char_count + 66) // 67
        max_single = 70
        max_multi = 67

    return {
        "text": text,
        "char_count": char_count,
        "is_gsm7": gsm,
        "encoding": "GSM-7" if gsm else "Unicode",
        "segment_count": segments,
        "max_single_segment": max_single,
        "concat_segment_size": max_multi,
        "under_three_segments": segments <= 3,
    }


def format_emergency_sms(
    grade: str,
    event: str,
    area: str,
    action: str,
    lang: str = "en"
) -> str:
    """
    Construct a concise, safety-critical SMS message strictly fitting:
    - <= 160 characters for English (1 segment)
    - <= 201 characters for Indic scripts (<= 3 segments)
    """
    header = "[DRILL]"

    # Format localized emergency header
    if lang == "hi":
        sms = f"{header} {event} ({area}) - ग्रेड {grade}: {action}"
    elif lang == "bn":
        sms = f"{header} {event} ({area}) - গ্রেড {grade}: {action}"
    elif lang == "or":
        sms = f"{header} {event} ({area}) - ଗ୍ରେଡ୍ {grade}: {action}"
    elif lang == "ta":
        sms = f"{header} {event} ({area}) - தரம் {grade}: {action}"
    elif lang == "te":
        sms = f"{header} {event} ({area}) - గ్రేడ్ {grade}: {action}"
    elif lang == "mr":
        sms = f"{header} {event} ({area}) - श्रेणी {grade}: {action}"
    elif lang == "gu":
        sms = f"{header} {event} ({area}) - ગ્રેડ {grade}: {action}"
    else:
        sms = f"{header} {event} ({area}) - Grade {grade}: {action}"

    # Truncate cleanly if needed
    gsm = is_gsm7(sms)
    limit = 160 if gsm else 201  # 201 chars max for 3 Unicode segments
    if len(sms) > limit:
        sms = sms[: limit - 3] + "..."
    return sms
