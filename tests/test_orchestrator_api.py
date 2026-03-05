from dataclasses import dataclass, field

from fastapi.testclient import TestClient

import orchestrator.api as api_module


@dataclass
class _FakeArtifact:
    artifact_id: str
    content: str = ""


@dataclass
class _FakeResult:
    success: bool = True
    plan: object = field(default_factory=lambda: type("Plan", (), {"plan_id": "plan-1"})())
    blueprint: object = field(default_factory=lambda: type("Plan", (), {"plan_id": "bp-1"})())
    architecture_artifacts: list = field(default_factory=lambda: [_FakeArtifact("res-1")])
    code_artifacts: list = field(default_factory=lambda: [_FakeArtifact("cod-1", "print('ok')")])
    test_verdicts: list = field(default_factory=lambda: [{"artifact": "cod-1", "status": "PASS", "judge_score": "1.0"}])


class _FakeIntentEngine:
    async def run_full_pipeline(self, description: str, requester: str, max_healing_retries: int):
        assert description
        assert requester
        assert max_healing_retries >= 1
        return _FakeResult()


def test_orchestrate_endpoint(monkeypatch):
    monkeypatch.setattr(api_module, "IntentEngine", _FakeIntentEngine)
    client = TestClient(api_module.app)

    response = client.post("/orchestrate", params={"user_query": "build test app"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "A2A Workflow Complete"
    assert body["pipeline_results"]["coding"] == ["cod-1"]


def test_plans_ingress_endpoint():
    client = TestClient(api_module.app)
    response = client.post("/plans/ingress", json={"plan_id": "plan-test-123"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["plan_id"] == "plan-test-123"
