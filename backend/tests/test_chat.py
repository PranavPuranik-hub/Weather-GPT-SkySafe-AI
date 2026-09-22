"""
Acceptance Test Suite for Citizen Chat Agent.
Verifies:
1. 15 scripted utterances in 3 languages (English, Hindi, Odia).
2. Deterministic tool execution and FactSheet/ClaimLedger generation.
3. Honest "I don't have this data" fallback pointing to official IMD helpline for out-of-scope queries.
4. Onboarding flow with hashed phone storage.
5. Dev panel alert simulation with <60s delivery latency timer.
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.core.db import Base, engine, SessionLocal
from app.models import Alert

client = TestClient(app)

SCRIPTED_UTTERANCES = [
    # 1. Current alert (English)
    ("Is there any active weather alert in Cuttack?", "en", "current_alert", ["get_active_alerts"]),
    # 2. Current alert (Hindi)
    ("क्या कटक में कोई सक्रिय चेतावनी है?", "hi", "current_alert", ["get_active_alerts"]),
    # 3. Current alert (Odia)
    ("କଟକରେ କୌଣସି ବାତ୍ୟା ଚେତାବନୀ ଅଛି କି?", "or", "current_alert", ["get_active_alerts"]),
    # 4. Forecast (English)
    ("Give me the 3-day weather forecast for Puri", "en", "forecast", ["get_forecast"]),
    # 5. Forecast (Hindi)
    ("पुरी के लिए आज का मौसम पूर्वानुमान क्या है?", "hi", "forecast", ["get_forecast"]),
    # 6. Forecast (Odia)
    ("ପୁରୀ ପାଇଁ ଆଜିର ପାଣିପାଗ ପୂର୍ବାନୁମାନ କୁହନ୍ତୁ", "or", "forecast", ["get_forecast"]),
    # 7. Safety check (English)
    ("Is it safe to go fishing in Puri sea today?", "en", "safety_check", ["get_marine"]),
    # 8. Safety check (Hindi)
    ("क्या आज समुद्र में मछली पकड़ने जाना सुरक्षित है?", "hi", "safety_check", ["get_marine"]),
    # 9. Safety check (Odia)
    ("ସମୁଦ୍ରକୁ ମାଛ ଧରିବା ପାଇଁ ଯିବା ସୁରକ୍ଷିତ କି?", "or", "safety_check", ["get_marine"]),
    # 10. Nearest shelter (English)
    ("Where is the nearest cyclone shelter in Cuttack?", "en", "nearest_shelter", ["nearest_shelter"]),
    # 11. Nearest shelter (Hindi)
    ("कटक में निकटतम राहत शिविर या आश्रय स्थल कहाँ है?", "hi", "nearest_shelter", ["nearest_shelter"]),
    # 12. Action advice (English)
    ("What should I do now for my safety?", "en", "action_advice", ["get_active_alerts"]),
    # 13. Climate info (English)
    ("What is normal rainfall in July in Cuttack?", "en", "climate_info", ["get_climate_normals"]),
    # 14. Change language (English)
    ("Change language to Hindi", "en", "change_language", []),
    # 15. Registration (English)
    ("Register my phone number for disaster alerts", "en", "registration", []),
]


def setup_module():
    """Seed an alert for testing."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    existing = db.query(Alert).filter(Alert.identifier == "DRILL-CYC-TEST-CHAT").first()
    future_time = datetime.utcnow() + timedelta(days=2)
    if not existing:
        alert = Alert(
            alert_id="DRILL-CYC-TEST-CHAT",
            identifier="DRILL-CYC-TEST-CHAT",
            event="Severe Cyclonic Storm",
            severity="Severe",
            district="Cuttack",
            state="Odisha",
            headline="Severe Cyclone Warning for Cuttack coast.",
            instruction="Inspect house roof. Prepare emergency kit before 95 km/h winds.",
            is_simulation=True,
            is_expired=False,
            expires=future_time
        )
        db.add(alert)
        db.commit()
    else:
        existing.is_expired = False
        existing.expires = future_time
        db.commit()
    db.close()


