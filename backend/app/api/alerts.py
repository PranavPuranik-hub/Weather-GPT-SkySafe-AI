"""
Alerts Query API Endpoint with Regional and Severity Filtering.
"""
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Alert

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=list[dict[str, Any]])
@router.get("/", response_model=list[dict[str, Any]])
def list_alerts(
    state: str | None = Query(None, description="Filter by State name (case-insensitive)"),
    district: str | None = Query(None, description="Filter by District name (case-insensitive)"),
    severity: str | None = Query(None, description="Filter by Severity level (e.g. Extreme, Severe)"),
    active_only: bool = Query(True, description="Only return non-expired alerts"),
    db: Session = Depends(get_db),
):
    """
    List normalized CAP weather alerts with optional state, district, severity, and active filters.
    """
    query = db.query(Alert)

    if active_only:
        query = query.filter(Alert.is_expired.is_(False))

    if state:
        query = query.filter(Alert.state.ilike(f"%{state.strip()}%"))

    if district:
        query = query.filter(Alert.district.ilike(f"%{district.strip()}%"))

    if severity:
        query = query.filter(Alert.severity.ilike(f"%{severity.strip()}%"))

    results = query.order_by(Alert.sent.desc().nullslast()).all()
    return [alert.to_dict() for alert in results]
