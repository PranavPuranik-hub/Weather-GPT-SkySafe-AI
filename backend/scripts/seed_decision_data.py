import os
import sys
from pathlib import Path
import json

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.core.db import SessionLocal, Base, engine
from app.models.decision import WardInfo, Depot, Resource, Shelter

def get_geojson_square(lat, lon, size=0.005):
    """Generate a simple square polygon GeoJSON string for mock wards."""
    coords = [
        [lon - size, lat - size],
        [lon + size, lat - size],
        [lon + size, lat + size],
        [lon - size, lat + size],
        [lon - size, lat - size]
    ]
    return json.dumps({
        "type": "Polygon",
        "coordinates": [coords]
    })

def seed_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(WardInfo).count() > 0:
        print("Data already seeded.")
        db.close()
        return

    # 1. Ward Info (Mock data around Cuttack/Bhubaneswar)
    base_lat = 20.46
    base_lon = 85.88

    wards = [
        WardInfo(ward_id="Ward 1", name="Cuttack Central", population=15000, elderly_share=0.12, kutcha_house_share=0.20, low_lying_score=0.4, hospital_distance_km=2.5, lat=base_lat, lon=base_lon, polygon=get_geojson_square(base_lat, base_lon)),
        WardInfo(ward_id="Ward 2", name="Mahanadi Basin East", population=22000, elderly_share=0.15, kutcha_house_share=0.45, low_lying_score=0.85, hospital_distance_km=5.0, lat=base_lat + 0.01, lon=base_lon + 0.01, polygon=get_geojson_square(base_lat + 0.01, base_lon + 0.01)),
        WardInfo(ward_id="Ward 7", name="Cuttack South Riverfront", population=12400, elderly_share=0.18, kutcha_house_share=0.60, low_lying_score=0.9, hospital_distance_km=7.2, lat=base_lat - 0.01, lon=base_lon - 0.01, polygon=get_geojson_square(base_lat - 0.01, base_lon - 0.01)),
        WardInfo(ward_id="Ward 14", name="Puri Coastal North", population=8500, elderly_share=0.20, kutcha_house_share=0.30, low_lying_score=0.7, hospital_distance_km=12.0, lat=19.81, lon=85.82, polygon=get_geojson_square(19.81, 85.82)),
    ]
    db.add_all(wards)

    # 2. Shelters
    shelters = [
        Shelter(ward_id="Ward 1", name="Cuttack Central High School", lat=base_lat + 0.002, lon=base_lon + 0.002, capacity=1000, current_occupancy=0, contact="1077"),
        Shelter(ward_id="Ward 2", name="Mahanadi Relief Center", lat=base_lat + 0.015, lon=base_lon + 0.015, capacity=2000, current_occupancy=1500, contact="1077"),
        Shelter(ward_id="Ward 7", name="South Cuttack Cyclone Shelter", lat=base_lat - 0.008, lon=base_lon - 0.008, capacity=500, current_occupancy=480, contact="1077"),
        Shelter(ward_id="Ward 14", name="Puri Coastal Relief Camp", lat=19.815, lon=85.825, capacity=1500, current_occupancy=0, contact="1077"),
    ]
    db.add_all(shelters)

    # 3. Depots
    d1 = Depot(name="Cuttack Main Depot A", lat=base_lat + 0.02, lon=base_lon)
    d2 = Depot(name="Puri Coastal Depot B", lat=19.83, lon=85.85)
    db.add_all([d1, d2])
    db.commit()
    db.refresh(d1)
    db.refresh(d2)

    # 4. Resources
    resources = [
        Resource(depot_id=d1.id, type="NDRF Teams", total_qty=10, available_qty=10),
        Resource(depot_id=d1.id, type="Pumps", total_qty=20, available_qty=15),
        Resource(depot_id=d1.id, type="Boats", total_qty=15, available_qty=15),
        Resource(depot_id=d2.id, type="NDRF Teams", total_qty=5, available_qty=5),
        Resource(depot_id=d2.id, type="Relief Kits", total_qty=5000, available_qty=5000),
    ]
    db.add_all(resources)
    db.commit()

    print("Decision models data seeded successfully.")
    db.close()

if __name__ == "__main__":
    seed_data()
