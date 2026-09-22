"""
Tests for Ingestion Service: Deduplication, Expiration, and Fixtures Ingestion.
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from skysafe.core.db import Base
from skysafe.ingest.sachet_client import sachet_client
from skysafe.ingest.service import IngestService
from skysafe.models import Alert


def setup_test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def test_load_offline_fixtures():
    fixtures = sachet_client.load_offline_fixtures()
    # At least 8 realistic fixtures required
    assert len(fixtures) >= 8
    # Verify each fixture is marked as exercise / simulation
    for f in fixtures:
        assert f["is_simulation"] is True
        assert f["status"] == "Exercise"
        assert f["note"] == "DRILL - SIMULATED"


def test_deduplication():
    db = setup_test_db()
    service = IngestService()

    alert_data = {
        "alert_id": "TEST-DEDUPE-001",
        "headline": "First Version of Warning",
        "severity": "Moderate",
        "district": "Cuttack",
        "sent": datetime.now(UTC),
    }

    # Store first time
    alert_1 = service.store_alert(db, alert_data)
    assert alert_1.id is not None
    count_1 = db.query(Alert).filter(Alert.alert_id == "TEST-DEDUPE-001").count()
    assert count_1 == 1

    # Store second time with updated headline
    alert_data["headline"] = "Updated Headline for Same Alert"
    alert_data["severity"] = "Severe"
    alert_2 = service.store_alert(db, alert_data)

    # Should update existing record, not create duplicate
    assert alert_2.id == alert_1.id
    count_2 = db.query(Alert).filter(Alert.alert_id == "TEST-DEDUPE-001").count()
    assert count_2 == 1

    updated = db.query(Alert).filter(Alert.alert_id == "TEST-DEDUPE-001").first()
    assert updated.headline == "Updated Headline for Same Alert"
    assert updated.severity == "Severe"


def test_expiration_marking():
    db = setup_test_db()
    service = IngestService()

    now = datetime.utcnow()
    past_date = now - timedelta(hours=2)
    future_date = now + timedelta(hours=2)

    # Past alert (should be marked expired)
    service.store_alert(
        db,
        {
            "alert_id": "TEST-EXP-001",
            "headline": "Expired Alert",
            "severity": "Minor",
            "district": "Wayanad",
            "expires": past_date,
            "is_expired": False,
        },
    )

    # Future alert (should remain active)
    service.store_alert(
        db,
        {
            "alert_id": "TEST-ACT-002",
            "headline": "Active Alert",
            "severity": "Extreme",
            "district": "Cuttack",
            "expires": future_date,
            "is_expired": False,
        },
    )

    expired_count = service.mark_expired_alerts(db)
    assert expired_count == 1

    exp_alert = db.query(Alert).filter(Alert.alert_id == "TEST-EXP-001").first()
    assert exp_alert.is_expired is True

    act_alert = db.query(Alert).filter(Alert.alert_id == "TEST-ACT-002").first()
    assert act_alert.is_expired is False
