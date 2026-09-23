"""
Eval metrics: all values derived from DB queries. No hardcoded numbers.
"""
import statistics
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from app.models import Alert
from app.models.reports import Report, WardState, WardStateEnum
from app.models.eval import ChatEvent


def latency_stats(db: Session) -> Dict[str, Any]:
    """p50 and p95 of alert ingest lag from DB."""
    lags = [
        row.ingest_lag_seconds
        for row in db.query(Alert.ingest_lag_seconds).filter(
            Alert.ingest_lag_seconds.isnot(None)
        ).all()
    ]
    if not lags:
        return {"p50_seconds": None, "p95_seconds": None, "source": "alerts.ingest_lag_seconds"}
    lags_sorted = sorted(lags)
    p50 = statistics.median(lags_sorted)
    idx_p95 = max(0, int(len(lags_sorted) * 0.95) - 1)
    p95 = lags_sorted[idx_p95]
    return {
        "p50_seconds": round(p50, 2),
        "p95_seconds": round(p95, 2),
        "source": "alerts.ingest_lag_seconds"
    }


def alert_counts(db: Session) -> Dict[str, int]:
    """Total, active, expired, simulation alert counts from DB."""
    total = db.query(Alert).count()
    active = db.query(Alert).filter(Alert.is_expired == False).count()
    expired = db.query(Alert).filter(Alert.is_expired == True).count()
    simulated = db.query(Alert).filter(Alert.is_simulation == True).count()
    return {
        "total": total,
        "active": active,
        "expired": expired,
        "simulated": simulated,
        "source": "alerts table"
    }


def llm_path_breakdown(db: Session) -> Dict[str, Any]:
    """Breakdown of LLM paths from chat_events table."""
    try:
        events = db.query(ChatEvent).all()
        counts: Dict[str, int] = {}
        for ev in events:
            counts[ev.path_used] = counts.get(ev.path_used, 0) + 1
        total = sum(counts.values())
        return {
            "total_events": total,
            "breakdown": counts,
            "source": "chat_events.path_used"
        }
    except Exception:
        return {"total_events": 0, "breakdown": {}, "source": "chat_events.path_used"}


def language_coverage(db: Session) -> Dict[str, Any]:
    """Distinct languages seen across alerts and chat events."""
    alert_langs = [r[0] for r in db.query(Alert.language).distinct().all() if r[0]]
    try:
        event_langs = [r[0] for r in db.query(ChatEvent.lang).distinct().all() if r[0]]
    except Exception:
        event_langs = []
    all_langs = list(set(alert_langs + event_langs))
    return {"languages": sorted(all_langs), "count": len(all_langs), "source": "alerts.language + chat_events.lang"}


def report_confirmation_latency(db: Session) -> Dict[str, Any]:
    """Average time from first report to ward confirmation."""
    confirmed_wards = db.query(WardState).filter(
        WardState.state == WardStateEnum.CONFIRMED.value
    ).all()
    latencies = []
    for ws in confirmed_wards:
        first_report = db.query(Report).filter(
            Report.ward_id == ws.ward_id
        ).order_by(Report.timestamp.asc()).first()
        if first_report and ws.last_updated and first_report.timestamp:
            delta = (ws.last_updated - first_report.timestamp).total_seconds()
            if delta >= 0:
                latencies.append(delta)
    if not latencies:
        return {"avg_seconds": None, "count": 0, "source": "ward_states.last_updated - reports.timestamp"}
    return {
        "avg_seconds": round(statistics.mean(latencies), 1),
        "count": len(latencies),
        "source": "ward_states.last_updated - reports.timestamp"
    }


def broadcast_latency_stats(db: Session) -> Dict[str, Any]:
    """p50 / p95 of end-to-end broadcast latency from ChatEvent.latency_ms."""
    try:
        vals = [
            ev.latency_ms for ev in db.query(ChatEvent).filter(ChatEvent.latency_ms.isnot(None)).all()
        ]
        if not vals:
            return {"p50_ms": None, "p95_ms": None, "source": "chat_events.latency_ms"}
        vals_sorted = sorted(vals)
        p50 = statistics.median(vals_sorted)
        idx = max(0, int(len(vals_sorted) * 0.95) - 1)
        return {
            "p50_ms": round(p50, 1),
            "p95_ms": round(vals_sorted[idx], 1),
            "source": "chat_events.latency_ms"
        }
    except Exception:
        return {"p50_ms": None, "p95_ms": None, "source": "chat_events.latency_ms"}


def get_all_metrics(db: Session) -> Dict[str, Any]:
    """Aggregate all metrics in one call."""
    from app.eval.outage import is_outage_enabled
    return {
        "ingest_latency": latency_stats(db),
        "alert_counts": alert_counts(db),
        "llm_path_breakdown": llm_path_breakdown(db),
        "language_coverage": language_coverage(db),
        "report_confirmation_latency": report_confirmation_latency(db),
        "broadcast_latency": broadcast_latency_stats(db),
        "source_outage_active": is_outage_enabled(),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
