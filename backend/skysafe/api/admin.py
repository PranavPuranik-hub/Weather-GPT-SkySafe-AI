"""
Admin API Endpoints: Simulation Injection and System Diagnostics.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from skysafe.core.config import settings
from skysafe.core.db import SessionLocal
from skysafe.ingest.service import ingest_service

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/simulate/{scenario}", response_model=dict[str, Any])
def simulate_scenario(scenario: str, db: Session = Depends(get_db)):
    """
    Inject a simulated drill scenario alert into the system as if newly received.
    Strictly forbidden in live mode.
    """
    if settings.MODE != "fixtures":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulation injection is only allowed in fixtures/demo mode.",
        )

    alert = ingest_service.simulate_scenario(scenario, db=db)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario}' not found. Available: kerala_flood, odisha_cyclone, rajasthan_heatwave, bihar_thunderstorm, tamilnadu_high_wave, uttarakhand_landslide, andhra_cyclone.",
        )

    return alert.to_dict()
