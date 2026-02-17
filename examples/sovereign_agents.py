import torch
import asyncio
import sys
import os

# Add parent directory to path to import a2a_mcp
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a2a_mcp.runtime import MCPADKRuntime
from a2a_mcp.event_store import PostgresEventStore
from a2a_mcp.qube_integration import MCPQubeOrchestrator

async def main():
    print("🚀 Starting Sovereign Agent Demo...")
    
    # 1. Initialize core system
    runtime = MCPADKRuntime(use_real_llm=False)
    event_store = PostgresEventStore(pool=None) # Using mock pool
    orchestrator = MCPQubeOrchestrator(event_store)
    
    # 2. Orchestrate an MCP Token
    ci_cd_embeddings = torch.randn(5, 4096)
    task_desc = "Navigate WHAM world with nimble A90 sports car logic"
    
    result = await runtime.orchestrate(ci_cd_embeddings, task_desc)
    mcp_token = result['mcp_token']
    
    # 3. Spawn Sovereign Agent
    print("\n🔹 Spawning Sovereign Agent...")
    agent = await orchestrator.spawn_sovereign_agent(
        prompt="nimble A90 sports car",
        task=task_desc,
        mcp_token=mcp_token
    )
    
    # 4. Run Simulation (Events recorded to store)
    await orchestrator.run_simulation(agent, duration_ticks=10)
    
    # 5. Verify Sovereignty
    print("\n🛡️ Verifying Sovereignty...")
    is_safe = await orchestrator.verify_sovereignty(agent)
    
    # 6. Inspect Audit Trail
    print("\n📋 Final Audit Trail (Last 3 events):")
    history = event_store.get_history()
    for event in history[-3:]:
        payload_summary = str(event['payload'])[:50] + "..."
        print(f"  [{event['timestamp']}] {event['event_type']}: {event['hash'][:10]}... | {payload_summary}")

    if is_safe:
        print("\n✅ Sovereignty invariants maintained and verified.")
    else:
        print("\n❌ CRITICAL: Chain integrity compromised!")

if __name__ == "__main__":
    asyncio.run(main())
