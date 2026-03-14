import asyncio
import websockets
import json
import random
import time
import argparse
import os
from typing import Dict, Any

# Adjust path to import sibling modules if run as script
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from pipeline.manifold import Manifold

class ParkerAgent:
    def __init__(self, uri="ws://localhost:8080", simulate=False):
        self.uri = uri
        self.simulate = simulate
        self.manifold = Manifold(check_mount=True)
        self.collected_states = []
        
    async def run_mission(self) -> Dict[str, Any]:
        print(f"🦕 Parker Agent Initialized. Target: {self.uri} {'(SIMULATION)' if self.simulate else ''}")
        
        # Mock socket for simulation
        class MockSocket:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def send(self, msg): pass
            async def recv(self): return "{}"

        connector = websockets.connect(self.uri) if not self.simulate else MockSocket()
        
        try:
            async with connector as websocket:
                if not self.simulate:
                    await websocket.send(json.dumps({"type": "init", "role": "parker_architect"}))
                
                print("🔭 Exploring Game World to build Manifold...")
                
                # Exploration Phase (Simulated Speed Run)
                distance = 0
                max_dist = 5000 # 5km sample
                
                while distance < max_dist:
                    # Move
                    action = {"type": "move", "direction": "right", "turbo": True}
                    if not self.simulate:
                        await websocket.send(json.dumps(action))
                    
                    distance += 100
                    
                    # Periodic Observation (Analysis)
                    if distance % 1000 == 0:
                        print(f"📸 Scanning Sector {distance}m...")
                        observation = {
                            "location": distance,
                            "terrain_complexity": random.random(),
                            "entities": ["dino", "coin"] if random.random() > 0.5 else ["rock"]
                        }
                        self.collected_states.append(observation)
                        
                        # Simulate processing time
                        await asyncio.sleep(0.1)
                        
                    await asyncio.sleep(0.01)

                print("✅ Exploration Complete. Generating Artifacts...")
                return self._synthesize_artifacts()

        except Exception as e:
            if not self.simulate:
                print(f"⚠️ Connection failed ({e}). Switching to Simulation.")
                self.simulate = True
                return await self.run_mission()
            raise e

    def _synthesize_artifacts(self) -> Dict[str, Any]:
        # 1. Aggregate State
        aggregated_state = {
            "sectors_scanned": len(self.collected_states),
            "average_complexity": sum(s["terrain_complexity"] for s in self.collected_states) / len(self.collected_states),
            "samples": self.collected_states
        }
        
        # 2. Generate Manifold Embedding
        print("🧠 Generating Vector Embeddings...")
        embedding = self.manifold.encode_state(aggregated_state)
        
        # 3. Decode into Unity Plan
        print("🏗️  Decoding into Unity Scaffolding...")
        unity_plan = self.manifold.decode_plan(embedding)
        
        return {
            "remodel_plan": unity_plan,
            "raw_embedding": embedding
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", action="store_true", help="Force simulation mode")
    args = parser.parse_args()
    
    agent = ParkerAgent(simulate=args.simulate)
    artifacts = asyncio.run(agent.run_mission())
    
    print("\n📦 Mission Artifacts Generated:")
    print(json.dumps(artifacts["remodel_plan"], indent=2))
