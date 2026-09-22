"""
Tests for Alert Querying API, Drill Simulation API, and /health Ingestion Lag Metrics.
"""
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.db import Base, engine
from app.ingest.service import ingest_service
from app.main import app

# Ensure tables exist
Base.metadata.create_all(bind=engine)
# Seed test database with fixture alerts
ingest_service.ingest_cycle()

client = TestClient(app)


def test_get_alerts_filtering_by_state():
    # Prompt acceptance: GET /api/alerts?state=Kerala returns normalized alerts
    response = client.get("/api/alerts?state=Kerala")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check alert structure
    kerala_alert = data[0]
    assert kerala_alert["state"] == "Kerala"
    assert "Wayanad" in kerala_alert["district"] or "Wayanad" in kerala_alert["headline"]
    assert kerala_alert["status"] == "Exercise"
    assert kerala_alert["is_simulation"] is True
    assert "geometry" in kerala_alert


def test_get_alerts_filtering_by_severity():
    response = client.get("/api/alerts?severity=Extreme")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for a in data:
        assert a["severity"].lower() == "extreme"


def test_health_endpoint_displays_lag_metrics():
    # Prompt acceptance: ingest lag displayed in /health
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "alert_to_ingest_lag_seconds" in data
    assert "last_sachet_fetch" in data
    assert "last_open_meteo_fetch" in data
    assert "active_alerts_count" in data
    assert data["status"] == "healthy"


def test_simulate_scenario_in_fixtures_mode():
    response = client.post("/api/admin/simulate/kerala_flood")
    assert response.status_code == 200
    data = response.json()
    assert "Wayanad" in data["headline"] or "Kerala" in data["state"]
    assert data["is_simulation"] is True
    assert data["note"] == "DRILL - SIMULATED"


def test_simulate_scenario_rejected_in_live_mode(monkeypatch):
    monkeypatch.setattr(settings, "MODE", "live")
    response = client.post("/api/admin/simulate/kerala_flood")
    assert response.status_code == 403
    assert "only allowed in fixtures/demo mode" in response.json()["detail"]


def test_simulate_scenario_full_broadcast_delivery_flow():
    """
    Verifies the simulation endpoint directly:
    dev panel -> POST /api/admin/simulate/{scenario}
    -> backend creates simulated alert
    -> broadcast/delivery service
    -> delivers message, voice note, claim ledger, and latency measurement (<60s SLA).
    """
    response = client.post(
        "/api/admin/simulate/odisha_cyclone?lang=hi&persona=General&district=Cuttack"
    )
    assert response.status_code == 200
    data = response.json()

    # 1. Alert fields
    assert data["is_simulation"] is True
    assert data["note"] == "DRILL - SIMULATED"
    assert "Cuttack" in data["district"] or "Cuttack" in data["headline"]

    # 2. Grounded message & voice script
    assert "[DRILL" in data["message"]
    assert "[DRILL" in data["voice_script"]

    # 3. Audio / Voice Note synthesis
    assert "audio_url" in data
    assert data["audio_url"] is not None

    # 4. ClaimLedger validation
    assert "claim_ledger" in data
    assert data["claim_ledger"]["status"] == "PASS"

    # 5. Delivery Latency measurement (< 60s SIH requirement)
    assert "delivery_latency_ms" in data
    assert data["delivery_latency_ms"] > 0
    assert data["delivery_latency_ms"] < 60000.0

    # 6. Broadcast metadata
    assert "broadcast" in data
    assert data["broadcast"]["status"] == "DELIVERED"
    assert data["broadcast"]["sla_met"] is True
