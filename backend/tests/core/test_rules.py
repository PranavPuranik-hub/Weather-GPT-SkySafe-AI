"""
Unit tests for RuleEngine verifying YAML rules across all hazards, grades, and personas.
"""
import pytest
from app.core.factsheet import FactSheet, build_factsheet
from app.core.rule_engine import RuleEngine, normalize_hazard, rule_engine


HAZARDS = [
    "cyclone",
    "heavy_rain_flood",
    "heatwave",
    "thunderstorm_lightning",
    "storm_surge_high_waves",
]
GRADES = ["A", "B", "C", "D"]
PERSONAS = ["general", "farmer", "fisherman", "elderly_alone", "pregnant_infants"]


def test_normalize_hazard():
    assert normalize_hazard("Heavy Rain/Flood") == "heavy_rain_flood"
    assert normalize_hazard("Thunderstorm/Lightning") == "thunderstorm_lightning"
    assert normalize_hazard("Storm Surge/High Waves") == "storm_surge_high_waves"
    assert normalize_hazard("Cyclone") == "cyclone"


@pytest.mark.parametrize("hazard", HAZARDS)
@pytest.mark.parametrize("grade", GRADES)
@pytest.mark.parametrize("persona", PERSONAS)
def test_all_hazards_grades_personas_actions(hazard, grade, persona):
    alert = {
        "identifier": "TEST-RULE-001",
        "event": hazard,
        "severity": "Extreme" if grade == "A" else "Moderate",
        "district": "TestDistrict",
        "state": "TestState",
        "description": "Wind speeds of 90 km/h and wave heights of 3.0 m expected.",
    }
    fs = build_factsheet(alert)
    actions, why = rule_engine.get_actions(
        hazard=hazard,
        grade=grade,
        persona=persona,
        factsheet=fs,
    )

    # 1. Must return 2 to 4 actions
    assert 2 <= len(actions) <= 4, f"Hazard {hazard}, Grade {grade}, Persona {persona} returned {len(actions)} actions"

    # 2. Must contain zero unresolved placeholders like {field}
    for act in actions:
        text = act["action"]
        assert "{" not in text and "}" not in text, f"Unresolved placeholder in action: '{text}'"

    # 3. Why list must be a list of fact IDs
    assert isinstance(why, list)
