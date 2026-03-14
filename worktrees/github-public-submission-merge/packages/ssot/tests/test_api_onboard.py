from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_onboard_agent_success():
    """Test onboarding with a specific user."""
    response = client.post("/qbot/onboard", json={"user": "test_agent"})
    assert response.status_code == 200
    assert response.json() == {
        "onboarded": True,
        "badge": "test_agent-badge-v1",
        "status": "credentialed"
    }

def test_onboard_agent_default_user():
    """Test onboarding without a user defaults to 'unknown'."""
    response = client.post("/qbot/onboard", json={})
    assert response.status_code == 200
    assert response.json() == {
        "onboarded": True,
        "badge": "unknown-badge-v1",
        "status": "credentialed"
    }
