import sys
import os
import json

# Ensure we can find the modules in the ghost-void directory
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "ghost-void")))

from agency_hub.cognitive_tools import get_cognitive_manifold_review

def main():
    # 1. Define a realistic 'current_spoke_state' from the engine
    current_spoke_state = {
        "position": {"x": 124.5, "y": -42.1},
        "state_hash": "a1b2c3d4e5f6g7h8",
        "tiles": [
            {"id": 1, "type": "obsidian", "bounds": {"min": {"x": 120, "y": -45}, "max": {"x": 130, "y": -35}}},
            {"id": 2, "type": "magma", "bounds": {"min": {"x": 130, "y": -45}, "max": {"x": 140, "y": -35}}}
        ],
        "entities": [
            {"type": "raptor", "distance": 15.2, "hostile": True},
            {"type": "pioneer_crate", "distance": 5.0, "looted": False}
        ],
        "environmental_vibe": "oppressive_heat"
    }

    print("--- 🧠 Executing Prototype Tool Call: get_cognitive_manifold_review ---")
    
    # 2. Execute the tool call
    review_json = get_cognitive_manifold_review(current_spoke_state)
    
    # 3. Print the review
    review = json.loads(review_json)
    print(json.dumps(review, indent=2))
    
    # Validation checks
    if review.get("status") == "SETTLED":
        print("\n✅ Prototype SUCCESS: Parker has interpreted the Spoke state.")
    else:
        print("\n❌ Prototype FAILED: Review returned error status.")

if __name__ == "__main__":
    main()
