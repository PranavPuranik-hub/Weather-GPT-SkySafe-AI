import pytest
from app.core.db import Base, engine, SessionLocal
from app.decision.scoring import calculate_ward_risk_score
from app.decision.optimizer import optimize_resources
from app.models.decision import WardInfo, Depot, Resource, Shelter
from app.models.reports import WardState

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="function")
def db_session():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    db.query(Shelter).delete()
    db.query(Resource).delete()
    db.query(Depot).delete()
    db.query(WardState).delete()
    db.query(WardInfo).delete()
    db.commit()
    
    # Add dummy data
    d = Depot(name="Test Depot", lat=20.0, lon=85.0)
    db.add(d)
    db.commit()
    db.refresh(d)
    
    db.add(Resource(depot_id=d.id, type="Relief Kits", total_qty=100, available_qty=100))
    
    w1 = WardInfo(ward_id="W1", name="Low Risk", population=1000, elderly_share=0.1, kutcha_house_share=0.1, low_lying_score=0.1, hospital_distance_km=1.0, lat=20.01, lon=85.01)
    w2 = WardInfo(ward_id="W2", name="High Risk", population=10000, elderly_share=0.3, kutcha_house_share=0.8, low_lying_score=0.9, hospital_distance_km=15.0, lat=20.02, lon=85.02)
    
    db.add_all([w1, w2])
    db.commit()
    
    # Let's add a dummy alert, shelter, and ward state for W2 to fully test the ledger and optimizer
    alert = Alert(
        alert_id="TEST-ALERT",
        identifier="TEST-ALERT",
        district="Test District",
        severity="Severe",
        headline="Test Headline"
    )
    db.add(alert)
    
    shelter = Shelter(ward_id="W2", name="W2 Shelter", lat=20.0, lon=85.0, capacity=200, current_occupancy=50)
    db.add(shelter)
    
    ws = WardState(ward_id="W2", state="Confirmed", ground_truth_score=3.0)
    db.add(ws)
    db.commit()
    
    try:
        yield db
    finally:
        db.close()

from app.decision.scoring import WEIGHTS
from app.models import Alert

def test_risk_score_calculation(db_session):
    # Retrieve mock wards
    w2 = db_session.query(WardInfo).filter_by(ward_id="W2").first()
    
    # 1. INDEPENDENT CALCULATION
    # Alert Severity: "Severe" -> 0.8
    expected_alert_score = 0.8 * 100 * WEIGHTS["alert_severity"]
    
    # Low Lying
    expected_low_lying = 0.9 * 100 * WEIGHTS["low_lying"]
    
    # Population Density: min(10000 / 50000.0, 1.0) = 0.2
    expected_pop = 0.2 * 100 * WEIGHTS["population_density"]
    
    # Vulnerability: min(0.3 + 0.8, 1.0) = 1.0
    expected_vuln = 1.0 * 100 * WEIGHTS["vulnerability"]
    
    # Hospital Distance: min(15.0 / 20.0, 1.0) = 0.75
    expected_hosp = 0.75 * 100 * WEIGHTS["hospital_distance"]
    
    # Citizen Reports: score=3.0 -> min((3.0 - 1.0) / 4.0, 1.0) = 0.5
    expected_reports = 0.5 * 100 * WEIGHTS["citizen_reports"]
    
    # Shelter Gap:
    # Needs = 10000 * 0.1 = 1000
    # Available = 200 - 50 = 150
    # Gap = 1000 - 150 = 850
    # Gap norm = min(850 / 1000, 1.0) = 0.85
    expected_shelter = 0.85 * 100 * WEIGHTS["shelter_gap"]
    
    expected_total = round(
        expected_alert_score + expected_low_lying + expected_pop + expected_vuln + 
        expected_hosp + expected_reports + expected_shelter, 
        1
    )
    
    # 2. RUN APPLICATION CALCULATION
    app_total, factors = calculate_ward_risk_score(db_session, w2)
    
    # Convert list of dicts to dict for easy lookup
    factor_dict = {f["factor"]: f for f in factors}
    
    # 3. ASSERT INDIVIDUAL FACTORS MATCH EXACTLY
    assert factor_dict["Alert Severity"]["score"] == pytest.approx(expected_alert_score)
    assert factor_dict["Alert Severity"]["source"] == "SACHET Alert: TEST-ALERT"
    
    assert factor_dict["Low Lying Area"]["score"] == pytest.approx(expected_low_lying)
    assert factor_dict["Low Lying Area"]["source"] == "Ward Demographics DB"
    
    assert factor_dict["Population"]["score"] == pytest.approx(expected_pop)
    assert factor_dict["Population"]["source"] == "Census DB"
    
    assert factor_dict["Vulnerability (Elderly + Kutcha)"]["score"] == pytest.approx(expected_vuln)
    assert factor_dict["Vulnerability (Elderly + Kutcha)"]["source"] == "Demographics Survey"
    
    assert factor_dict["Hospital Distance"]["score"] == pytest.approx(expected_hosp)
    assert factor_dict["Hospital Distance"]["source"] == "Health Infra Registry"
    
    assert factor_dict["Confirmed Citizen Reports"]["score"] == pytest.approx(expected_reports)
    assert factor_dict["Confirmed Citizen Reports"]["source"] == "Citizen Reporting Cluster Engine"
    
    assert factor_dict["Shelter Capacity Gap"]["score"] == pytest.approx(expected_shelter)
    assert factor_dict["Shelter Capacity Gap"]["source"] == "Real-time Shelter DB"
    
    # 4. ASSERT TOTAL SCORE MATCHES EXACTLY
    assert app_total == expected_total

def test_resource_optimizer(db_session):
    allocations = optimize_resources(db_session)
    
    # High Risk ward should get resources
    assert len(allocations) > 0
    assert allocations[0]["ward_id"] == "W2"
    assert "Relief Kits" in allocations[0]["resource_type"]
    assert allocations[0]["qty"] > 0
