import pytest
from app.sms.encoder import generate_sms, count_sms_segments
from app.sms.parser import parse_sms_reply
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.models import Report

@pytest.fixture(scope="function")
def db_session():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    yield db
    db.close()

def test_sms_encoder_english_gsm7():
    alert = {
        "severity": "Extreme",
        "event": "Cyclone",
        "district": "Puri",
        "headline": "A very severe cyclonic storm is approaching the coast."
    }
    result = generate_sms(alert, lang="en")
    
    assert not result["is_unicode"]
    assert "SKYSAFE EXTREME CYCLONE PURI" in result["text"]
    assert "1=SAFE 2=HELP" in result["text"]
    assert result["length"] <= 160
    assert result["segments"] == 1

def test_sms_encoder_hindi_unicode():
    alert = {
        "severity": "Extreme",
        "event": "Cyclone",
        "district": "Puri"
    }
    result = generate_sms(alert, lang="hi")
    
    assert result["is_unicode"]
    assert "अत्यंत" in result["text"]
    assert "चक्रवात" in result["text"]
    assert "1=सुरक्षित 2=मदद" in result["text"]
    assert result["segments"] <= 3

def test_sms_encoder_odia_unicode():
    alert = {
        "severity": "Severe",
        "event": "Cyclone",
        "district": "Cuttack"
    }
    result = generate_sms(alert, lang="or")
    
    assert result["is_unicode"]
    assert "ଗମ୍ଭୀର" in result["text"]
    assert "ବାତ୍ୟା" in result["text"]
    assert result["segments"] <= 3

def test_sms_segment_counting():
    # GSM-7
    assert count_sms_segments("A" * 160, is_unicode=False) == 1
    assert count_sms_segments("A" * 161, is_unicode=False) == 2
    
    # UCS-2
    assert count_sms_segments("A" * 70, is_unicode=True) == 1
    assert count_sms_segments("A" * 71, is_unicode=True) == 2

def test_sms_reply_parser_safe(db_session):
    cat = parse_sms_reply("1", "HASH123", "W1", db_session)
    assert cat == "Safe"
    
    report = db_session.query(Report).filter_by(reporter_hash="HASH123").first()
    assert report is not None
    assert report.category == "Safe"

def test_sms_reply_parser_help(db_session):
    cat = parse_sms_reply("2 ", "HASH123", "W1", db_session) # trailing space
    assert cat == "Need Help"
    
    report = db_session.query(Report).filter_by(reporter_hash="HASH123").first()
    assert report is not None
    assert report.category == "Need Help"

def test_sms_reply_parser_water(db_session):
    cat = parse_sms_reply("3", "HASH123", "W1", db_session)
    assert cat == "Water Logging"

def test_sms_reply_parser_invalid(db_session):
    cat = parse_sms_reply("Hello", "HASH123", "W1", db_session)
    assert cat is None
