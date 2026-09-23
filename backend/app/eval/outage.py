"""
Source Outage Toggle for Lab/Eval mode.
Thread-safe boolean flag. When enabled, ingest_cycle falls back to cached/fixture data.
"""
import threading

_lock = threading.Lock()
_outage_enabled: bool = False


def is_outage_enabled() -> bool:
    """Returns True if source outage simulation is currently active."""
    with _lock:
        return _outage_enabled


def set_outage(enabled: bool) -> None:
    """Enable or disable the source outage simulation."""
    global _outage_enabled
    with _lock:
        _outage_enabled = enabled


class SourceUnavailableError(Exception):
    """Raised by ingest_cycle when outage toggle is active."""
    pass
