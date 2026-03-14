import asyncio
import uuid
import json
from avatars.registry import get_registry
from agents.gating_agent import GatingAgent
from schemas.agent_artifacts import MCPArtifact
from orchestrator.storage import DBManager

async def run_gating_demo():
    print("--- Initiating Scaffold Avatar Gating Demo ---")
    
    registry = get_registry()
    db = DBManager()
    
    # 1. Setup the Scaffold Avatar
    scaffold_avatar = registry.get_avatar("scaffold")
    gating_agent = GatingAgent()
    scaffold_avatar.bind_agent(gating_agent)
    
    print(f"Loaded Avatar: {scaffold_avatar}")
    
    # 2. Simulate a proposed artifact (e.g., from a CoderAgent)
    proposed_artifact = MCPArtifact(
        artifact_id=f"art-{str(uuid.uuid4())[:8]}",
        type="code_solution",
        content={
            "action": "modify_physics",
            "params": {"slip_angle_max": 45.0},
            "description": "Supra Drift Mode implementation"
        },
        agent_name="CoderAgent-Alpha"
    )
    db.save_artifact(proposed_artifact)
    print(f"Proposed Artifact: {proposed_artifact.artifact_id} ({proposed_artifact.type})")
    
    # 3. Use the Scaffold Avatar to Gate the Artifact
    print("\nExecuting Gating Protocol...")
    gate_result_raw = await scaffold_avatar.respond(
        prompt="Gate this physics modification against the Supra GT500 spec.",
        context={"artifact_id": proposed_artifact.artifact_id}
    )
    
    # Parse the result back to dict (since Avatar.respond returns str)
    try:
        if isinstance(gate_result_raw, str):
            # Replace single quotes with double quotes for JSON parsing if needed, 
            # though json.dumps should have been used.
            # GatingAgent returns a dict, Avatar.respond does str(dict)
            # which uses single quotes.
            import ast
            gate_result = ast.literal_eval(gate_result_raw)
        else:
            gate_result = gate_result_raw
    except:
        gate_result = {"status": "FAIL", "details": gate_result_raw}
    
    print("\n--- Gate Result (Attestation) ---")
    print(json.dumps(gate_result, indent=2))
    
    if gate_result.get("status") == "PASS":
        print("\n✓ ATTESTATION SUCCESSFUL: Artifact committed to digital thread.")
    else:
        print("\n✗ ATTESTATION FAILED: Rejecting proposed modification.")

if __name__ == "__main__":
    asyncio.run(run_gating_demo())
