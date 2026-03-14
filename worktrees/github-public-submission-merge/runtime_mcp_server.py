"""Runtime MCP server scaffold for GameEngine runtime assignments."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from bootstrap import bootstrap_paths

bootstrap_paths()

try:
    from fastmcp import FastMCP
except ModuleNotFoundError:
    from mcp.server.fastmcp import FastMCP

from schemas.agent_artifacts import MCPArtifact
from schemas.runtime_bridge import RuntimeAssignmentV1

mcp = FastMCP("A2A_Runtime")

_RUNTIME_ASSIGNMENTS: Dict[str, RuntimeAssignmentV1] = {}


def _coerce_runtime_assignment(payload: dict[str, Any]) -> RuntimeAssignmentV1:
    artifact = MCPArtifact.model_validate(payload)
    if artifact.type != "runtime.assignment.v1":
        raise ValueError(
            f"Unsupported artifact type '{artifact.type}'. Expected runtime.assignment.v1"
        )

    content = artifact.content
    if isinstance(content, str):
        content = json.loads(content)

    return RuntimeAssignmentV1.model_validate(content)


def submit_runtime_assignment(artifact: dict) -> dict:
    """Accept and register a runtime assignment artifact."""
    assignment = _coerce_runtime_assignment(artifact)
    _RUNTIME_ASSIGNMENTS[assignment.assignment_id] = assignment
    return {
        "status": "accepted",
        "assignment_id": assignment.assignment_id,
        "plan_id": assignment.plan_id,
        "worker_count": len(assignment.workers),
    }


def get_runtime_assignment(assignment_id: str) -> dict:
    """Return a previously registered runtime assignment."""
    assignment = _RUNTIME_ASSIGNMENTS.get(assignment_id)
    if assignment is None:
        return {"status": "not_found", "assignment_id": assignment_id}
    return {"status": "ok", "assignment": assignment.model_dump(mode="json")}


def list_runtime_assignments(plan_id: str = "") -> dict:
    """List runtime assignments, optionally filtered by plan_id."""
    assignments: List[RuntimeAssignmentV1] = list(_RUNTIME_ASSIGNMENTS.values())
    if plan_id.strip():
        assignments = [a for a in assignments if a.plan_id == plan_id]

    return {
        "status": "ok",
        "count": len(assignments),
        "assignments": [a.model_dump(mode="json") for a in assignments],
    }


mcp.tool()(submit_runtime_assignment)
mcp.tool()(get_runtime_assignment)
mcp.tool()(list_runtime_assignments)


if __name__ == "__main__":
    mcp.run()
