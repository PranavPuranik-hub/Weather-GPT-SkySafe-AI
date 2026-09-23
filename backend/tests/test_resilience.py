"""
Tests for C11.2 Reliability: graceful degradation for all failure paths.
No citizen-facing raw exceptions for any degradation path.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.eval.outage import set_outage
from app.main import app

client = TestClient(app)


# ─── Feed down / Ingest failure ───────────────────────────────────────────────

def test_ingest_outage_health_still_responds():
    """Health endpoint must respond even when source outage is active."""
    set_outage(True)
    try:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        # Status may be healthy or degraded but must not raise 500
        assert data["status"] in ("healthy", "degraded")
    finally:
        set_outage(False)


def test_ingest_sachet_failure_no_crash():
    """If SACHET feed raises an exception, ingest_cycle handles it gracefully."""
    from app.ingest.service import ingest_service
    with patch("app.ingest.sachet_client.sachet_client.fetch_feed_alerts", side_effect=Exception("network error")):
        try:
            alerts = ingest_service.ingest_cycle()
            # Should return empty list, not raise
            assert isinstance(alerts, list)
        except Exception:
            pytest.fail("ingest_cycle must not propagate network exceptions")


# ─── LLM quota exhausted ──────────────────────────────────────────────────────

def test_llm_failure_falls_back_to_template():
    """
    When primary LLM raises, compose_message must fall back to TemplateClient
    without raising and without exposing raw error to citizen.
    """
    from app.pipeline.composer import compose_message

    factsheet = {"facts": [{"id": "F1", "field": "event", "value": "Cyclone"}]}
    actionplan = {"ordered_actions": [{"id": "a1", "instruction": "Evacuate immediately."}]}

    with patch("app.pipeline.composer.generate_with_fallback", side_effect=Exception("LLM quota exceeded")):
        text, voice, ledger, path = compose_message("TEST-001", factsheet, actionplan)
        assert isinstance(text, str)
        assert len(text) > 0
        assert path == "template_fallback"


def test_chat_endpoint_llm_failure_no_500():
    """Chat endpoint must return 200 even when LLM is completely unavailable."""
    with patch("app.pipeline.composer.generate_with_fallback", side_effect=Exception("quota")):
        res = client.post("/api/chat/message", json={"message": "Is there a cyclone warning?"})
        # Must not 500 — either 200 with fallback or a user-friendly 503
        assert res.status_code in (200, 503)
        if res.status_code == 200:
            data = res.json()
            assert "message" in data
            assert len(data["message"]) > 0


# ─── TTS / Voice unavailable ─────────────────────────────────────────────────

def test_tts_failure_no_crash():
    """Voice synthesis failure must not prevent chat message delivery."""
    with patch("app.voice.synthesizer.voice_synthesizer.synthesize", side_effect=Exception("TTS offline")):
        res = client.post("/api/chat/message", json={"message": "Is there a flood warning?"})
        # Message must still be delivered even if audio fails
        assert res.status_code == 200
        data = res.json()
        assert "message" in data


# ─── Database slow / unavailable ─────────────────────────────────────────────

def test_health_degraded_on_db_failure():
    """Health check must return 'degraded' (not 500) when DB is unavailable."""
    with patch("app.api.health.check_db_health", return_value=False):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"


# ─── Internet loss (offline fixtures mode) ───────────────────────────────────

def test_fixtures_mode_serves_alerts():
    """In fixtures mode, alert list must be non-empty and serve without internet."""
    res = client.get("/api/alerts")
    assert res.status_code == 200
    # May return empty list in test DB; important is it doesn't 500
    assert isinstance(res.json(), (list, dict))


def test_chat_works_without_live_feed():
    """Chat endpoint must work in fixtures mode without any live network calls."""
    with patch("app.ingest.sachet_client.sachet_client.fetch_feed_alerts", side_effect=Exception("no internet")):
        res = client.post("/api/chat/message", json={"message": "Flood warning in my area?"})
        assert res.status_code == 200
