"""
Open-Meteo API Typed Client with 15-Minute Caching, Offline Fixtures, and Fallback Resilience.
"""
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger("app.ingest.open_meteo")

CACHE_TTL_SECONDS = 15 * 60  # 15 minutes


class OpenMeteoCacheEntry(BaseModel):
    data: dict[str, Any]
    timestamp: float


class ForecastResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str = "Asia/Kolkata"
    hourly: dict[str, Any] = Field(default_factory=dict)
    daily: dict[str, Any] | None = None


class MarineResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str = "Asia/Kolkata"
    hourly: dict[str, Any] = Field(default_factory=dict)


class FloodResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str = "Asia/Kolkata"
    daily: dict[str, Any] = Field(default_factory=dict)


class ArchiveResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str = "Asia/Kolkata"
    daily: dict[str, Any] = Field(default_factory=dict)


class OpenMeteoClient:
    """
    Typed client for Open-Meteo APIs (Forecast, Marine, Flood, Archive).
    Includes in-memory TTL caching and cached-response fallback.
    """

    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
    FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self, fixtures_dir: str | None = None) -> None:
        self._cache: dict[str, OpenMeteoCacheEntry] = {}
        if fixtures_dir:
            self.fixtures_dir = Path(fixtures_dir)
        else:
            candidates = [
                Path("/data/fixtures/open_meteo"),
                Path("/app/data/fixtures/open_meteo"),
                Path(__file__).resolve().parents[3] / "data" / "fixtures" / "open_meteo",
                Path(__file__).resolve().parents[2] / "data" / "fixtures" / "open_meteo",
                Path(settings.DATA_DIR) / "fixtures" / "open_meteo",
            ]
            self.fixtures_dir = next((p for p in candidates if p.exists()), candidates[0])

    def _get_cache_key(self, endpoint: str, params: dict[str, Any]) -> str:
        """Create canonical cache key from endpoint and sorted parameters."""
        sorted_params = sorted((k, str(v)) for k, v in params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        return f"{endpoint}?{param_str}"

    def _load_fixture(self, name: str) -> dict[str, Any]:
        """Load fixture JSON file from disk."""
        path = self.fixtures_dir / f"{name}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        logger.warning(f"Fixture not found at {path}, returning empty dict.")
        return {}

    def _fetch_with_cache(
        self, endpoint: str, params: dict[str, Any], fixture_name: str, timeout: float = 8.0
    ) -> dict[str, Any]:
        """
        Execute request with in-memory 15-min cache and network fallback.
        In fixtures mode, strictly returns offline fixture data.
        """
        cache_key = self._get_cache_key(endpoint, params)
        now = time.time()

        # Offline fixtures mode
        if settings.MODE == "fixtures":
            fixture_data = self._load_fixture(fixture_name)
            self._cache[cache_key] = OpenMeteoCacheEntry(data=fixture_data, timestamp=now)
            return fixture_data

        # Check valid in-memory cache
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if now - entry.timestamp < CACHE_TTL_SECONDS:
                return entry.data

        # Attempt live API call
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(endpoint, params=params)
                response.raise_for_status()
                data = response.json()
                self._cache[cache_key] = OpenMeteoCacheEntry(data=data, timestamp=now)
                return data
        except Exception as exc:
            logger.warning(f"Open-Meteo live request failed ({endpoint}): {exc}")
            # Fallback to stale cache if present
            if cache_key in self._cache:
                logger.info(f"Serving stale cached response for {cache_key}")
                return self._cache[cache_key].data
            # Fallback to offline fixture as safety net
            logger.info(f"Serving offline fixture fallback for {fixture_name}")
            fallback_data = self._load_fixture(fixture_name)
            if fallback_data:
                self._cache[cache_key] = OpenMeteoCacheEntry(data=fallback_data, timestamp=now)
                return fallback_data
            return {}

    def get_forecast(self, lat: float, lon: float) -> ForecastResponse:
        """
        Fetch hourly and daily weather forecast data.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "precipitation,precipitation_probability,wind_speed_10m,wind_gusts_10m,temperature_2m",
            "daily": "precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max",
            "timezone": "Asia/Kolkata",
        }
        data = self._fetch_with_cache(self.FORECAST_URL, params, "forecast")
        return ForecastResponse(**data) if data else ForecastResponse(latitude=lat, longitude=lon)

    def get_marine(self, lat: float, lon: float) -> MarineResponse:
        """
        Fetch hourly marine wave and sea surface conditions.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "wave_height,wave_period,wind_wave_height",
            "timezone": "Asia/Kolkata",
        }
        data = self._fetch_with_cache(self.MARINE_URL, params, "marine")
        return MarineResponse(**data) if data else MarineResponse(latitude=lat, longitude=lon)

    def get_flood(self, lat: float, lon: float) -> FloodResponse:
        """
        Fetch river discharge daily hydro data.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "river_discharge",
            "timezone": "Asia/Kolkata",
        }
        data = self._fetch_with_cache(self.FLOOD_URL, params, "flood")
        return FloodResponse(**data) if data else FloodResponse(latitude=lat, longitude=lon)

    def get_archive(
        self, lat: float, lon: float, start_date: str = "2021-01-01", end_date: str = "2025-12-31"
    ) -> ArchiveResponse:
        """
        Fetch historical climate archive data.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "Asia/Kolkata",
        }
        data = self._fetch_with_cache(self.ARCHIVE_URL, params, "archive")
        return ArchiveResponse(**data) if data else ArchiveResponse(latitude=lat, longitude=lon)


# Default singleton instance
open_meteo_client = OpenMeteoClient()
