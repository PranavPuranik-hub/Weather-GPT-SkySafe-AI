import math
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.decision.scoring import calculate_ward_risk_score
from app.models.decision import Depot, Shelter, WardInfo


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def optimize_resources(db: Session) -> List[Dict[str, Any]]:
    """
    Greedy allocator: prioritize highest risk wards and assign nearest available resources.
    """
    wards = db.query(WardInfo).all()
    depots = db.query(Depot).all()

    # Calculate risk scores for all wards
    ward_scores = []
    for w in wards:
        score, factors = calculate_ward_risk_score(db, w)
        ward_scores.append({
            "ward": w,
            "score": score,
            "factors": factors
        })

    # Sort wards descending by score
    ward_scores.sort(key=lambda x: x["score"], reverse=True)

    # Fetch available resources (in memory for greedy allocation simulation)
    # depot_resources[depot_id][type] = available_qty
    depot_resources = {}
    depot_models = {}
    for d in depots:
        depot_models[d.id] = d
        depot_resources[d.id] = {}
        for r in d.resources:
            if r.available_qty > 0:
                depot_resources[d.id][r.type] = {
                    "qty": r.available_qty,
                    "db_id": r.id
                }

    allocations = []
    speed_kmh = 30.0 # assumed truck speed

    # Simple rule matrix per hazard proxy (risk >= 60 triggers actions)
    for ws in ward_scores:
        w = ws["ward"]
        if ws["score"] < 40.0:
            continue # Skip low risk

        # Determine needed resources based on factors
        needs = {}
        if ws["score"] >= 70:
            needs["NDRF Teams"] = 2
            needs["Relief Kits"] = 500
        elif ws["score"] >= 50:
            needs["Relief Kits"] = 200

        if w.low_lying_score > 0.7:
            needs["Boats"] = 4
            needs["Pumps"] = 5

        for r_type, qty_needed in needs.items():
            # Find closest depot with this resource
            closest_depot = None
            min_dist = float('inf')
            for d_id, d_res in depot_resources.items():
                if r_type in d_res and d_res[r_type]["qty"] > 0:
                    dist = haversine(w.lat, w.lon, depot_models[d_id].lat, depot_models[d_id].lon)
                    if dist < min_dist:
                        min_dist = dist
                        closest_depot = d_id

            if closest_depot:
                available = depot_resources[closest_depot][r_type]["qty"]
                allocate_qty = min(qty_needed, available)
                eta_min = int((min_dist / speed_kmh) * 60)

                # Decrement in-memory for this pass
                depot_resources[closest_depot][r_type]["qty"] -= allocate_qty

                # Build ledger justification
                top_factors = ws["factors"][:3]
                rationale_text = f"risk {ws['score']}; " + "; ".join([f"{f['factor']} {f['value']}" for f in top_factors])

                allocations.append({
                    "ward_id": w.ward_id,
                    "ward_name": w.name,
                    "resource_type": r_type,
                    "qty": allocate_qty,
                    "depot_name": depot_models[closest_depot].name,
                    "eta_min": eta_min,
                    "rationale": rationale_text,
                    "ledger": top_factors, # specific data points for the drawer
                    "db_resource_id": depot_resources[closest_depot][r_type]["db_id"]
                })

    return allocations

def suggest_evacuations(db: Session) -> List[Dict[str, Any]]:
    wards = db.query(WardInfo).all()
    shelters = db.query(Shelter).all()

    # Risk calculation
    suggestions = []
    for w in wards:
        score, _ = calculate_ward_risk_score(db, w)
        if score > 60:
            # Find nearest shelter with spare capacity
            spare_shelters = [s for s in shelters if (s.capacity - s.current_occupancy) > 0]
            if spare_shelters:
                nearest = min(spare_shelters, key=lambda s: haversine(w.lat, w.lon, s.lat, s.lon))
                spare = nearest.capacity - nearest.current_occupancy
                suggestions.append({
                    "ward_id": w.ward_id,
                    "ward_name": w.name,
                    "shelter_name": nearest.name,
                    "spare_capacity": spare,
                    "risk_score": score
                })

    suggestions.sort(key=lambda x: x["risk_score"], reverse=True)
    return suggestions
