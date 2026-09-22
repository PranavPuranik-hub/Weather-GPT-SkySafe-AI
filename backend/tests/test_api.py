from fastapi.testclient import TestClient

from skysafe.main import app

client = TestClient(app)

def test_health_endpoint():
    for endpoint in ["/health", "/health/"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "last_sachet_fetch" in data
        assert "last_open_meteo_fetch" in data
        assert "llm_provider" in data
        assert "mode" in data
        assert data["status"] in ["healthy", "degraded"]

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
