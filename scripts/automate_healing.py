import asyncio
from typing import Any, Dict, Optional

from orchestrator.main import MCPHub
from scripts.tune_avatar_style import synthesize_lora_training_data
# Import ingestion utilities from your app layer
from app.vector_ingestion import VectorIngestionEngine


async def run_unified_loop(
    task_description: str,
    snapshot_data: Optional[Dict[str, Any]] = None,
    oidc_claims: Optional[Dict[str, Any]] = None,
):
    # 1. Start Observer Mode & Monitor
    print("Initializing AutonomyDriftMonitor...") #

    # Keep script invocations safe even when caller does not pass context payloads.
    snapshot_data = snapshot_data or {}
    oidc_claims = oidc_claims or {}

    # 2. Sync Knowledge (Vector Ingestion)
    engine = VectorIngestionEngine()
    # Process current repo snapshot into vector nodes
    nodes = await engine.process_snapshot(snapshot_data, oidc_claims) 
    
    # 3. Update Agent Recovery Style (LoRA)
    # Convert nodes to training data for recovery logic
    training_data = synthesize_lora_training_data(nodes)
    
    # 4. Execute Self-Healing Loop
    hub = MCPHub()
    # Runs the Coder -> Tester -> Fix cycle
    final_artifact = await hub.run_healing_loop(task_description)
    
    return final_artifact
