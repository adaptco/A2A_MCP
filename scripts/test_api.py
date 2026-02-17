import asyncio
from orchestrator.main import MCPHub

async def main():
    print("🚀 Initiating A2A-MCP Self-Healing Test...")
    hub = MCPHub()
    
    # Task: Create a specific storage function
    # Note: We intentionally provide a slightly vague task to see 
    # if the Tester Agent triggers a refinement cycle.
    task = "Implement a secure file-deletion utility in storage.py"
    
    final_artifact = await hub.run_healing_loop(task)
    
    if final_artifact:
        print(f"\n✅ Success! Final Verified Artifact ID: {final_artifact.artifact_id}")
        print(f"Agent Trace: {final_artifact.agent_name} (v{final_artifact.version})")
    else:
        print("\n❌ System failed to converge within retry limits.")

if __name__ == "__main__":
    asyncio.run(main())
