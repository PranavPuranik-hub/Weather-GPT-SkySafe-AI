"""
ChatEvent model: logs LLM path used for each compose call.
Used by /api/eval/metrics to compute LLM path breakdown without hardcoded values.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.core.db import Base


class ChatEvent(Base):
    """Records the LLM path taken for each broadcast/compose invocation."""
    __tablename__ = "chat_events"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(128), index=True, nullable=False)
    path_used = Column(String(50), nullable=False)  # llm_ok, llm_retry, template_fallback
    latency_ms = Column(Float, nullable=True)
    lang = Column(String(10), default="en")
    persona = Column(String(50), default="General")
    created_at = Column(DateTime, default=datetime.utcnow)
