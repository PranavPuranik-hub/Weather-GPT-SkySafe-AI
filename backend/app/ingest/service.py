"""
Ingestion Service: Deduplication, Expiration Marking, Lag Calculation, and Scenario Simulation.
"""
import logging
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.ingest.cap_parser import parse_cap_xml
from app.ingest.imd_client import imd_client
from app.ingest.sachet_client import sachet_client
from app.models import Alert

logger = logging.getLogger("app.ingest.service")


class IngestService:
    """
    Coordinates ingestion lifecycle across NDMA SACHET and IMD feeds,
    ensuring deduplication, lag measurement, and database persistence.
    """

    def __init__(self) -> None:
        self.last_fetch_latency_ms: float = 0.0
        self.last_ingest_lag_seconds: float | None = None
        self.last_sachet_fetch: str | None = None

    def store_alert(self, db: Session, alert_dict: dict[str, Any]) -> Alert:
        """
        Persist normalized alert dictionary to database with deduplication.
        If alert exists, update fields while preserving existing history.
        """
        identifier = alert_dict.get("identifier") or alert_dict.get("alert_id")
        existing: Alert | None = db.query(Alert).filter(Alert.alert_id == identifier).first()

        now = datetime.now(UTC)
        sent_dt = alert_dict.get("sent")
        lag_seconds: float | None = None
        if sent_dt:
            # Calculate alert-to-ingest lag
            if sent_dt.tzinfo:
                lag_seconds = max(0.0, (now - sent_dt).total_seconds())
            else:
                lag_seconds = max(0.0, (now.replace(tzinfo=None) - sent_dt).total_seconds())

        alert_dict["ingest_lag_seconds"] = lag_seconds
        alert_dict["ingested_at"] = now.replace(tzinfo=None)

        if existing:
            # Update existing alert
            for k, v in alert_dict.items():
                if hasattr(existing, k) and k not in ("id", "created_at"):
                    setattr(existing, k, v)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_alert = Alert(**alert_dict)
            db.add(new_alert)
            db.commit()
            db.refresh(new_alert)
            return new_alert

    def mark_expired_alerts(self, db: Session) -> int:
        """
        Mark alerts whose expiration time has passed as expired.
        """
        now = datetime.utcnow()
        expired_count = (
            db.query(Alert)
            .filter(Alert.is_expired.is_(False), Alert.expires.isnot(None), Alert.expires < now)
            .update({Alert.is_expired: True})
        )
        if expired_count > 0:
            db.commit()
            logger.info(f"Marked {expired_count} alerts as expired.")
        return expired_count

    def ingest_cycle(self, db: Session | None = None) -> list[Alert]:
        """
        Execute full polling and ingestion cycle:
        1. Query primary source (NDMA SACHET / Fixtures)
        2. Query secondary redundancy source (IMD)
        3. Dedupe and persist alerts
        4. Mark expired alerts
        5. Record latency and alert-to-ingest lag
        """
        start_time = time.time()
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        stored_alerts: list[Alert] = []
        try:
            # 1. Primary Source
            fetched_alerts = sachet_client.fetch_feed_alerts()

            # 2. Secondary Redundancy (live mode only)
            if settings.MODE != "fixtures":
                imd_alerts = imd_client.fetch_alerts()
                fetched_alerts.extend(imd_alerts)

            # Dedupe in-memory by identifier
            unique_alerts: dict[str, dict[str, Any]] = {}
            for a in fetched_alerts:
                ident = a.get("identifier") or a.get("alert_id")
                if ident and ident not in unique_alerts:
                    unique_alerts[ident] = a

            # 3. Store into DB
            lags: list[float] = []
            for alert_data in unique_alerts.values():
                alert_obj = self.store_alert(db, alert_data)
                stored_alerts.append(alert_obj)
                if alert_obj.ingest_lag_seconds is not None:
                    lags.append(alert_obj.ingest_lag_seconds)

            # 4. Mark expired
            self.mark_expired_alerts(db)

            # 5. Record operational metrics
            self.last_fetch_latency_ms = (time.time() - start_time) * 1000.0
            self.last_sachet_fetch = datetime.utcnow().isoformat() + "Z"
            if lags:
                self.last_ingest_lag_seconds = sum(lags) / len(lags)

            logger.info(
                f"Ingestion cycle completed: {len(stored_alerts)} alerts stored in "
                f"{self.last_fetch_latency_ms:.1f}ms. Avg lag: {self.last_ingest_lag_seconds}s"
            )
        except Exception as exc:
            logger.error(f"Error during ingestion cycle: {exc}")
        finally:
            if close_session:
                db.close()

        return stored_alerts

    def simulate_scenario(self, scenario_name: str, db: Session | None = None) -> Alert | None:
        """
        Inject a drill scenario alert into the database with current timestamp.
        Allowed only in fixtures/demo mode.
        """
        fixture_map = {
            "kerala_flood": "heavy_rain_kerala.xml",
            "heavy_rain_kerala": "heavy_rain_kerala.xml",
            "odisha_cyclone": "cyclone_odisha.xml",
            "cyclone_odisha": "cyclone_odisha.xml",
            "rajasthan_heatwave": "heatwave_rajasthan.xml",
            "heatwave_rajasthan": "heatwave_rajasthan.xml",
            "bihar_thunderstorm": "thunderstorm_bihar.xml",
            "thunderstorm_bihar": "thunderstorm_bihar.xml",
            "tamilnadu_high_wave": "high_wave_tamilnadu.xml",
            "high_wave_tamilnadu": "high_wave_tamilnadu.xml",
            "uttarakhand_landslide": "landslide_uttarakhand.xml",
            "landslide_uttarakhand": "landslide_uttarakhand.xml",
            "andhra_cyclone": "cyclone_andhra.xml",
            "cyclone_andhra": "cyclone_andhra.xml",
        }

        filename = fixture_map.get(scenario_name.lower())
        if not filename:
            # Attempt to find by matching XML name directly
            target = f"{scenario_name}.xml"
            if (sachet_client.fixtures_dir / target).exists():
                filename = target
            else:
                logger.warning(f"Unknown scenario drill name: {scenario_name}")
                return None

        filepath = sachet_client.fixtures_dir / filename
        if not filepath.exists():
            logger.warning(f"Scenario fixture file not found: {filepath}")
            return None

        xml_content = filepath.read_text(encoding="utf-8")
        parsed = parse_cap_xml(xml_content, source="SIMULATION")
        if not parsed:
            return None

        # Re-stamp with current time as newly received alert
        now = datetime.now(UTC)
        parsed["sent"] = now
        parsed["effective"] = now
        parsed["status"] = "Exercise"
        parsed["is_simulation"] = True
        parsed["note"] = "DRILL - SIMULATED"
        # Generate unique identifier for this simulation instance
        parsed["identifier"] = f"{parsed['identifier']}-SIM-{int(time.time())}"
        parsed["alert_id"] = parsed["identifier"]

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            alert = self.store_alert(db, parsed)
            logger.info(f"Simulated drill alert injected: {alert.alert_id} ({alert.headline})")
            return alert
        finally:
            if close_session:
                db.close()


# Singleton
ingest_service = IngestService()
