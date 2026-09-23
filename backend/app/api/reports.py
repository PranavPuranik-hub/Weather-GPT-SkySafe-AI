import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.reports import WardState, WardStateEnum
from app.reports.service import SSE_CLIENTS, submit_report

logger = logging.getLogger("app")
router = APIRouter(prefix="/api/reports", tags=["Reports"])

class SimulateReportRequest(BaseModel):
    ward_id: str
    count: int = 5
    text: str = "Water entered my home"

import queue


@router.get("/ward_state_stream")
async def ward_state_stream(request: Request):
    """
    Server-Sent Events (SSE) endpoint to stream WardState changes to the dashboard.
    """
    q = queue.Queue()
    SSE_CLIENTS.append(q)

    async def event_generator():
        try:
            while True:
                # Disconnect if client leaves
                if await request.is_disconnected():
                    break

                # Non-blocking get with short sleep
                try:
                    payload = q.get_nowait()
                    yield f"data: {json.dumps(payload)}\n\n"
                except queue.Empty:
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass
        finally:
            if q in SSE_CLIENTS:
                SSE_CLIENTS.remove(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/simulate")
def simulate_ward_reports(req: SimulateReportRequest, db: Session = Depends(get_db)):
    """
    Simulate independent citizen reports in a specific ward to trigger a state flip.
    Useful for demonstrating Zero-Trust Verification.
    """
    # Reset ward state first for the demo
    ws = db.query(WardState).filter(WardState.ward_id == req.ward_id).first()
    if ws:
        ws.state = WardStateEnum.PREDICTED.value
        ws.ground_truth_score = 1.0
        db.commit()

    from app.models.reports import Report
    db.query(Report).filter(Report.ward_id == req.ward_id).delete()
    db.commit()

    results = []
    import uuid
    run_id = str(uuid.uuid4())[:8]
    for i in range(req.count):
        user_hash = f"simulated_user_{run_id}_{i}"
        report = submit_report(
            db=db,
            text=req.text,
            lat=20.0,
            lon=85.0,
            user_hash=user_hash,
            ward_id=req.ward_id
        )
        results.append(report.id)

    return {"status": "success", "ward_id": req.ward_id, "reports_created": len(results)}
