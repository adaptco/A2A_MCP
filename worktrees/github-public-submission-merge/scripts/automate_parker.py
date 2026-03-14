import asyncio
import json
import yaml
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from jurassic_pixels.parker_agent import ParkerAgent

async def main():
    print("🤖 AUTOMATION: Triggering Parker Agent Workflow...")
    
    # 1. Initialize Agent (Force simulation if no server arg)
    server_uri = "ws://localhost:8080"
    # Logic: Try real first, but ParkerAgent falls back to sim anyway if connection fails.
    # We will pass simulate=False to test the fallback logic too.
    agent = ParkerAgent(uri=server_uri, simulate=False)
    
    # 2. Run Mission
    print("▶️  Starting Mission...")
    try:
        results = await agent.run_mission()
    except Exception as e:
        print(f"❌ Mission Failed: {e}")
        return

    # 3. Process Artifacts
    remodel_plan = results["remodel_plan"]
    raw_vector = results["raw_embedding"]
    
    print(f"\n🧠 Manifold Vector Generated (First 5 dims): {raw_vector[:5]}...")
    
    # 4. Save Unity Scaffolding
    output_path = Path("unity_scaffold.yaml")
    with open(output_path, "w") as f:
        yaml.dump(remodel_plan, f, sort_keys=False)
        
    print(f"✅ Unity Scaffolding Saved to: {output_path.absolute()}")
    
    # 5. Simulate Webhook Trigger
    print("\n🔗 Triggering CI/CD Webhook for Model Integration...")
    payload = {
        "event": "remodel_proposal",
        "agent": "Parker",
        "artifact_uri": str(output_path.absolute()),
        "vector_signature": raw_vector[:5]
    }
    # (Mock Request)
    print(f"   POST https://ci.internal/hooks/unity-builder\n   Payload: {json.dumps(payload, indent=2)}")
    print("🎉 Workflow Complete.")

if __name__ == "__main__":
    asyncio.run(main())
