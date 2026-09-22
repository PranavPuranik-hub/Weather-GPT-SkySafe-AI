"""
Tests for Open-Meteo Typed Client: Caching, Offline Fixtures, and Fallback.
"""
from app.ingest.open_meteo import OpenMeteoClient


def test_open_meteo_offline_fixtures():
    client = OpenMeteoClient()

    forecast = client.get_forecast(20.46, 85.88)
    assert forecast.latitude == 20.46
    assert forecast.longitude == 85.88
    assert "precipitation" in forecast.hourly
    assert "temperature_2m" in forecast.hourly
    assert len(forecast.hourly["time"]) > 0

    marine = client.get_marine(13.08, 80.27)
    assert marine.latitude == 13.08
    assert marine.longitude == 80.27
    assert "wave_height" in marine.hourly
    assert len(marine.hourly["wave_height"]) > 0

    flood = client.get_flood(20.46, 85.88)
    assert "river_discharge" in flood.daily
    assert len(flood.daily["river_discharge"]) > 0

    archive = client.get_archive(20.46, 85.88)
    assert "precipitation_sum" in archive.daily


def test_open_meteo_caching():
    client = OpenMeteoClient()
    # First call fills cache
    res1 = client.get_forecast(20.46, 85.88)
    cache_len1 = len(client._cache)
    assert cache_len1 >= 1

    # Second identical call uses cache
    res2 = client.get_forecast(20.46, 85.88)
    assert len(client._cache) == cache_len1
    assert res1.hourly == res2.hourly
