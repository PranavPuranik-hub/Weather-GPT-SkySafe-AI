"""
Health check endpoint reporting system operational metrics.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter
from skysafe.core.config import settings
from skysafe.core.db import check_db_health

router = APIRouter(tags=["Health"])

# Global tracker for fetch timestamps (updated by ingest scheduler)
ingest_status: Dict[str, Optional[str]] = {
    "last_sachet_fetch": None,
    "last_open_meteo_fetch": None
}

@router.get("/health", response_model=Dict[str, Any])
@router.get("/health/", response_model=Dict[str, Any])
def health_check():
    """
    Returns status of DB connection, last SACHET fetch, last Open-Meteo fetch, active LLM provider, and operational mode.
    """
    db_ok = check_db_health()
    
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "last_sachet_fetch": ingest_status["last_sachet_fetch"],
        "last_open_meteo_fetch": ingest_status["last_open_meteo_fetch"],
        "llm_provider": settings.LLM_PROVIDER,
        "mode": settings.MODE
    }
