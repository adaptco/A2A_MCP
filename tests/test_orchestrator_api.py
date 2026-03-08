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


class _FakeOptionBService:
    create_calls = 0
    select_calls = 0

    @classmethod
    def from_env(cls):
        return cls()

    async def aclose(self):
        return None

    async def select_routing(self, *, operation: str):
        self.__class__.select_calls += 1
        return {
            "operation": operation,
            "selected_agent": "claude_agent",
            "model_string": "claude-sonnet-4-20250514",
            "weight_pct": 35.0,
            "routing_table_record_id": "rec-agent",
            "candidate_count": 1,
        }

    async def create_run_record(self, *, run_payload: dict):
        self.__class__.create_calls += 1
        return "rec-run-1"

    async def update_run_record(self, *, record_id: str, fields: dict):
        return None

    async def post_slack_message(self, *, channel_id: str, text: str, thread_ts: str | None = None):
        return {"ok": True, "channel": channel_id, "thread_ts": thread_ts, "text": text}

    @staticmethod
    def build_initial_run_payload(*, run_id: str, trace_id: str, command, requester: str, routing_decision: dict):
        return {
            "run_id": run_id,
            "trace_id": trace_id,
            "requester": requester,
            "command": command.normalized_command,
            "routing_decision": str(routing_decision),
            "status": "queued",
        }


def test_orchestrate_endpoint(monkeypatch):
    monkeypatch.setattr(api_module, "IntentEngine", _FakeIntentEngine)
    monkeypatch.setenv("AUTH_DISABLED", "true")
    client = TestClient(api_module.app)

    response = client.post("/orchestrate", params={"user_query": "build test app"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "A2A Workflow Complete"
    assert body["pipeline_results"]["coding"] == ["cod-1"]


def test_orchestrate_option_b_payload(monkeypatch):
    monkeypatch.setattr(api_module, "IntentEngine", _FakeIntentEngine)
    monkeypatch.setattr(api_module, "OptionBService", _FakeOptionBService)
    monkeypatch.setenv("AUTH_DISABLED", "true")
    api_module._IDEMPOTENCY_CACHE.clear()
    _FakeOptionBService.create_calls = 0
    _FakeOptionBService.select_calls = 0

    client = TestClient(api_module.app)
    response = client.post(
        "/orchestrate",
        json={
            "command": "!triage",
            "args": "test run",
            "slack": {"channel_id": "C0ADDUZJ5V5", "thread_ts": "1736208745.294349"},
        },
        headers={"X-Idempotency-Key": "idem-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"].startswith("run-")
    assert body["routing_decision"]["selected_agent"] == "claude_agent"
    assert body["airtable_record_id"] == "rec-run-1"
    assert body["slack_post_status"] == "sent"
    assert body["trace_id"]
    assert _FakeOptionBService.select_calls == 1
    assert _FakeOptionBService.create_calls == 1


def test_orchestrate_option_b_idempotency(monkeypatch):
    monkeypatch.setattr(api_module, "IntentEngine", _FakeIntentEngine)
    monkeypatch.setattr(api_module, "OptionBService", _FakeOptionBService)
    monkeypatch.setenv("AUTH_DISABLED", "true")
    api_module._IDEMPOTENCY_CACHE.clear()
    _FakeOptionBService.create_calls = 0

    client = TestClient(api_module.app)
    payload = {"command": "!run", "args": "ship release", "slack": {"channel_id": "C123"}}
    headers = {"X-Idempotency-Key": "idem-repeat"}
    first = client.post("/orchestrate", json=payload, headers=headers)
    second = client.post("/orchestrate", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["run_id"] == second.json()["run_id"]
    assert _FakeOptionBService.create_calls == 1


def test_orchestrate_option_b_invalid_command(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    client = TestClient(api_module.app)
    response = client.post("/orchestrate", json={"command": "!unknown"})
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error_code"] == "OPTB_INVALID_COMMAND"


def test_plans_ingress_endpoint(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    client = TestClient(api_module.app)
    response = client.post("/plans/ingress", json={"plan_id": "plan-test-123"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["plan_id"] == "plan-test-123"
