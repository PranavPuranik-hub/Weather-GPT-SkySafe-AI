"""
Models package: SQLAlchemy ORM models for alerts, actions, districts, and resources.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from datetime import datetime
from skysafe.core.db import Base

class Alert(Base):
    """CAP Alert records model."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(100), unique=True, index=True, nullable=False)
    headline = Column(String(255), nullable=False)
    severity = Column(String(50), nullable=False)
    district = Column(String(100), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
