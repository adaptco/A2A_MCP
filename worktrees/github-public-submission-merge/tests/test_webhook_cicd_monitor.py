import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from agents.cicd_monitor_agent import CICDMonitorAgent
import orchestrator.webhook as webhook


def _workflow_payload(run_id: int, workflow_name: str, head_sha: str) -> dict:
    return {
        "workflow_run": {
            "id": run_id,
            "name": workflow_name,
            "status": "completed",
            "conclusion": "success",
            "head_sha": head_sha,
            "head_branch": "main",
            "html_url": "https://example.test/run",
            "event": "push",
            "run_number": 1,
        }
    }


def test_github_actions_webhook_ingest_and_status(monkeypatch):
    monitor = CICDMonitorAgent(required_workflows=["Agents CI/CD"], production_branches=["main"])
    monkeypatch.setattr(webhook, "CI_CD_MONITOR", monitor)
    monkeypatch.setattr(webhook, "WEBHOOK_SHARED_SECRET", "")
    monkeypatch.setattr(webhook, "GITHUB_WEBHOOK_SECRET", "")

    client = TestClient(webhook.app)

    response = client.post(
        "/webhooks/github/actions",
        json=_workflow_payload(101, "Agents CI/CD", "sha-001"),
        headers={"X-GitHub-Event": "workflow_run"},
    )
    assert response.status_code == 200
    assert response.json()["snapshot"]["production_ready"] is True

    status_response = client.get("/cicd/status/sha-001")
    assert status_response.status_code == 200
    assert status_response.json()["ready_for_release"] is True


def test_github_actions_webhook_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(webhook, "CI_CD_MONITOR", CICDMonitorAgent())
    monkeypatch.setattr(webhook, "WEBHOOK_SHARED_SECRET", "secret123")
    monkeypatch.setattr(webhook, "GITHUB_WEBHOOK_SECRET", "")

    client = TestClient(webhook.app)
    response = client.post(
        "/webhooks/github/actions",
        json=_workflow_payload(102, "Agents CI/CD", "sha-002"),
    )
    assert response.status_code == 401


def test_ingress_compat_route_still_works(monkeypatch):
    monkeypatch.setattr(webhook, "PLAN_STATE_MACHINES", {})
    client = TestClient(webhook.app)

    response = client.post("/ingress", json={"plan_id": "compat-plan"})
    assert response.status_code == 200
    assert response.json()["plan_id"] == "compat-plan"


def test_github_actions_webhook_accepts_valid_signature_when_configured(monkeypatch):
    monitor = CICDMonitorAgent(required_workflows=["Agents CI/CD"], production_branches=["main"])
    monkeypatch.setattr(webhook, "CI_CD_MONITOR", monitor)
    monkeypatch.setattr(webhook, "WEBHOOK_SHARED_SECRET", "")
    monkeypatch.setattr(webhook, "GITHUB_WEBHOOK_SECRET", "sig-secret")

    payload = _workflow_payload(103, "Agents CI/CD", "sha-003")
    body = json.dumps(payload, separators=(",", ":"))
    digest = hmac.new(b"sig-secret", body.encode("utf-8"), hashlib.sha256).hexdigest()

    client = TestClient(webhook.app)
    response = client.post(
        "/webhooks/github/actions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "workflow_run",
            "X-Hub-Signature-256": f"sha256={digest}",
        },
    )
    assert response.status_code == 200
    assert response.json()["snapshot"]["ready_for_release"] is True


def test_github_actions_webhook_rejects_invalid_signature_when_configured(monkeypatch):
    monkeypatch.setattr(webhook, "CI_CD_MONITOR", CICDMonitorAgent())
    monkeypatch.setattr(webhook, "WEBHOOK_SHARED_SECRET", "")
    monkeypatch.setattr(webhook, "GITHUB_WEBHOOK_SECRET", "sig-secret")

    payload = _workflow_payload(104, "Agents CI/CD", "sha-004")
    body = json.dumps(payload, separators=(",", ":"))

    client = TestClient(webhook.app)
    response = client.post(
        "/webhooks/github/actions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "workflow_run",
            "X-Hub-Signature-256": "sha256=deadbeef",
        },
    )
    assert response.status_code == 401
