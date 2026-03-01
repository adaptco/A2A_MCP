import pytest
from fastapi.testclient import TestClient

import orchestrator.webhook as webhook


class _FakeEngineSuccess:
    async def run_release_workflow_from_webhook(self, payload, provider, event_type):
        return {
            "provider": provider,
            "event_type": event_type,
            "repository": payload.get("repository", {}).get("full_name", "unknown"),
            "release_tag": payload.get("release", {}).get("tag_name", "untagged"),
            "success": True,
        }


class _FakeEngineFailure:
    async def run_release_workflow_from_webhook(self, payload, provider, event_type):
        raise RuntimeError("release execution failed")


@pytest.fixture
def client():
    return TestClient(webhook.app)


def test_release_webhook_accepts_and_completes_job(client, monkeypatch):
    webhook.RELEASE_JOBS.clear()
    monkeypatch.setattr(webhook, "WEBHOOK_SHARED_SECRET", "")
    monkeypatch.setattr(webhook, "_get_engine", lambda: _FakeEngineSuccess())

    payload = {
        "repository": {"full_name": "acme/a2a-mcp"},
        "release": {"tag_name": "v1.2.3"},
    }
    response = client.post(
        "/webhooks/release",
        json=payload,
        headers={
            "X-Webhook-Provider": "github",
            "X-Webhook-Event": "release",
        },
    )
    assert response.status_code == 200
    release_id = response.json()["release_id"]

    status_response = client.get(f"/webhooks/release/{release_id}")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "completed"
    assert body["result"]["success"] is True
    assert body["result"]["release_tag"] == "v1.2.3"


def test_release_webhook_enforces_token_when_configured(client, monkeypatch):
    webhook.RELEASE_JOBS.clear()
    monkeypatch.setattr(webhook, "WEBHOOK_SHARED_SECRET", "topsecret")
    monkeypatch.setattr(webhook, "_get_engine", lambda: _FakeEngineSuccess())

    denied = client.post("/webhooks/release", json={})
    assert denied.status_code == 401

    allowed = client.post(
        "/webhooks/release",
        json={},
        headers={"X-Webhook-Token": "topsecret"},
    )
    assert allowed.status_code == 200


def test_release_webhook_records_failure_status(client, monkeypatch):
    webhook.RELEASE_JOBS.clear()
    monkeypatch.setattr(webhook, "WEBHOOK_SHARED_SECRET", "")
    monkeypatch.setattr(webhook, "_get_engine", lambda: _FakeEngineFailure())

    response = client.post("/webhooks/release", json={})
    assert response.status_code == 200
    release_id = response.json()["release_id"]

    status_response = client.get(f"/webhooks/release/{release_id}")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "failed"
    assert "release execution failed" in body["error"]
