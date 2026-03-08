from __future__ import annotations

from typing import Any

from app.vector_ingestion import VectorIngestionEngine
from orchestrator.main import MCPHub
from scripts.tune_avatar_style import synthesize_lora_training_data


async def run_unified_loop(
    task_description: str,
    snapshot_data: Any | None = None,
    oidc_claims: Any | None = None,
) -> Any:
    """Run ingestion, style synthesis, and healing loop in one coroutine."""

    print("Initializing AutonomyDriftMonitor...")

    engine = VectorIngestionEngine()
    nodes = await engine.process_snapshot(snapshot_data or {}, oidc_claims or {})

    _training_data = synthesize_lora_training_data(nodes)

    hub = MCPHub()
    final_artifact = await hub.run_healing_loop(task_description)
    return final_artifact
