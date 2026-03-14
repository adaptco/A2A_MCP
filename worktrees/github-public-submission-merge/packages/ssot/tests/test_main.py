from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_readiness_check():
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "ts" in data
    assert isinstance(data["ts"], int)
