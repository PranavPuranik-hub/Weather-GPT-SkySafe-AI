"""
Tests for CAP 1.2 XML parsing, geometry extraction, and malformed input tolerance.
"""
import json
from pathlib import Path

from app.ingest.cap_parser import _extract_polygon_geojson, parse_cap_xml


def test_parse_valid_kerala_fixture():
    fixture_path = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "cap" / "heavy_rain_kerala.xml"
    assert fixture_path.exists(), f"Fixture missing: {fixture_path}"
    content = fixture_path.read_text(encoding="utf-8")

    alert = parse_cap_xml(content, source="SACHET")
    assert alert is not None
    assert alert["identifier"] == "SACHET-2026-KL-001"
    assert alert["status"] == "Exercise"
    assert alert["is_simulation"] is True
    assert alert["note"] == "DRILL - SIMULATED"
    assert alert["severity"] == "Severe"
    assert alert["state"] == "Kerala"
    assert alert["district"] == "Wayanad"
    assert "Wayanad" in alert["headline"]

    # Verify GeoJSON polygon
    assert alert["geometry"] is not None
    geom = json.loads(alert["geometry"])
    assert geom["type"] == "Polygon"
    assert len(geom["coordinates"][0]) >= 4
    # Ensure coordinates are [lon, lat]
    first_coord = geom["coordinates"][0][0]
    assert 75.0 <= first_coord[0] <= 78.0  # longitude
    assert 10.0 <= first_coord[1] <= 13.0  # latitude


def test_parse_malformed_xml_resilience():
    # Never crash on malformed or empty XML
    assert parse_cap_xml("") is None
    assert parse_cap_xml("   ") is None
    assert parse_cap_xml("<broken><xml>") is None
    assert parse_cap_xml("<not_alert><item>Data</item></not_alert>") is None
    assert parse_cap_xml("<alert><missing_identifier>val</missing_identifier></alert>") is None


def test_polygon_to_geojson_conversion():
    poly_str = "20.35,85.75 20.60,85.80 20.55,86.10 20.30,86.00 20.35,85.75"
    geojson = _extract_polygon_geojson(poly_str)
    assert geojson is not None
    assert geojson["type"] == "Polygon"
    coords = geojson["coordinates"][0]
    # Check ring is closed
    assert coords[0] == coords[-1]
    # First point check [lon, lat]
    assert coords[0] == [85.75, 20.35]

    # Invalid polygon returns None
    assert _extract_polygon_geojson("") is None
    assert _extract_polygon_geojson("invalid") is None
