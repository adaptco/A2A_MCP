import os
import sys
import json
import random
import argparse
from typing import List, Dict, Any

# Add agents directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))
from parker import Parker

class RAGMock:
    """Mock RAG system for Parker's Semantic Memory."""
    def __init__(self):
        self.kb = [
            "Previous: Crafted spear before T-Rex encounter -> survived.",
            "Previous: Ran to cave when health was low -> survived.",
            "Previous: Fought T-Rex unarmed -> died.",
            "Strategy: Gather wood and stone in safe zones first.",
            "Strategy: Hunt only when health is above 70 and armed."
        ]
        
    def retrieve(self, query: str) -> List[str]:
        # Simple keyword matching for mock
        results = [item for item in self.kb if any(word in item.lower() for word in query.lower().split())]
        return results if results else self.kb[:2]

def run_episode(parker: Parker, rag: RAGMock, episode_num: int):
    print(f"\n--- Episode {episode_num} ---")
    state = {
        "health": 100,
        "threats": [],
        "resources": {"wood": 0, "stone": 0}
    }
    
    actions = ["gather", "craft", "explore", "hunt", "escape"]
    total_reward = 0
    survived = True
    
    # Simulate a few steps
    for step in range(5):
        # Context-aware thought
        context = f"Step {step+1}: Health={state['health']}, Resources={state['resources']}"
        parker.think(context)
        
        # RAG retrieval
        memory_query = "T-Rex survival" if state['health'] < 50 else "gathering strategy"
        retrieved = rag.retrieve(memory_query)
        
        # Decide and act
        action, reasoning = parker.act(state, actions)
        print(f"Action: {action} | {reasoning}")
        
        # Simulate environment response
        if action == "gather":
            state["resources"]["wood"] += random.randint(1, 3)
            state["resources"]["stone"] += random.randint(0, 2)
            total_reward += 5
        elif action == "hunt":
            if state["resources"]["wood"] > 2: # Mock having a tool
                total_reward += 30
            else:
                state["health"] -= 40
                total_reward -= 10
        elif action == "explore":
            total_reward += 10
            if random.random() < 0.2:
                state["threats"].append("T-Rex")
                
        if state["health"] <= 0:
            survived = False
            break
            
    outcome = {"reward": total_reward, "survived": survived}
    parker.learn(outcome)
    print(f"Outcome: {outcome}")

def interactive_mode(parker: Parker):
    print("\n--- Parker Interactive Mode ---")
    print("Type 'exit' to quit, 'status' to see Parker's personality.")
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'status':
            print(f"🤖 Parker Status:")
            print(f"  Confidence: {parker.confidence:.2f}")
            print(f"  XP: {parker.xp}")
            print(f"  Goal: {parker.current_goal}")
            print(f"  Mood: {parker.current_mood}")
            print(f"  Personality: {parker.personality}")
            continue
            
        # Use Parker's logic to "respond"
        thought = parker.think(f"User asked: {user_input}")
        print(f"🤖 Parker (Thinking): {thought}")
        print(f"🤖 Parker: I'm currently focused on my goal: {parker.current_goal}. I feel {parker.current_mood} about it.")

def export_lora_data(parker: Parker):
    print("\n--- Exporting LoRA Training Data ---")
    data = []
    for i, thought in enumerate(parker.thoughts):
        data.append({
            "instruction": f"You are Parker, an agent in Jurassic Pixels. Current mood: {parker.current_mood}.",
            "input": f"Observation: {thought}",
            "output": f"Thought: {thought}"
        })
        
    filepath = "parker_lora_data.json"
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Exported {len(data)} records to {filepath}")

def main():
    parser = argparse.ArgumentParser(description="Parker Training Orchestrator")
    parser.add_argument("--episodes", type=int, default=5, help="Number of episodes to train")
    parser.add_argument("--interactive", action="store_true", help="Start interactive mode after training")
    parser.add_argument("--export", action="store_true", help="Export LoRA data after training")
    parser.add_argument("--test", action="store_true", help="Run in test mode (no training)")
    
    args = parser.parse_args()
    
    parker = Parker()
    rag = RAGMock()
    
    if args.test:
        print("Running in test mode...")
        return
        
    print(f"Starting Parker's training for {args.episodes} episodes...")
    for i in range(args.episodes):
        run_episode(parker, rag, i+1)
        
    if args.export:
        export_lora_data(parker)
        
    if args.interactive:
        interactive_mode(parker)

if __name__ == "__main__":
    main()
