"""
Models package: SQLAlchemy ORM models for alerts, actions, districts, and resources.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.core.db import Base


from app.models.reports import Report, WardState, WardStateEnum
from app.models.decision import WardInfo, Depot, Resource, Shelter, Decision
from app.models.eval import ChatEvent

class Alert(Base):
    """
    Normalized CAP 1.2 Alert Model storing parsed official alerts and drill exercises.
    Compatible with SQLite and Postgres/PostGIS.
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(128), unique=True, index=True, nullable=False)
    identifier = Column(String(128), index=True, nullable=True)
    sender = Column(String(255), nullable=True)
    sent = Column(DateTime, nullable=True)
    status = Column(String(50), default="Actual")
    msg_type = Column(String(50), default="Alert")
    scope = Column(String(50), default="Public")
    note = Column(String(255), nullable=True)

    # Info block
    language = Column(String(20), default="en")
    category = Column(String(50), default="Met")
    event = Column(String(100), nullable=True)
    urgency = Column(String(50), default="Unknown")
    severity = Column(String(50), nullable=False)
    certainty = Column(String(50), default="Unknown")
    effective = Column(DateTime, nullable=True)
    onset = Column(DateTime, nullable=True)
    expires = Column(DateTime, nullable=True)
    headline = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    instruction = Column(Text, nullable=True)

    # Area block & Geometry
    area_desc = Column(Text, nullable=True)
    polygon = Column(Text, nullable=True)
    geocode = Column(Text, nullable=True)
    geometry = Column(Text, nullable=True)  # GeoJSON string representation

    # Location tags
    state = Column(String(100), index=True, nullable=True)
    district = Column(String(100), index=True, nullable=False)

    # Operational metadata
    is_expired = Column(Boolean, default=False, index=True)
    is_simulation = Column(Boolean, default=False, index=True)
    source = Column(String(50), default="SACHET")
    ingested_at = Column(DateTime, default=datetime.utcnow)
    ingest_lag_seconds = Column(Float, nullable=True)
    raw_xml = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs: Any) -> None:
        if "identifier" in kwargs and "alert_id" not in kwargs:
            kwargs["alert_id"] = kwargs["identifier"]
        elif "alert_id" in kwargs and "identifier" not in kwargs:
            kwargs["identifier"] = kwargs["alert_id"]
        super().__init__(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Convert alert instance into serializable dictionary."""
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "identifier": self.identifier or self.alert_id,
            "sender": self.sender,
            "sent": self.sent.isoformat() if self.sent else None,
            "status": self.status,
            "msg_type": self.msg_type,
            "scope": self.scope,
            "note": self.note,
            "language": self.language,
            "category": self.category,
            "event": self.event,
            "urgency": self.urgency,
            "severity": self.severity,
            "certainty": self.certainty,
            "effective": self.effective.isoformat() if self.effective else None,
            "onset": self.onset.isoformat() if self.onset else None,
            "expires": self.expires.isoformat() if self.expires else None,
            "headline": self.headline,
            "description": self.description,
            "instruction": self.instruction,
            "area_desc": self.area_desc,
            "polygon": self.polygon,
            "geocode": self.geocode,
            "geometry": self.geometry,
            "state": self.state,
            "district": self.district,
            "is_expired": self.is_expired,
            "is_simulation": self.is_simulation,
            "source": self.source,
            "ingested_at": self.ingested_at.isoformat() if self.ingested_at else None,
            "ingest_lag_seconds": self.ingest_lag_seconds,
        }
