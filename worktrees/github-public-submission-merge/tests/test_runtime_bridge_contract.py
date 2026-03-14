from schemas.runtime_bridge import (
    KernelVectorControlModel,
    RuntimeAssignmentV1,
    RuntimeBridgeMetadata,
    RuntimeWorkerAssignment,
)


def test_runtime_assignment_v1_round_trip():
    worker = RuntimeWorkerAssignment(
        worker_id="worker-01-runtime",
        agent_name="GameRuntimeAgent",
        role="runtime",
        fidelity="low",
        runtime_target="threejs_compact_worker",
        deployment_mode="compact_runtime",
        render_backend="threejs",
        runtime_shell="wasm",
        metadata={"lane": "runtime"},
        mcp={"provider": "github-mcp"},
    )
    kernel_model = KernelVectorControlModel(
        kernel_id="kernel-plan-abc123",
        vector_namespace="a2a.manifold.plan-abc123",
        release_control={"required_phase": "ready_for_release"},
        spec_refs=["INDEX.md"],
    )
    bridge_meta = RuntimeBridgeMetadata(
        handshake_id="hs-abc123",
        plan_id="plan-abc123",
        token_stream_normalized=True,
        runtime_workers_ready=1,
        kernel_model_written=True,
    )
    assignment = RuntimeAssignmentV1(
        assignment_id="rtassign-abc123",
        handshake_id="hs-abc123",
        plan_id="plan-abc123",
        repository="adaptco/A2A_MCP",
        commit_sha="abc123",
        actor="qa_user",
        prompt="deploy runtime worker",
        runtime={"wasm_shell": {"enabled": True}},
        workers=[worker],
        token_stream=[{"token": "runtime", "token_id": "tok-1"}],
        kernel_model=kernel_model,
        runtime_bridge_metadata=bridge_meta,
        mcp={"provider": "github-mcp", "api_key_fingerprint": "deadbeefdeadbeef"},
    )

    dumped = assignment.model_dump(mode="json")
    reparsed = RuntimeAssignmentV1.model_validate(dumped)

    assert reparsed.schema_version == "runtime.assignment.v1"
    assert reparsed.workers[0].render_backend == "threejs"
    assert reparsed.workers[0].metadata["lane"] == "runtime"
    assert reparsed.kernel_model is not None
    assert reparsed.kernel_model.api_token_env_var == "A2A_MCP_API_TOKEN"
    assert reparsed.runtime_bridge_metadata is not None
    assert reparsed.runtime_bridge_metadata.runtime_workers_ready == 1
