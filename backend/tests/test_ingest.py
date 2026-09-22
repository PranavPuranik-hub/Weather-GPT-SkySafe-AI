from app.ingest import fetch_open_meteo_forecast, fetch_sachet_alerts


def test_ingest_functions():
    alerts = fetch_sachet_alerts()
    assert isinstance(alerts, list)

    forecast = fetch_open_meteo_forecast(20.46, 85.88)
    assert isinstance(forecast, dict)
