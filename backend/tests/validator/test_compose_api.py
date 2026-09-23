"""
Integration tests for compose API.
"""
from datetime import datetime

from fastapi.testclient import TestClient

from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models import Alert

client = TestClient(app)

def setup_module():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(Alert).filter(Alert.identifier == "TEST-ALERT").first():
        a = Alert(
            identifier="TEST-ALERT",
            event="Cyclone",
            severity="Severe",
            urgency="Expected",
            certainty="Likely",
            district="Mumbai",
            state="Maharashtra",
            headline="Cyclone warning",
            description="Wind speeds up to 100 kmh.",
            instruction="Stay indoors.",
            expires=datetime.now()
        )
        db.add(a)
        db.commit()
    db.close()

def test_compose_endpoint_fallback():
    # Because LLM is not mocked and we don't know if Ollama is running,
    # it should eventually fallback to template if it fails.
    resp = client.post("/api/compose", json={
        "alert_id": "TEST-ALERT",
        "persona": "general",
        "lang": "en"
    })

    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert "voice_script" in data
    assert "claim_ledger" in data
    assert "path_used" in data

    # Wait, Template fallback should work
    if data["claim_ledger"]["status"] != "PASS":
        print(data["claim_ledger"])
    assert data["claim_ledger"]["status"] == "PASS"
    assert data["path_used"] in ["llm_ok", "llm_retry", "template_fallback"]
