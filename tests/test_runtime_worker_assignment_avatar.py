from __future__ import annotations

from schemas.runtime_bridge import RuntimeWorkerAssignment


def test_runtime_worker_assignment_preserves_avatar_and_rbac():
    worker = RuntimeWorkerAssignment(
        worker_id="worker-01-coderagent",
        agent_name="CoderAgent",
        role="worker",
        fidelity="high",
        runtime_target="unity_lora_worker",
        deployment_mode="lora_training",
        render_backend="unity",
        metadata={"scope": "coding"},
        avatar={"avatar_id": "avatar_coder", "style": "engineer"},
        rbac={"role": "pipeline_operator", "actions": ["execute_kernel_action"]},
        mcp={"provider": "github-mcp"},
    )
    dumped = worker.model_dump(mode="json")
    assert dumped["avatar"]["avatar_id"] == "avatar_coder"
    assert dumped["rbac"]["role"] == "pipeline_operator"
