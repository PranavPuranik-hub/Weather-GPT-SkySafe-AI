"""
Tests for Alert Querying API, Drill Simulation API, and /health Ingestion Lag Metrics.
"""
from fastapi.testclient import TestClient

from skysafe.core.config import settings
from skysafe.core.db import Base, engine
from skysafe.ingest.service import ingest_service
from skysafe.main import app

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
