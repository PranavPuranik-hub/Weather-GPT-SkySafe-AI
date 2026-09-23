from app.chat.tools import get_forecast, get_marine


def test_get_forecast_live_or_fixture_success():
    # Should not raise any exceptions and should not use Climatological fallback when system is healthy
    res = get_forecast({"district": "Puri", "lat": 19.8, "lon": 85.8})
    assert "error" not in res
    sources = [f["source"] for f in res["facts"]]
    assert any("Open-Meteo Forecast" in s for s in sources), "Expected Open-Meteo source when healthy"

def test_get_forecast_total_failure_fallback(monkeypatch):
    # Force a total failure in the fetch wrapper
    def mock_fail(*args, **kwargs):
        raise RuntimeError("Simulated network/system failure")

    import app.chat.tools
    monkeypatch.setattr(app.chat.tools, "fetch_open_meteo_forecast", mock_fail)

    res = get_forecast({"district": "Cuttack"})
    assert "error" in res
    assert res["error"] == "Simulated network/system failure"
    sources = [f["source"] for f in res["facts"]]
    assert any("Climatological Forecast Fallback" in s for s in sources), "Expected Climatological fallback on total failure"

def test_get_marine_success():
    res = get_marine({"district": "Puri", "lat": 19.8, "lon": 85.8})
    sources = [f["source"] for f in res["facts"]]
    assert any("Marine Weather Observation" in s for s in sources)

def test_get_marine_total_failure(monkeypatch):
    def mock_fail(*args, **kwargs):
        raise ValueError("Marine failed")

    # We patch the client since get_marine calls open_meteo_client directly (with .model_dump())
    import app.chat.tools
    class MockClient:
        def get_marine(self, *args, **kwargs):
            raise ValueError("Marine failed")

    monkeypatch.setattr(app.chat.tools, "open_meteo_client", MockClient())

    res = get_marine({"district": "Puri"})
    sources = [f["source"] for f in res["facts"]]
    assert any("Marine Observation Fallback" in s for s in sources)
