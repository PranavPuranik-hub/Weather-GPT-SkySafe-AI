from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.db import Base


class WardInfo(Base):
    """Static demographic and geographic data for a ward."""
    __tablename__ = "ward_info"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    population = Column(Integer, nullable=False)
    elderly_share = Column(Float, nullable=False)  # e.g. 0.15 for 15%
    kutcha_house_share = Column(Float, nullable=False)
    low_lying_score = Column(Float, nullable=False) # 0.0 to 1.0
    hospital_distance_km = Column(Float, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    polygon = Column(String(2000), nullable=True) # GeoJSON string for map rendering


class Depot(Base):
    """A physical location storing emergency resources."""
    __tablename__ = "depots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)

    resources = relationship("Resource", back_populates="depot")


class Resource(Base):
    """Emergency resources available at a depot."""
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    depot_id = Column(Integer, ForeignKey("depots.id"), nullable=False)
    type = Column(String(50), nullable=False) # e.g. "Pumps", "Boats", "NDRF Teams"
    total_qty = Column(Integer, nullable=False)
    available_qty = Column(Integer, nullable=False)

    depot = relationship("Depot", back_populates="resources")


class Shelter(Base):
    """Official emergency shelters."""
    __tablename__ = "shelters"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(String(50), index=True, nullable=True)
    name = Column(String(100), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=False)
    current_occupancy = Column(Integer, default=0)
    contact = Column(String(50), nullable=True)


class Decision(Base):
    """Audit log of official actions taken."""
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(String(50), index=True, nullable=False)
    action = Column(String(50), nullable=False) # Approve, Dispatch, Dismiss, Broadcast
    resource_type = Column(String(50), nullable=True)
    qty = Column(Integer, nullable=True)
    status = Column(String(50), default="Pending")
    timestamp = Column(DateTime, default=datetime.utcnow)
    rationale = Column(String(2000), nullable=True)
    user_role = Column(String(50), default="Officer")
