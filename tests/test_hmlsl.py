import json
import pytest
from orchestrator.hmlsl_ledger import HMLSLLedgerManager
from orchestrator.stateflow import StateMachine, State

def test_hmlsl_generation():
    plan_id = "test-plan-hmlsl"
    ledger_mgr = HMLSLLedgerManager(plan_id)

    # 1. Add Structural Nodes
    ledger_mgr.add_structural_node(
        contract_type="MCP_TOOL",
        definition={"name": "unity_render", "args": ["scene_id"]}
    )

    # 2. Add Behavioral Traces (Simulating a workflow)
    ledger_mgr.add_behavioral_trace(
        step_description="Initialize Unity",
        tool_invocation={"tool_name": "unity", "args": {"scene_id": "123"}}
    )
    ledger_mgr.add_behavioral_trace(
        step_description="Reasoning about scene",
        tool_invocation={"tool_name": "reasoning", "args": {}},
        result="Scene is complex"
    )
    ledger_mgr.add_behavioral_trace(
        step_description="Render Scene",
        tool_invocation={"tool_name": "unity", "args": {"quality": "high"}}
    )

    # 3. Finalize Ledger
    artifact = ledger_mgr.finalize()

    # 4. Verify Structure
    assert artifact.id == f"hmlsl-{plan_id}"
    assert len(artifact.structural_nodes) == 1
    assert len(artifact.behavioral_traces) == 3

    # 5. Verify Self-Clustering & Semantic Weights
    assert len(artifact.semantic_weights) == 3

    # Verify Resonance
    resonances = [w.resonance_score for w in artifact.semantic_weights]
    # 2/3 and 1/3 are expected
    assert any(abs(r - 0.6666) < 0.01 for r in resonances)

    # 6. Verify Visual Persona
    assert len(artifact.visual_persona_nodes) == 1
    persona = artifact.visual_persona_nodes[0]
    assert persona.cluster_id == "unity"
    assert persona.aesthetic_params["style"] == "cyberpunk_construct"

    # 7. Verify RBAC
    roles = [r.role for r in artifact.rbac_nodes]
    assert "UNITY_RENDERER" in roles

    # 8. Verify Merkle Root
    assert artifact.merkle_root is not None
    assert len(artifact.merkle_root) == 64  # SHA256 hex

    # 9. Verify JSON-LD Exportability
    json_output = artifact.model_dump_json(by_alias=True)
    data = json.loads(json_output)
    assert "@context" in data
    assert "@type" in data
    assert data["@type"] == "HMLSLArtifact"

def test_stateflow_integration():
    """
    Verify we can hook HMLSL into Stateflow transitions.
    """
    plan_id = "test-plan-integration"
    ledger_mgr = HMLSLLedgerManager(plan_id)
    sm = StateMachine(max_retries=3)
    sm.plan_id = plan_id

    # Define a callback that logs to ledger
    def log_transition(record):
        # Explicitly use .value to get clean string
        ledger_mgr.add_behavioral_trace(
            step_description=f"Transition to {record.to_state.value}",
            tool_invocation={"tool_name": "stateflow", "event": record.event},
            result=str(record.meta)
        )

    # Register callback for all relevant states
    for state in State:
        sm.register_callback(state, log_transition)

    # Trigger transitions
    sm.trigger("OBJECTIVE_INGRESS") # IDLE -> SCHEDULED
    sm.trigger("RUN_DISPATCHED")    # SCHEDULED -> EXECUTING

    # Finalize
    artifact = ledger_mgr.finalize()

    # Verify traces
    assert len(artifact.behavioral_traces) == 2
    assert artifact.behavioral_traces[0].step_description == "Transition to SCHEDULED"
    assert artifact.behavioral_traces[1].step_description == "Transition to EXECUTING"
