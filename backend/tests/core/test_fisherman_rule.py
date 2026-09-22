"""
Unit tests for Fisherman SAFE/UNSAFE rule threshold flip.
"""
from app.core.factsheet import build_factsheet
from app.core.rule_engine import rule_engine


def test_fisherman_threshold_unsafe_wave():
    alert = {
        "identifier": "FISH-001",
        "event": "High Waves",
        "description": "Wave height reaching 3.0 meters in coastal waters.",
    }
    fs = build_factsheet(alert)
    is_unsafe, wave_id, wind_id = rule_engine.evaluate_fisherman_threshold(fs)
    assert is_unsafe is True
    assert wave_id is not None


def test_fisherman_threshold_unsafe_wind():
    alert = {
        "identifier": "FISH-002",
        "event": "Gale Wind Alert",
        "description": "Squally winds reaching 50 km/h expected off coast.",
    }
    fs = build_factsheet(alert)
    is_unsafe, wave_id, wind_id = rule_engine.evaluate_fisherman_threshold(fs)
    assert is_unsafe is True
    assert wind_id is not None


def test_fisherman_threshold_safe():
    alert = {
        "identifier": "FISH-003",
        "event": "Light Breeze Advisory",
        "description": "Mild winds of 15 km/h with calm wave height of 1.0 meter.",
    }
    fs = build_factsheet(alert)
    is_unsafe, wave_id, wind_id = rule_engine.evaluate_fisherman_threshold(fs)
    assert is_unsafe is False
