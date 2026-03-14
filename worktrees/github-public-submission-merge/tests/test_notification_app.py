from fastapi.testclient import TestClient

import app.notification_app as notification_app
from agents.notification_agent import NotificationResult


class StubAgent:
    agent_name = "NotificationAgent-Stub"

    def send_to_whatsapp_channel(self, *, channel_url: str, message: str):
        return NotificationResult(
            status="SENT",
            mode="bridge_to_operator",
            detail=f"{channel_url}::{message}",
        )


def test_notification_app_endpoint(monkeypatch):
    monkeypatch.setattr(notification_app, "_agent", StubAgent())
    client = TestClient(notification_app.app_notify)

    response = client.post(
        "/notify/whatsapp/channel",
        json={
            "channel_url": "https://whatsapp.com/channel/0029Vb6UzUH5a247SNGocW26",
            "message": "pipeline done",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SENT"
    assert body["mode"] == "bridge_to_operator"
