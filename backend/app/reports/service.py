"""
Reports package: Automated bulletin & Situation Report (SitRep) generator, and Citizen Report clustering.
"""
import queue
import re
from datetime import datetime, timedelta
from typing import List

from sqlalchemy.orm import Session

from app.models.reports import Report, WardState, WardStateEnum

# SSE Broadcaster Queues
# We store a list of thread-safe Queues. Each connected client gets a queue.
SSE_CLIENTS: List[queue.Queue] = []

def broadcast_ward_state(ward_state: WardState):
    """Publish a WardState change to all connected SSE clients."""
    payload = {
        "ward_id": ward_state.ward_id,
        "state": ward_state.state,
        "last_updated": ward_state.last_updated.isoformat(),
        "ground_truth_score": ward_state.ground_truth_score,
        "severity": ward_state.severity
    }
    for q in SSE_CLIENTS:
        try:
            q.put_nowait(payload)
        except queue.Full:
            pass


def classify_report_category(text: str) -> str:
    """
    Rule-first classifier for report category.
    Classifications: 'Water Logging', 'Tree Down', 'Road Blocked', 'Power Outage', 'Need Help', 'Safe', 'Other'
    """
    t = text.lower()

    if re.search(r'\b(help|rescue|boat|stuck|save|emergency|trapped)\b', t):
        return "Need Help"
    if re.search(r'\b(safe|okay|fine|survived)\b', t):
        return "Safe"
    if re.search(r'\b(water|flood|flooding|waterlogged|waterlogging|submerged)\b', t):
        return "Water Logging"
    if re.search(r'\b(tree|branch|pole|mast|tower|down|fallen)\b', t):
        return "Tree Down"
    if re.search(r'\b(road|highway|street|blocked|traffic|jam|landslide)\b', t):
        return "Road Blocked"
    if re.search(r'\b(power|electricity|outage|dark|wire|cut)\b', t):
        return "Power Outage"

    return "Other"


def submit_report(db: Session, text: str, lat: float, lon: float, user_hash: str, ward_id: str, photo_url: str = None) -> Report:
    """
    Submit a citizen report and trigger clustering verification.
    """
    category = classify_report_category(text)

    # Check for Spam / Rate Limiting (same user in same ward in last 30 mins)
    thirty_mins_ago = datetime.utcnow() - timedelta(minutes=30)
    existing_reports = db.query(Report).filter(
        Report.reporter_hash == user_hash,
        Report.ward_id == ward_id,
        Report.timestamp >= thirty_mins_ago
    ).all()

    confidence = "Unverified"
    if existing_reports:
        confidence = "Spam"

    # Ensure WardState exists
    ws = db.query(WardState).filter(WardState.ward_id == ward_id).first()
    if not ws:
        ws = WardState(ward_id=ward_id, state=WardStateEnum.PREDICTED.value)
        db.add(ws)
        db.commit()
        db.refresh(ws)

    report = Report(
        text=text,
        category=category,
        ward_id=ward_id,
        lat=lat,
        lon=lon,
        photo_url=photo_url,
        reporter_hash=user_hash,
        confidence=confidence
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    if confidence != "Spam":
        # Process clustering
        process_clustering(db, ward_id)

    return report


def process_clustering(db: Session, ward_id: str):
    """
    Zero-trust verification: cluster independent reports in a time window.
    1 report = Reported (Unverified)
    3+ independent reports = Confirmed
    """
    thirty_mins_ago = datetime.utcnow() - timedelta(minutes=30)

    # Count unique non-spam reporters in this ward in the last 30 minutes
    valid_reports = db.query(Report).filter(
        Report.ward_id == ward_id,
        Report.confidence != "Spam",
        Report.timestamp >= thirty_mins_ago
    ).all()

    unique_reporters = set(r.reporter_hash for r in valid_reports)
    count = len(unique_reporters)

    ws = db.query(WardState).filter(WardState.ward_id == ward_id).first()
    if not ws:
        return

    old_state = ws.state

    if count >= 3:
        ws.state = WardStateEnum.CONFIRMED.value
        ws.ground_truth_score = min(ws.ground_truth_score + 0.1, 5.0)
        # Update the confidence of those reports
        for r in valid_reports:
            if r.confidence != "Confirmed":
                r.confidence = "Confirmed"
    elif count >= 1:
        if ws.state == WardStateEnum.PREDICTED.value:
            ws.state = WardStateEnum.REPORTED.value

    ws.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(ws)

    # Trigger SSE broadcast if state changed or if explicitly we just want to push update
    if old_state != ws.state or count >= 3:
        broadcast_ward_state(ws)


def generate_sitrep(district: str) -> str:
    """Generate markdown/PDF situation report for officials."""
    return f"# Situation Report - {district}\nStatus: DRILL / SIMULATION\n"
