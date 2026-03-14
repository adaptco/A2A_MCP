"""Cross-MCP bridge schemas for orchestration -> runtime handoff."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class RuntimeWorkerAssignment(BaseModel):
    """Runtime worker contract for assignment delivery."""

    worker_id: str
    agent_name: str
    role: str
    fidelity: Literal["high", "low"]
    runtime_target: str
    deployment_mode: str
    render_backend: Literal["unity", "threejs"]
    runtime_shell: Literal["wasm"] = "wasm"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    mcp: Dict[str, Any] = Field(default_factory=dict)


class KernelVectorControlModel(BaseModel):
    """Kernel control model for vector manifold release governance."""

    kernel_id: str
    manifold_engine: str = "vector-manifold-engine"
    vector_namespace: str
    release_channel: str = "stable"
    api_token_env_var: str = "A2A_MCP_API_TOKEN"
    release_control: Dict[str, Any] = Field(default_factory=dict)
    spec_refs: List[str] = Field(default_factory=list)


class RuntimeBridgeMetadata(BaseModel):
    """Bridge-level metadata wired into runtime assignment artifacts."""

    bridge_path: str = "orchestration_mcp->runtime_mcp"
    schema_version: Literal["runtime.assignment.v1"] = "runtime.assignment.v1"
    handshake_id: str
    plan_id: str
    token_stream_normalized: bool = False
    runtime_workers_ready: int = 0
    kernel_model_written: bool = False
    release_channel: str = "stable"


class RuntimeAssignmentV1(BaseModel):
    """Typed runtime assignment payload shared across MCP servers."""

    schema_version: Literal["runtime.assignment.v1"] = "runtime.assignment.v1"
    assignment_id: str
    handshake_id: str
    plan_id: str
    repository: str
    commit_sha: str
    actor: str
    prompt: str
    runtime: Dict[str, Any] = Field(default_factory=dict)
    workers: List[RuntimeWorkerAssignment] = Field(default_factory=list)
    token_stream: List[Dict[str, str]] = Field(default_factory=list)
    token_stream_stats: Dict[str, Any] = Field(default_factory=dict)
    stateful_artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    orchestration_state: Dict[str, Any] = Field(default_factory=dict)
    kernel_model: KernelVectorControlModel | None = None
    runtime_bridge_metadata: RuntimeBridgeMetadata | None = None
    mcp: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
