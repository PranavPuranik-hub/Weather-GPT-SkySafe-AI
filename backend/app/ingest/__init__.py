"""
Ingest package: Data fetching and parsing for SACHET (CAP format) and Open-Meteo APIs.
"""
from app.ingest.cap_parser import parse_cap_xml
from app.ingest.imd_client import ImdClient, imd_client
from app.ingest.open_meteo import OpenMeteoClient, open_meteo_client
from app.ingest.sachet_client import SachetClient, sachet_client
from app.ingest.scheduler import start_ingest_scheduler, stop_ingest_scheduler
from app.ingest.service import IngestService, ingest_service


def fetch_sachet_alerts():
    """Fetch SACHET CAP alerts via sachet_client."""
    return sachet_client.fetch_feed_alerts()


def fetch_open_meteo_forecast(lat: float, lon: float):
    """Fetch Open-Meteo forecast via open_meteo_client."""
    resp = open_meteo_client.get_forecast(lat, lon)
    return resp.model_dump()


__all__ = [
    "ImdClient",
    "IngestService",
    "OpenMeteoClient",
    "SachetClient",
    "fetch_open_meteo_forecast",
    "fetch_sachet_alerts",
    "imd_client",
    "ingest_service",
    "open_meteo_client",
    "parse_cap_xml",
    "sachet_client",
    "start_ingest_scheduler",
    "stop_ingest_scheduler",
]
