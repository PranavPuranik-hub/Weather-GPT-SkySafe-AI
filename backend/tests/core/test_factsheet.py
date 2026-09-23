"""
Unit tests for FactSheet builder and regex fact extraction.
"""
from app.core.factsheet import FactSheet, _extract_text_facts, build_factsheet


def test_build_factsheet_basic():
    alert = {
        "identifier": "TEST-ALERT-001",
        "event": "Cyclonic Storm",
        "severity": "Severe",
        "urgency": "Immediate",
        "certainty": "Observed",
        "district": "Ganjam",
        "state": "Odisha",
    }
    fs = build_factsheet(alert)
    assert len(fs.facts) >= 5
    assert fs.facts[0].id == "F1"
    assert fs.facts[1].id == "F2"
    assert fs.get_value("event") == "Cyclonic Storm"
    assert fs.get_value("severity") == "Severe"
    assert fs.get_value("area") == "Ganjam, Odisha"


def test_regex_fact_extraction():
    text = (
        "Gale winds of 95 km/h gusting to 120 kmph with high swell waves of 3.8 meters expected. "
        "Extremely heavy rainfall of 204 mm is likely."
    )
    extracted = _extract_text_facts(text, "CAP Description", "ALERT-123")

    fields = [item["field"] for item in extracted]
    assert "wind_speed_kmh" in fields or "wind_gust_kmh" in fields
    assert "wave_height_m" in fields
    assert "rainfall_mm" in fields

    for item in extracted:
        assert item["source_span"] is not None
        start, end = item["source_span"]
        assert 0 <= start < end <= len(text)


def test_factsheet_open_meteo_integration():
    alert = {
        "identifier": "TEST-ALERT-002",
        "event": "Heavy Rain",
        "severity": "Moderate",
    }
    open_meteo = {
        "hourly": {
            "wind_speed_10m": [30.0, 45.0, 50.0],
            "precipitation": [10.0, 25.0, 15.0],
            "temperature_2m": [28.0, 32.0, 30.0],
            "wave_height": [1.5, 2.8],
        }
    }
    fs = build_factsheet(alert, open_meteo_data=open_meteo)
    assert fs.get_value("wind_speed_kmh") == 50.0
    assert fs.get_value("rainfall_mm") == 50.0
    assert fs.get_value("temperature_c") == 32.0
    assert fs.get_value("wave_height_m") == 2.8


def test_factsheet_get_value_default():
    fs = FactSheet(facts=[])
    assert fs.get_value("nonexistent", "default_val") == "default_val"
