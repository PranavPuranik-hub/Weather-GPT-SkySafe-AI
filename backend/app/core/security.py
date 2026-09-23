"""
Security middleware and utilities for SkySafe AI.
Implements: input length limits, rate limiting, prompt-injection protection,
phone number hashing, PII scrubbing from logs.
"""
import hashlib
import logging
import re
import time
from collections import defaultdict
from threading import Lock

logger = logging.getLogger("app.security")

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_MESSAGE_LENGTH = 500       # citizen chat message
MAX_REPORT_TEXT_LENGTH = 1000  # incident report text
MAX_WARD_ID_LENGTH = 50
MAX_DISTRICT_LENGTH = 100
MAX_LANG_LENGTH = 10
MAX_PERSONA_LENGTH = 50

# Patterns that indicate prompt injection attempts
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+instructions",
    r"system\s*prompt",
    r"you\s+are\s+now",
    r"forget\s+(everything|all|your)",
    r"disregard\s+(your|all|previous)",
    r"act\s+as\s+(a|an)\s+\w+",
    r"pretend\s+(you\s+are|to\s+be)",
    r"jailbreak",
    r"dan\s+mode",
    r"developer\s+mode",
    r"bypass\s+(safety|rules|grounding)",
    r"override\s+(safety|validator|grounding)",
    r"</?(system|user|assistant|prompt|instruction)>",
    r"\[INST\]",
    r"<\|im_start\|>",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

# PII patterns to scrub from logs
_PII_PHONE_RE = re.compile(r"\b(\+?91)?[6-9]\d{9}\b")
_PII_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


# ─── Phone number hashing ─────────────────────────────────────────────────────

def hash_phone(phone: str) -> str:
    """
    One-way SHA-256 hash of a phone number.
    No PII is stored; the hash is stable for deduplication.
    """
    normalized = re.sub(r"[^\d+]", "", phone)
    return hashlib.sha256(normalized.encode()).hexdigest()[:32]


# ─── Prompt-injection detection ───────────────────────────────────────────────

def detect_prompt_injection(text: str) -> bool:
    """
    Returns True if the text contains known prompt-injection patterns.
    User text must NEVER be inserted into the system prompt; this is a
    defence-in-depth check for the report pipeline and chat router.
    """
    return bool(_INJECTION_RE.search(text))


def sanitize_user_input(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """
    Truncate to max_length and strip leading/trailing whitespace.
    Does NOT modify content beyond truncation (no HTML escaping —
    that's the validator's job).
    """
    return text[:max_length].strip()


# ─── PII-safe logging ─────────────────────────────────────────────────────────

class PIIRedactingFilter(logging.Filter):
    """Strips phone numbers and email addresses from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage())
        msg = _PII_PHONE_RE.sub("[PHONE_REDACTED]", msg)
        msg = _PII_EMAIL_RE.sub("[EMAIL_REDACTED]", msg)
        record.msg = msg
        record.args = ()
        return True


def install_pii_filter() -> None:
    """Install the PII-redacting filter on the root logger once."""
    root = logging.getLogger()
    for handler in root.handlers:
        if not any(isinstance(f, PIIRedactingFilter) for f in handler.filters):
            handler.addFilter(PIIRedactingFilter())
    # Also apply to the app logger
    app_logger = logging.getLogger("app")
    if not any(isinstance(f, PIIRedactingFilter) for f in app_logger.filters):
        app_logger.addFilter(PIIRedactingFilter())


# ─── Simple token-bucket rate limiter ─────────────────────────────────────────

class RateLimiter:
    """
    Per-IP token-bucket rate limiter. Thread-safe.
    Defaults: 60 requests / 60 seconds per IP.
    """

    def __init__(self, max_calls: int = 60, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, client_ip: str) -> bool:
        now = time.monotonic()
        with self._lock:
            timestamps = self._buckets[client_ip]
            # Evict old entries
            cutoff = now - self.window
            self._buckets[client_ip] = [t for t in timestamps if t > cutoff]
            if len(self._buckets[client_ip]) >= self.max_calls:
                return False
            self._buckets[client_ip].append(now)
            return True


# Singleton rate limiter (60 req / 60 s per IP)
rate_limiter = RateLimiter(max_calls=60, window_seconds=60)