@pytest.mark.parametrize("query,lang,expected_intent,expected_tools", SCRIPTED_UTTERANCES)
def test_scripted_chat_utterances(query, lang, expected_intent, expected_tools):
    """
    Acceptance Test: 15 scripted utterances in 3 languages.
    Verifies intent classification, tool execution, and ClaimLedger generation.
    """
    resp = client.post("/api/chat/message", json={
        "message": query,
        "lang": lang,
        "location": "Cuttack"
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == expected_intent
    for tool in expected_tools:
        assert tool in data["tools_called"]

    assert len(data["message"]) > 0
    assert data["session_id"] is not None

    # Verify Grounding Validator produced ClaimLedger with PASS status
    assert data["claim_ledger"] is not None
    assert data["claim_ledger"]["status"] == "PASS"


def test_outside_scope_honest_fallback():
    """
    Acceptance Test:
    Asking for something outside official weather/disaster data yields an honest
    'I don't have this data' response with IMD helpline and website. Never guess.
    """
    resp = client.post("/api/chat/message", json={
        "message": "Who won the cricket match yesterday between India and Australia?",
        "lang": "en"
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "outside_scope"
    assert "I do not have verified official weather or disaster data" in data["message"]
    assert "https://mausam.imd.gov.in" in data["message"]
    assert "1077" in data["message"] or "1800-180-1717" in data["message"]
    assert data["claim_ledger"]["status"] == "PASS"


def test_onboarding_and_phone_hash():
    """Verify onboarding registers preferences and hashes phone number with SHA-256."""
    resp = client.post("/api/chat/onboard", json={
        "phone": "9876543210",
        "language": "hi",
        "persona": "farmer",
        "location": "Puri",
        "consent_alerts": True
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["language"] == "hi"
    assert data["persona"] == "farmer"
    assert data["location"]["district"] == "Puri"
    assert data["phone_hash"] is not None
    # Phone number must NOT be in plain text
    assert "9876543210" not in data["phone_hash"]
    assert len(data["phone_hash"]) == 64  # SHA-256 hex length
    assert len(data["quick_replies"]) > 0


def test_dev_panel_simulate_incoming_alert():
    """Verify Dev panel simulate alert endpoint dispatches alert with latency timer under 60s."""
    resp = client.post("/api/chat/simulate", json={
        "scenario": "cyclone_t12",
        "district": "Cuttack"
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "alert_dispatched"
    assert data["delivery_timer_seconds"] <= 60
    assert data["is_simulation"] is True
    assert "[DRILL / SIMULATION]" in data["message"]
    assert data["audio_url"] is not None


def test_active_alert_query_returns_grounded_wayanad_alert():
    """
    Prompt 6 Verification:
    Query 'Is there any active alert?' routes to CURRENT_ACTIVE_ALERT,
    retrieves actual active Wayanad alert data, constructs FactSheet,
    composes grounded message, passes Grounding Validator with Claim Ledger.
    """
    resp = client.post("/api/chat/message", json={
        "message": "Is there any active alert?"
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "current_alert"
    assert "get_active_alerts" in data["tools_called"]
    # Confirm it returns actual active Wayanad alert data
    assert "Wayanad" in data["message"]
    # Verified Claim Ledger must be present with PASS status
    assert data["claim_ledger"] is not None
    assert data["claim_ledger"]["status"] == "PASS"


def test_active_alert_not_marked_as_drill_when_not_simulation():
    """
    Confirm alert is NOT marked as [DRILL] unless the underlying alert itself is a simulation.
    """
    db = SessionLocal()
    # Ensure a non-simulation alert exists for Cuttack
    existing = db.query(Alert).filter(Alert.identifier == "REAL-ALERT-TEST-001").first()
    future_time = datetime.utcnow() + timedelta(days=2)
    if not existing:
        real_alert = Alert(
            alert_id="REAL-ALERT-TEST-001",
            identifier="REAL-ALERT-TEST-001",
            event="Severe Thunderstorm Warning",
            severity="Severe",
            district="Cuttack",
            state="Odisha",
            headline="Severe Thunderstorm Warning for Cuttack.",
            instruction="Take shelter indoors immediately. Stay away from trees and power lines.",
            is_simulation=False,
            status="Actual",
            note="OFFICIAL GOVERNMENT WARNING",
            is_expired=False,
            expires=future_time
        )
        db.add(real_alert)
    else:
        existing.is_simulation = False
        existing.status = "Actual"
        existing.note = "OFFICIAL GOVERNMENT WARNING"
        existing.is_expired = False
        existing.expires = future_time
    db.commit()
    db.close()

    resp = client.post("/api/chat/message", json={
        "message": "Is there any active alert in Cuttack?",
        "location": "Cuttack"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "current_alert"
    # MUST NOT be marked as [DRILL] because underlying alert is not a simulation
    assert "[DRILL" not in data["message"]
    assert data["claim_ledger"]["status"] == "PASS"

