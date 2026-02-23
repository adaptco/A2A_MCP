from schemas.agent_artifacts import MCPArtifact
from schemas.runtime_bridge import RuntimeAssignmentV1, RuntimeWorkerAssignment

import runtime_mcp_server as runtime_server


def _build_assignment_artifact() -> dict:
    worker = RuntimeWorkerAssignment(
        worker_id="worker-01-runtime",
        agent_name="GameRuntimeAgent",
        role="runtime",
        fidelity="low",
        runtime_target="threejs_compact_worker",
        deployment_mode="compact_runtime",
        render_backend="threejs",
        runtime_shell="wasm",
        mcp={"provider": "github-mcp"},
    )
    assignment = RuntimeAssignmentV1(
        assignment_id="rtassign-test-001",
        handshake_id="hs-test-001",
        plan_id="plan-test-001",
        repository="adaptco/A2A_MCP",
        commit_sha="abc123",
        actor="qa_user",
        prompt="deploy runtime worker",
        runtime={"wasm_shell": {"enabled": True}},
        workers=[worker],
        token_stream=[{"token": "runtime", "token_id": "tok-1"}],
        mcp={"provider": "github-mcp", "api_key_fingerprint": "f00df00df00df00d"},
    )
    artifact = MCPArtifact(
        artifact_id="bridge-001",
        parent_artifact_id="plan-test-001",
        agent_name="OrchestrationAgent",
        type="runtime.assignment.v1",
        content=assignment.model_dump(mode="json"),
    )
    return artifact.model_dump(mode="json")


def test_runtime_mcp_server_submit_get_and_list():
    runtime_server._RUNTIME_ASSIGNMENTS.clear()
    payload = _build_assignment_artifact()

    submit = runtime_server.submit_runtime_assignment(payload)
    assert submit["status"] == "accepted"
    assert submit["assignment_id"] == "rtassign-test-001"

    fetched = runtime_server.get_runtime_assignment("rtassign-test-001")
    assert fetched["status"] == "ok"
    assert fetched["assignment"]["plan_id"] == "plan-test-001"

    listed = runtime_server.list_runtime_assignments("plan-test-001")
    assert listed["status"] == "ok"
    assert listed["count"] == 1
