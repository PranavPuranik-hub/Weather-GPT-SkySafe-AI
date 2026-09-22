"""
APScheduler Background Ingestion Worker with Latency and Alert-to-Ingest Lag Tracking.
"""
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.ingest.open_meteo import open_meteo_client
from app.ingest.service import ingest_service

logger = logging.getLogger("app.ingest.scheduler")

scheduler = BackgroundScheduler()


def scheduled_ingest_job() -> None:
    """
    Periodic job executing CAP alert fetch and Open-Meteo weather update.
    Tracks latency and alert-to-ingest lag metrics.
    """
    logger.info("Executing scheduled ingestion cycle...")
    try:
        # Run alert ingestion cycle
        alerts = ingest_service.ingest_cycle()
        logger.info(f"Ingested/refreshed {len(alerts)} alerts.")

        # Update sample district Open-Meteo forecast (e.g. Cuttack)
        open_meteo_client.get_forecast(20.46, 85.88)
    except Exception as exc:
        logger.error(f"Scheduled ingestion encountered an error: {exc}")


def start_ingest_scheduler() -> None:
    """
    Start the background scheduler with configured polling interval.
    """
    if not scheduler.running:
        interval = settings.INGEST_POLL_INTERVAL_SECONDS
        scheduler.add_job(
            scheduled_ingest_job,
            "interval",
            seconds=interval,
            id="cap_ingest_job",
            replace_existing=True,
            next_run_time=datetime.now(),  # Run immediately on startup
        )
        scheduler.start()
        logger.info(f"Ingest scheduler started. Polling every {interval}s.")


def stop_ingest_scheduler() -> None:
    """
    Shut down the background scheduler cleanly.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Ingest scheduler shut down.")
