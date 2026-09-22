from app.climate import get_climate_trends


def test_climate_trends():
    trends = get_climate_trends("Cuttack")
    assert trends["district"] == "Cuttack"
    assert "anomaly" in trends
