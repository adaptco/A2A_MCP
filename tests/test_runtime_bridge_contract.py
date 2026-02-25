from schemas.runtime_bridge import (
    DMNGlobalVariable,
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
        avatar={"avatar_id": "avatar-runtime-001", "style": "driver"},
        rbac={"agent_id": "agent-runtime", "role": "observer"},
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
        rag={"collection": "a2a_worldline_rag_v1", "model": "sentence-transformers/all-mpnet-base-v2"},
        workers=[worker],
        token_stream=[{"token": "runtime", "token_id": "tok-1"}],
        dmn_global_variables=[
            DMNGlobalVariable(
                name="A2A_RUNTIME_ENGINE",
                value="WASD GameEngine",
                source="runtime",
                dmn_key="runtime.engine",
                xml_path="/dmn/globalVariables/variable[@name='A2A_RUNTIME_ENGINE']",
            )
        ],
        dmn_global_variables_xml=(
            "<dmnGlobalVariables schema=\"runtime.assignment.v1\" count=\"1\">"
            "<variable name=\"A2A_RUNTIME_ENGINE\" source=\"runtime\" "
            "dmnKey=\"runtime.engine\" "
            "xmlPath=\"/dmn/globalVariables/variable[@name='A2A_RUNTIME_ENGINE']\">"
            "WASD GameEngine"
            "</variable></dmnGlobalVariables>"
        ),
        kernel_model=kernel_model,
        runtime_bridge_metadata=bridge_meta,
        mcp={"provider": "github-mcp", "api_key_fingerprint": "deadbeefdeadbeef"},
    )

    dumped = assignment.model_dump(mode="json")
    reparsed = RuntimeAssignmentV1.model_validate(dumped)

    assert reparsed.schema_version == "runtime.assignment.v1"
    assert reparsed.workers[0].render_backend == "threejs"
    assert reparsed.workers[0].metadata["lane"] == "runtime"
    assert reparsed.workers[0].avatar["avatar_id"] == "avatar-runtime-001"
    assert reparsed.workers[0].rbac["role"] == "observer"
    assert reparsed.rag["collection"] == "a2a_worldline_rag_v1"
    assert reparsed.kernel_model is not None
    assert reparsed.kernel_model.api_token_env_var == "A2A_MCP_API_TOKEN"
    assert reparsed.runtime_bridge_metadata is not None
    assert reparsed.runtime_bridge_metadata.runtime_workers_ready == 1
    assert reparsed.dmn_global_variables
    assert reparsed.dmn_global_variables[0].dmn_key == "runtime.engine"
    assert "A2A_RUNTIME_ENGINE" in reparsed.dmn_global_variables_xml
