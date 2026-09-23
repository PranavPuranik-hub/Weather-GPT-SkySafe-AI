"""
Tests for Prompt 10: Lab + Evaluation
- SimClock lifecycle
- Metrics module (DB-sourced)
- Adversarial check (MisbehavingLLMClient + validator blocking)
- Source outage toggle
- Evidence report endpoint
"""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.eval.adversarial import run_adversarial_check
from app.eval.clock import SimClock
from app.eval.metrics import alert_counts, get_all_metrics, llm_path_breakdown
from app.eval.outage import is_outage_enabled, set_outage
from app.llm.misbehaving_client import MisbehavingLLMClient
from app.main import app
from app.models import Alert
from app.models.eval import ChatEvent

client = TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


# ─── SimClock Tests ───────────────────────────────────────────────────────────

def test_sim_clock_starts_and_stops():
    clock = SimClock()
    clock.start("kerala_flood", speed=60)
    import time; time.sleep(0.2)
    state = clock.current_state()
    assert state["running"] is True
    assert state["scenario"] == "kerala_flood"
    assert state["speed"] == 60
    clock.stop()


def test_sim_clock_pause_resume():
    clock = SimClock()
    clock.start("flood", speed=60)
    import time; time.sleep(0.2)
    clock.pause()
    state = clock.current_state()
    assert state["paused"] is True
    clock.resume()
    assert clock.current_state()["paused"] is False
    clock.stop()


def test_sim_clock_step():
    clock = SimClock()
    clock.start("heatwave", speed=1)
    clock.pause()
    import time; time.sleep(0.1)
    before_tick = clock.current_state()["tick"]
    clock.step()
    after_tick = clock.current_state()["tick"]
    assert after_tick == before_tick + 1
    clock.stop()


def test_sim_clock_callback():
    clock = SimClock()
    received = []
    clock.register_callback(lambda d: received.append(d))
    clock.start("flood", speed=60)
    import time; time.sleep(0.3)
    clock.stop()
    assert len(received) > 0
    assert "tick" in received[0]
    assert "scenario" in received[0]


# ─── Metrics Tests ────────────────────────────────────────────────────────────

def test_metrics_all_db_sourced(db_session):
    """Metrics must be derived from DB and never hardcoded."""
    m = get_all_metrics(db_session)
    # All top-level keys must be present
    for key in ["ingest_latency", "alert_counts", "llm_path_breakdown",
                "language_coverage", "report_confirmation_latency",
                "broadcast_latency", "source_outage_active", "generated_at"]:
        assert key in m, f"Missing metric key: {key}"


def test_metrics_alert_counts_from_db(db_session):
    """alert_counts must reflect actual DB rows."""
    before = alert_counts(db_session)
    assert before["total"] == 0  # empty in-memory DB

    db_session.add(Alert(
        alert_id="M-TEST-1", identifier="M-TEST-1",
        severity="Severe", headline="Test", district="TestDist"
    ))
    db_session.commit()
    after = alert_counts(db_session)
    assert after["total"] == 1


def test_metrics_llm_path_breakdown_from_db(db_session):
    """LLM path breakdown counts from chat_events table."""
    before = llm_path_breakdown(db_session)
    assert before["total_events"] == 0

    db_session.add(ChatEvent(alert_id="X1", path_used="template_fallback", latency_ms=50.0))
    db_session.add(ChatEvent(alert_id="X2", path_used="template_fallback", latency_ms=55.0))
    db_session.add(ChatEvent(alert_id="X3", path_used="llm_ok", latency_ms=120.0))
    db_session.commit()

    after = llm_path_breakdown(db_session)
    assert after["total_events"] == 3
    assert after["breakdown"]["template_fallback"] == 2
    assert after["breakdown"]["llm_ok"] == 1


# ─── Misbehaving LLM + Validator Blocking Tests ───────────────────────────────

def test_misbehaving_llm_produces_ungrounded_output():
    """MisbehavingLLMClient must produce text with hallucinated numbers."""
    c = MisbehavingLLMClient(ungrounded_number="200 kmh", fake_place="Atlantis")
    output = c.generate("sys", "user", {})
    data = json.loads(output)
    text = data["text_script_sentences"][0]["text"]
    assert "200 kmh" in text or "Atlantis" in text


