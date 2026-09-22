import math
from typing import Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from app.models.decision import WardInfo, Shelter
from app.models.reports import WardState, WardStateEnum
from app.models import Alert

# Default Config Weights
WEIGHTS = {
    "alert_severity": 0.20,
    "low_lying": 0.15,
    "population_density": 0.10,
    "vulnerability": 0.15, # elderly + kutcha
    "hospital_distance": 0.05,
    "citizen_reports": 0.20,
    "shelter_gap": 0.15
}

def calculate_ward_risk_score(db: Session, ward_info: WardInfo) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Calculates a 0-100 risk score and returns a ledger of the top contributing factors.
    """
    factors = []
    
    # 1. Alert Severity (0 to 1)
    # Get active alert for district
    alert = db.query(Alert).filter(Alert.is_expired == False).first()
    severity_val = 0.0
    if alert:
        if alert.severity.lower() == "extreme": severity_val = 1.0
        elif alert.severity.lower() == "severe": severity_val = 0.8
        elif alert.severity.lower() == "moderate": severity_val = 0.5
        elif alert.severity.lower() == "minor": severity_val = 0.2
        factors.append({
            "factor": "Alert Severity", 
            "value": alert.severity, 
            "score": severity_val * 100 * WEIGHTS["alert_severity"],
            "source": f"SACHET Alert: {alert.identifier}"
        })

    # 2. Low Lying Score (0 to 1)
    low_lying = ward_info.low_lying_score
    factors.append({
        "factor": "Low Lying Area", 
        "value": f"{low_lying*100}%", 
        "score": low_lying * 100 * WEIGHTS["low_lying"],
        "source": "Ward Demographics DB"
    })

    # 3. Population Density Proxy (0 to 1) (Normalize by 50,000 max pop)
    pop_norm = min(ward_info.population / 50000.0, 1.0)
    factors.append({
        "factor": "Population", 
        "value": str(ward_info.population), 
        "score": pop_norm * 100 * WEIGHTS["population_density"],
        "source": "Census DB"
    })

    # 4. Vulnerability (Elderly + Kutcha) (0 to 1)
    vuln = min(ward_info.elderly_share + ward_info.kutcha_house_share, 1.0)
    factors.append({
        "factor": "Vulnerability (Elderly + Kutcha)", 
        "value": f"{(vuln*100):.1f}%", 
        "score": vuln * 100 * WEIGHTS["vulnerability"],
        "source": "Demographics Survey"
    })

    # 5. Hospital Distance (0 to 1) (Normalize by 20km max)
    hosp_norm = min(ward_info.hospital_distance_km / 20.0, 1.0)
    factors.append({
        "factor": "Hospital Distance", 
        "value": f"{ward_info.hospital_distance_km} km", 
        "score": hosp_norm * 100 * WEIGHTS["hospital_distance"],
        "source": "Health Infra Registry"
    })

    # 6. Citizen Reports (0 to 1) from WardState
    ws = db.query(WardState).filter(WardState.ward_id == ward_info.ward_id).first()
    reports_score = 0.0
    if ws:
        # ground_truth_score starts at 1.0. Max 5.0. Normalize (x - 1.0) / 4.0
        reports_score = min((ws.ground_truth_score - 1.0) / 4.0, 1.0)
    
    reports_val_str = f"Score {ws.ground_truth_score:.1f}" if ws else "None"
    factors.append({
        "factor": "Confirmed Citizen Reports", 
        "value": reports_val_str,
        "score": reports_score * 100 * WEIGHTS["citizen_reports"],
        "source": "Citizen Reporting Cluster Engine"
    })

    # 7. Shelter Capacity Gap (0 to 1)
    shelters = db.query(Shelter).filter(Shelter.ward_id == ward_info.ward_id).all()
    total_cap = sum(s.capacity for s in shelters)
    total_occ = sum(s.current_occupancy for s in shelters)
    available = total_cap - total_occ
    
    # Needs vs Available (Assume 10% of pop needs shelter in extreme event)
    needs = ward_info.population * 0.10
    gap = max(needs - available, 0)
    gap_norm = min(gap / needs if needs > 0 else 0, 1.0)
    
    factors.append({
        "factor": "Shelter Capacity Gap", 
        "value": f"{int(gap)} beds short", 
        "score": gap_norm * 100 * WEIGHTS["shelter_gap"],
        "source": "Real-time Shelter DB"
    })

    # Total Score
    total_score = sum(f["score"] for f in factors)
    
    # Sort factors by contribution
    factors.sort(key=lambda x: x["score"], reverse=True)

    return round(total_score, 1), factors
