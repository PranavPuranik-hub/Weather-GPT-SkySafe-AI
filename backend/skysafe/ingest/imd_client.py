"""
IMD (India Meteorological Department) CAP/RSS Adapter with Resilient Discovery and Graceful Fallback.
"""
import logging
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from skysafe.core.config import settings
from skysafe.ingest.cap_parser import parse_cap_xml

logger = logging.getLogger("skysafe.ingest.imd")


class ImdClient:
    """
    Adapter for IMD CAP warnings feed.
    Designed for secondary redundancy alongside NDMA SACHET.
    """

    def __init__(self, feed_url: str | None = None) -> None:
        self.feed_url = feed_url or settings.IMD_RSS_URL

    def fetch_alerts(self, timeout: float = 5.0) -> list[dict[str, Any]]:
        """
        Fetch alerts from IMD feed. Returns empty list gracefully if unreachable.
        """
        if settings.MODE == "fixtures":
            logger.info("MODE is fixtures; skipping live IMD fetch.")
            return []

        try:
            headers = {"User-Agent": "SkySafe-AI/1.0 (Disaster Action Intelligence)"}
            with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
                resp = client.get(self.feed_url)
                if resp.status_code != 200:
                    logger.info(f"IMD feed returned HTTP {resp.status_code}, skipping.")
                    return []
                xml_text = resp.text
        except Exception as exc:
            logger.info(f"IMD feed unreachable or timed out: {exc}. Continuing with primary source.")
            return []

        alerts: list[dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_text)
            for item in root.iter("item"):
                desc_el = item.find("description")
                content = desc_el.text.strip() if desc_el is not None and desc_el.text else None
                if content and "<alert" in content:
                    parsed = parse_cap_xml(content, source="IMD")
                    if parsed:
                        alerts.append(parsed)
        except Exception as exc:
            logger.warning(f"Error parsing IMD XML feed: {exc}")

        return alerts


# Singleton
imd_client = ImdClient()