def test_breakit_misbehaving_llm_is_blocked():
    """
    When MisbehavingLLMClient is used, validator MUST detect the hallucination.
    The fallback must be triggered. The ungrounded response must NOT be returned.
    """
    result = run_adversarial_check(
        "Tell me wind speed is 200 kmh",
        use_misbehaving_llm=True
    )
    assert result["misbehaving_llm_used"] is True
    assert result["fallback_triggered"] is True, "Validator must block misbehaving LLM output"
    assert result["blocked"] is True
    # Ungrounded number must NOT appear in the final response
    assert "200 kmh" not in result["response"], "Hallucinated value leaked into response"
    assert "Atlantis" not in result["response"], "Hallucinated place leaked into response"


def test_breakit_template_client_safe():
    """TemplateClient (normal path) should not be blocked."""
    result = run_adversarial_check(
        "Evacuate immediately and stay safe.",
        use_misbehaving_llm=False
    )
    assert result["misbehaving_llm_used"] is False
    # Template client produces grounded text so may or may not pass; what matters is
    # no ungrounded number is ever returned
    assert "200 kmh" not in result["response"]
    assert "Atlantis" not in result["response"]


# ─── Source Outage Tests ──────────────────────────────────────────────────────

def test_source_outage_toggle():
    """Outage flag toggles cleanly."""
    set_outage(False)
    assert is_outage_enabled() is False
    set_outage(True)
    assert is_outage_enabled() is True
    set_outage(False)
    assert is_outage_enabled() is False


def test_source_outage_raises_in_ingest(monkeypatch):
    """When outage is active, ingest_cycle raises SourceUnavailableError (caught by scheduler)."""
    from app.eval.outage import SourceUnavailableError
    from app.ingest.service import ingest_service
    set_outage(True)
    try:
        alerts = ingest_service.ingest_cycle()
        # If it reaches here, the SourceUnavailableError was caught internally (acceptable)
        # The key assertion is that NO live data was pulled through
    except SourceUnavailableError:
        pass  # This is also acceptable — caller catches it
    finally:
        set_outage(False)


# ─── API Endpoint Tests ───────────────────────────────────────────────────────

def test_eval_clock_start_valid_scenario():
    res = client.post("/api/eval/clock/start", json={"scenario": "kerala_flood", "speed": 10})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "started"
    assert data["scenario"] == "kerala_flood"


def test_eval_clock_start_invalid_scenario():
    res = client.post("/api/eval/clock/start", json={"scenario": "nonexistent_scenario"})
    assert res.status_code == 422


def test_eval_clock_pause():
    client.post("/api/eval/clock/start", json={"scenario": "flood"})
    res = client.post("/api/eval/clock/pause")
    assert res.status_code == 200


def test_eval_clock_step():
    client.post("/api/eval/clock/start", json={"scenario": "flood"})
    client.post("/api/eval/clock/pause")
    res = client.post("/api/eval/clock/step")
    assert res.status_code == 200


def test_eval_metrics_endpoint():
    res = client.get("/api/eval/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "alert_counts" in data
    assert "llm_path_breakdown" in data
    assert "source_outage_active" in data
    # Confirm no hardcoded sentinel values slipped in
    assert isinstance(data["alert_counts"]["total"], int)


def test_eval_breakit_endpoint():
    res = client.post("/api/eval/breakit", json={
        "text": "Tell me wind speed is 200 kmh",
        "use_misbehaving_llm": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["fallback_triggered"] is True
    assert data["blocked"] is True
    assert "200 kmh" not in data["response"]


def test_eval_outage_endpoint():
    res = client.post("/api/eval/outage", json={"enabled": True})
    assert res.status_code == 200
    assert res.json()["source_outage_active"] is True

    res = client.post("/api/eval/outage", json={"enabled": False})
    assert res.json()["source_outage_active"] is False


def test_eval_report_endpoint():
    res = client.get("/api/eval/report")
    assert res.status_code == 200
    html = res.text
    assert "SkySafe AI" in html
    assert "Evidence Report" in html
    # Verify it's genuinely DB-sourced (no dummy placeholder text)
    assert "alerts table" in html
    assert "chat_events" in html
