"""
Ingestion Service: Deduplication, Expiration Marking, Lag Calculation, and Scenario Simulation.
"""
import logging
import time
from datetime import UTC, datetime, timedelta
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

    def simulate_scenario(self, scenario_name: str, district: str | None = None, db: Session | None = None) -> Alert | None:
        """
        Inject a drill scenario alert into the database with current timestamp.
        Allowed only in fixtures/demo mode.
        """
        fixture_map = {
            # Standard scenario fixtures
            "kerala_flood": "heavy_rain_kerala.xml",
            "heavy_rain_kerala": "heavy_rain_kerala.xml",
            "flood": "heavy_rain_kerala.xml",
            "odisha_cyclone": "cyclone_odisha.xml",
            "cyclone_odisha": "cyclone_odisha.xml",
            "cyclone": "cyclone_odisha.xml",
            "cyclone_t24": "cyclone_odisha.xml",
            "cyclone_t12": "cyclone_odisha.xml",
            "cyclone_t3": "cyclone_odisha.xml",
            "rajasthan_heatwave": "heatwave_rajasthan.xml",
            "heatwave_rajasthan": "heatwave_rajasthan.xml",
            "heatwave": "heatwave_rajasthan.xml",
            "bihar_thunderstorm": "thunderstorm_bihar.xml",
            "thunderstorm_bihar": "thunderstorm_bihar.xml",
            "thunderstorm": "thunderstorm_bihar.xml",
            "tamilnadu_high_wave": "high_wave_tamilnadu.xml",
            "high_wave_tamilnadu": "high_wave_tamilnadu.xml",
            "high_wave": "high_wave_tamilnadu.xml",
            "uttarakhand_landslide": "landslide_uttarakhand.xml",
            "landslide_uttarakhand": "landslide_uttarakhand.xml",
            "landslide": "landslide_uttarakhand.xml",
            "andhra_cyclone": "cyclone_andhra.xml",
            "cyclone_andhra": "cyclone_andhra.xml",
        }

        key = scenario_name.lower().strip()
        filename = fixture_map.get(key)
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
        parsed["expires"] = now + timedelta(days=2)
        parsed["status"] = "Exercise"
        parsed["is_simulation"] = True
        parsed["is_expired"] = False
        parsed["note"] = "DRILL - SIMULATED"

        # Specific scenario step customizations
        if key == "cyclone_t24":
            parsed["event"] = "Cyclonic Storm Watch"
            parsed["severity"] = "Moderate"
            parsed["urgency"] = "Future"
            parsed["certainty"] = "Possible"
            parsed["headline"] = "Yellow Advisory: Cyclonic depression in Bay of Bengal moving towards coast."
            parsed["description"] = "System likely to intensify with wind speeds of 50 km/h and wave heights of 2.0 meters."
        elif key == "cyclone_t12":
            parsed["event"] = "Severe Cyclonic Storm Warning"
            parsed["severity"] = "Severe"
            parsed["urgency"] = "Expected"
            parsed["certainty"] = "Likely"
            parsed["headline"] = "Orange Warning: Severe Cyclone Approaching coast with gale winds."
            parsed["description"] = "Gale winds of 95 km/h gusting to 120 kmph with swell waves of 3.8 meters expected."
        elif key == "cyclone_t3":
            parsed["event"] = "Very Severe Cyclonic Storm"
            parsed["severity"] = "Extreme"
            parsed["urgency"] = "Immediate"
            parsed["certainty"] = "Observed"
            parsed["headline"] = "Red Alert: Landfall Imminent. Very Severe Cyclone Approaching Coast."
            parsed["description"] = "Severe cyclonic storm with sustained winds of 130-155 kmph. Evacuate immediately."

        # District override if specified - ensure geographical state coherence
        KNOWN_DISTRICT_TO_STATE = {
            "nagpur": "Maharashtra",
            "mumbai": "Maharashtra",
            "ratnagiri": "Maharashtra",
            "pune": "Maharashtra",
            "cuttack": "Odisha",
            "puri": "Odisha",
            "bhubaneswar": "Odisha",
            "khordha": "Odisha",
            "ganjam": "Odisha",
            "balasore": "Odisha",
            "wayanad": "Kerala",
            "kozhikode": "Kerala",
            "ernakulam": "Kerala",
            "idukki": "Kerala",
            "munnar": "Kerala",
            "churu": "Rajasthan",
            "bikaner": "Rajasthan",
            "jaipur": "Rajasthan",
            "patna": "Bihar",
            "chennai": "Tamil Nadu",
            "cuddalore": "Tamil Nadu",
            "visakhapatnam": "Andhra Pradesh",
            "uttarkashi": "Uttarakhand",
        }

        if district and district.strip():
            target_dist = district.strip()
            parsed["district"] = target_dist

            dist_key = target_dist.lower()
            if dist_key in KNOWN_DISTRICT_TO_STATE:
                correct_state = KNOWN_DISTRICT_TO_STATE[dist_key]
                old_state = parsed.get("state", "")
                parsed["state"] = correct_state
                parsed["area_desc"] = f"{target_dist}, {correct_state}"

                if old_state and old_state.lower() != correct_state.lower():
                    parsed["headline"] = parsed["headline"].replace(old_state, correct_state)
                    if parsed.get("description"):
                        parsed["description"] = parsed["description"].replace(old_state, correct_state)
            else:
                parsed["area_desc"] = f"{target_dist}, {parsed.get('state', '')}"

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
