import pytest

from app.core.db import Base, SessionLocal, engine
from app.models.reports import Report, WardState, WardStateEnum
from app.reports.service import classify_report_category, submit_report


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Clean up the tables for these tests
    db.query(Report).delete()
    db.query(WardState).delete()
    db.commit()
    try:
        yield db
    finally:
        db.close()


def test_classify_report_category():
    assert classify_report_category("Water entered my home") == "Water Logging"
    assert classify_report_category("There is a tree fallen on the road") == "Tree Down"
    assert classify_report_category("I need help, send a rescue boat") == "Need Help"
    assert classify_report_category("Road is blocked by landslide") == "Road Blocked"
    assert classify_report_category("We are safe now") == "Safe"

def test_spam_prevention(db_session):
    ward_id = "Ward 7"

    # First report
    r1 = submit_report(db_session, "Need help", 20.0, 85.0, "user1", ward_id)
    assert r1.confidence == "Unverified"

    ws = db_session.query(WardState).filter_by(ward_id=ward_id).first()
    assert ws.state == WardStateEnum.REPORTED.value

    # Second report by SAME user (Spam)
    r2 = submit_report(db_session, "Need boat", 20.0, 85.0, "user1", ward_id)
    assert r2.confidence == "Spam"

    # State should remain REPORTED, not CONFIRMED (since count = 1 valid report)
    ws = db_session.query(WardState).filter_by(ward_id=ward_id).first()
    assert ws.state == WardStateEnum.REPORTED.value

def test_clustering_threshold(db_session):
    ward_id = "Ward 8"

    submit_report(db_session, "Tree down", 20.0, 85.0, "u1", ward_id)
    submit_report(db_session, "Tree down", 20.0, 85.0, "u2", ward_id)

    ws = db_session.query(WardState).filter_by(ward_id=ward_id).first()
    assert ws.state == WardStateEnum.REPORTED.value

    # 3rd independent report flips state to Confirmed
    submit_report(db_session, "Tree down", 20.0, 85.0, "u3", ward_id)

    ws = db_session.query(WardState).filter_by(ward_id=ward_id).first()
    assert ws.state == WardStateEnum.CONFIRMED.value
    assert ws.ground_truth_score > 1.0 # Should have incremented
