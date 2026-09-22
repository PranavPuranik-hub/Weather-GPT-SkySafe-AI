import queue
from fastapi.testclient import TestClient
from app.main import app
from app.reports.service import SSE_CLIENTS
from app.models.reports import WardState
from app.core.db import SessionLocal

# create a fake client queue
q = queue.Queue()
SSE_CLIENTS.append(q)

client = TestClient(app)

res = client.post("/api/reports/simulate", json={
  "ward_id": "Ward 7",
  "count": 5,
  "text": "Water entered my home"
})
print("Simulate Res:", res.json())

while not q.empty():
    print("SSE Event:", q.get())

db = SessionLocal()
ws = db.query(WardState).filter(WardState.ward_id == 'Ward 7').first()
print("Ward 7 State in DB:", ws.state if ws else None)
