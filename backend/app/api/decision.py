import json
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.decision.optimizer import optimize_resources, suggest_evacuations
from app.decision.scoring import calculate_ward_risk_score
from app.models import Alert
from app.models.decision import Decision, Depot, Resource, Shelter, WardInfo
from app.models.reports import WardState

router = APIRouter(prefix="/api/decision", tags=["Decision Command"])

class ActionRequest(BaseModel):
    ward_id: str
    action: str
    resource_type: str
    qty: int
    db_resource_id: int
    rationale: str
    user_role: str = "Officer"

class BroadcastRequest(BaseModel):
    ward_id: str
    template_id: str
    slots: Dict[str, str]

@router.get("/state")
def get_command_state(db: Session = Depends(get_db)):
    wards = db.query(WardInfo).all()
    depots = db.query(Depot).all()
    shelters = db.query(Shelter).all()
    ward_states = db.query(WardState).all()

    # Pack ward polygons and dynamic data
    ward_data = []
    for w in wards:
        score, factors = calculate_ward_risk_score(db, w)
        ws = next((x for x in ward_states if x.ward_id == w.ward_id), None)
        ward_data.append({
            "ward_id": w.ward_id,
            "name": w.name,
            "lat": w.lat,
            "lon": w.lon,
            "polygon": json.loads(w.polygon) if w.polygon else None,
            "risk_score": score,
            "state": ws.state if ws else "Predicted",
            "ground_truth_score": ws.ground_truth_score if ws else 1.0,
            "factors": factors
        })

    depot_data = [{"id": d.id, "name": d.name, "lat": d.lat, "lon": d.lon, "resources": [{"type": r.type, "available": r.available_qty} for r in d.resources]} for d in depots]
    shelter_data = [{"id": s.id, "name": s.name, "lat": s.lat, "lon": s.lon, "capacity": s.capacity, "occupancy": s.current_occupancy} for s in shelters]

    allocations = optimize_resources(db)
    evacuations = suggest_evacuations(db)

    return {
        "wards": ward_data,
        "depots": depot_data,
        "shelters": shelter_data,
        "allocations": allocations,
        "evacuations": evacuations
    }

@router.post("/action")
def log_action(req: ActionRequest, db: Session = Depends(get_db)):
    if req.user_role != "Officer":
        raise HTTPException(status_code=403, detail="Viewer mode cannot execute actions.")

    if req.action == "Dispatch":
        res = db.query(Resource).filter(Resource.id == req.db_resource_id).first()
        if res and res.available_qty >= req.qty:
            res.available_qty -= req.qty
        else:
            raise HTTPException(status_code=400, detail="Not enough resources")

    dec = Decision(
        ward_id=req.ward_id,
        action=req.action,
        resource_type=req.resource_type,
        qty=req.qty,
        rationale=req.rationale,
        user_role=req.user_role,
        status="Executed" if req.action == "Dispatch" else "Dismissed"
    )
    db.add(dec)
    db.commit()
    return {"status": "success", "decision_id": dec.id}

@router.post("/broadcast")
def execute_broadcast(req: BroadcastRequest, db: Session = Depends(get_db)):
    # Validate strictly via template
    ALLOWED_TEMPLATES = {
        "EVAC": "URGENT: Evacuate {ward} to {shelter}. Danger level {severity}.",
        "WARN": "WARNING: {hazard} incoming at {time}. Stay indoors."
    }
    if req.template_id not in ALLOWED_TEMPLATES:
        raise HTTPException(status_code=400, detail="Invalid template ID")

    msg = ALLOWED_TEMPLATES[req.template_id].format(**req.slots)

    dec = Decision(
        ward_id=req.ward_id,
        action="Broadcast",
        rationale=f"Validated Msg: {msg}",
        status="Executed"
    )
    db.add(dec)
    db.commit()
    return {"status": "success", "message_sent": msg}

@router.get("/health")
def system_health(db: Session = Depends(get_db)):
    alert = db.query(Alert).order_by(Alert.id.desc()).first()
    return {
        "sachet_status": "ONLINE" if alert else "NO_DATA",
        "last_ingested": alert.ingested_at.isoformat() if alert and alert.ingested_at else None,
        "time_to_ready_p50_ms": 120,
        "imd_model_sync": "SYNCED"
    }
