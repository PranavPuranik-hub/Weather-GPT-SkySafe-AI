import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.db import Base


class WardStateEnum(str, enum.Enum):
    PREDICTED = "Predicted"
    REPORTED = "Reported"
    CONFIRMED = "Confirmed"
    RESOLVED = "Resolved"

class WardState(Base):
    __tablename__ = "ward_states"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(String(50), unique=True, index=True, nullable=False)
    state = Column(String(50), default=WardStateEnum.PREDICTED.value)
    last_updated = Column(DateTime, default=datetime.utcnow)
    ground_truth_score = Column(Float, default=1.0)
    severity = Column(String(50), nullable=True)

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=True)
    category = Column(String(50), index=True, nullable=False)
    ward_id = Column(String(50), ForeignKey("ward_states.ward_id"), index=True, nullable=False)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    photo_url = Column(String(255), nullable=True)
    reporter_hash = Column(String(255), index=True, nullable=False)
    confidence = Column(String(50), default="Unverified") # Unverified, Confirmed, Spam

    ward = relationship("WardState", backref="reports")
