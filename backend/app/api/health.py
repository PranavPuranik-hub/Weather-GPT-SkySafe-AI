"""
Health check endpoint reporting system operational metrics and ingest lag.
"""
from typing import Any

from fastapi import APIRouter

from app.core.config import settings
from app.core.db import SessionLocal, check_db_health
from app.ingest.service import ingest_service
from app.models import Alert

router = APIRouter(tags=["Health"])

# Global tracker for fetch timestamps
ingest_status: dict[str, str | None] = {
    "last_sachet_fetch": None,
    "last_open_meteo_fetch": None,
}


@router.get("/health", response_model=dict[str, Any])
@router.get("/health/", response_model=dict[str, Any])
def health_check():
    """
    Returns status of DB connection, last SACHET fetch, last Open-Meteo fetch,
    alert-to-ingest lag (in seconds), active LLM provider, and operational mode.
    """
    db_ok = check_db_health()

    active_alerts = 0
    if db_ok:
        try:
            with SessionLocal() as db:
                active_alerts = db.query(Alert).filter(Alert.is_expired.is_(False)).count()
        except Exception:
            pass

    sachet_fetch = ingest_service.last_sachet_fetch or ingest_status["last_sachet_fetch"]
    open_meteo_fetch = ingest_status["last_open_meteo_fetch"] or sachet_fetch

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "last_sachet_fetch": sachet_fetch,
        "last_open_meteo_fetch": open_meteo_fetch,
        "alert_to_ingest_lag_seconds": ingest_service.last_ingest_lag_seconds,
        "fetch_latency_ms": ingest_service.last_fetch_latency_ms,
        "active_alerts_count": active_alerts,
        "llm_provider": settings.LLM_PROVIDER,
        "mode": settings.MODE,
    }
