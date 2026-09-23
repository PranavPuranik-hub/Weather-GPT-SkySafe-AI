"""
NDMA SACHET RSS Feed and CAP XML Fetcher with Retry Backoff and Offline Fixtures.
"""
import logging
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.ingest.cap_parser import parse_cap_xml

logger = logging.getLogger("app.ingest.sachet")


class SachetClient:
    """
    Client for fetching and parsing alerts from NDMA SACHET CAP RSS feeds.
    Supports offline fixtures mode and network retry with exponential backoff.
    """

    def __init__(self, feed_url: str | None = None, fixtures_dir: str | None = None) -> None:
        self.feed_url = feed_url or settings.SACHET_RSS_URL
        if fixtures_dir:
            self.fixtures_dir = Path(fixtures_dir)
        else:
            candidates = [
                Path("/data/fixtures/cap"),
                Path("/app/data/fixtures/cap"),
                Path(__file__).resolve().parents[3] / "data" / "fixtures" / "cap",
                Path(__file__).resolve().parents[2] / "data" / "fixtures" / "cap",
                Path(settings.DATA_DIR) / "fixtures" / "cap",
            ]
            self.fixtures_dir = next((p for p in candidates if p.exists()), candidates[0])

    def load_offline_fixtures(self) -> list[dict[str, Any]]:
        """
        Load all CAP 1.2 XML files from the fixtures directory.
        Used when MODE=fixtures or during network fallback.
        """
        alerts: list[dict[str, Any]] = []
        if not self.fixtures_dir.exists():
            logger.warning(f"Fixtures directory does not exist: {self.fixtures_dir}")
            return alerts

        xml_files = sorted(self.fixtures_dir.glob("*.xml"))
        now = datetime.now(UTC)
        for xml_file in xml_files:
            try:
                content = xml_file.read_text(encoding="utf-8")
                parsed = parse_cap_xml(content, source="FIXTURES")
                if parsed:
                    # Active scenario fixtures (non-expired files) must remain active for testing and demos
                    if not xml_file.name.startswith("expired_"):
                        parsed["is_expired"] = False
                        if parsed.get("expires"):
                            exp = parsed["expires"]
                            if exp.tzinfo is None:
                                exp = exp.replace(tzinfo=UTC)
                            if exp <= now:
                                parsed["expires"] = (now + timedelta(days=7)).replace(tzinfo=None)
                    alerts.append(parsed)
            except Exception as exc:
                logger.warning(f"Error reading fixture file {xml_file}: {exc}")
        logger.info(f"Loaded {len(alerts)} alerts from offline fixtures.")
        return alerts

    def _fetch_with_retry(self, url: str, max_retries: int = 2, timeout: float = 6.0) -> str | None:
        """Fetch URL content with exponential backoff."""
        delay = 1.0
        for attempt in range(max_retries + 1):
            try:
                headers = {"User-Agent": "SkySafe-AI/1.0 (Disaster Action Intelligence)"}
                with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
                    resp = client.get(url)
                    if resp.status_code == 200:
                        return resp.text
                    logger.warning(f"HTTP {resp.status_code} fetching {url}")
            except Exception as exc:
                logger.warning(f"Attempt {attempt+1} failed for {url}: {exc}")
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2.0
        return None

    def fetch_feed_alerts(self) -> list[dict[str, Any]]:
        """
        Fetch and parse latest CAP alerts. In fixtures mode, reads from local directory.
        """
        if settings.MODE == "fixtures":
            return self.load_offline_fixtures()

        rss_xml = self._fetch_with_retry(self.feed_url)
        if not rss_xml:
            logger.warning("Failed to retrieve SACHET RSS feed. Falling back to fixtures.")
            return self.load_offline_fixtures()

        cap_urls: list[str] = []
        try:
            root = ET.fromstring(rss_xml)
            # Find item links
            for item in root.iter("item"):
                link_el = item.find("link")
                guid_el = item.find("guid")
                url = None
                if link_el is not None and link_el.text:
                    url = link_el.text.strip()
                elif guid_el is not None and guid_el.text:
                    url = guid_el.text.strip()
                if url and (url.endswith(".xml") or "cap" in url.lower()):
                    cap_urls.append(url)
        except Exception as exc:
            logger.warning(f"Failed to parse SACHET RSS XML: {exc}")

        if not cap_urls:
            logger.warning("No CAP items found in RSS feed. Falling back to fixtures.")
            return self.load_offline_fixtures()

        parsed_alerts: list[dict[str, Any]] = []
        for url in cap_urls[:15]:  # Limit to 15 recent alerts per cycle
            cap_xml = self._fetch_with_retry(url)
            if cap_xml:
                parsed = parse_cap_xml(cap_xml, source="SACHET")
                if parsed:
                    parsed_alerts.append(parsed)

        return parsed_alerts if parsed_alerts else self.load_offline_fixtures()


# Singleton
sachet_client = SachetClient()
