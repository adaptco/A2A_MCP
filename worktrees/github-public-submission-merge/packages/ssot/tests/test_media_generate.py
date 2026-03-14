from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_media_generate_video():
    """Test generating media with valid 'video' type."""
    response = client.post(
        "/media/generate",
        json={"prompt": "A beautiful sunset", "media_type": "video"}
    )
    assert response.status_code == 200
    expected = {
        "accepted": True,
        "media_type": "video",
        "status": "queued",
        "prompt": "A beautiful sunset"
    }
    assert response.json() == expected

def test_media_generate_video_case_insensitive():
    """Test generating media with valid 'Video' type (case insensitive)."""
    response = client.post(
        "/media/generate",
        json={"prompt": "A beautiful sunset", "media_type": "Video"}
    )
    assert response.status_code == 200
    assert response.json()["accepted"] is True

def test_media_generate_invalid_type():
    """Test generating media with invalid 'audio' type."""
    response = client.post(
        "/media/generate",
        json={"prompt": "A beautiful sunset", "media_type": "audio"}
    )
    # Expect 422 because Pydantic model restricts to Literal["video", "Video"]
    assert response.status_code == 422

def test_media_generate_missing_prompt():
    """Test generating media without a prompt."""
    response = client.post(
        "/media/generate",
        json={"media_type": "video"}
    )
    assert response.status_code == 422
