import json
import logging
from typing import Dict, Any
from agency_hub.tensor_field import TensorField
from pipeline.manifold import Manifold

logger = logging.getLogger(__name__)

def get_cognitive_manifold_review(raw_state: Dict[str, Any]) -> str:
    """
    Tool function for LLMs to review the embedding vector environment.
    Transforms raw state into a cognitive manifold review.
    """
    try:
        # 1. Initialize Manifold components
        tensor_field = TensorField(embedding_dim=64)
        manifold = Manifold()

        # 2. Voxelize and Compute Eigenstate
        voxel_tensor = tensor_field.voxelize_state(raw_state)
        eigenstate = tensor_field.compute_eigenstate(voxel_tensor)
        
        # 3. Encode into high-dimensional space
        embedding = manifold.encode_state(raw_state)
        
        # 4. Decode into Unity Remodel Plan
        plan = manifold.decode_plan(embedding)
        
        # 5. Synthesis Report (Parker's Voice)
        review = {
            "avatar": "Parker",
            "mission": "Cognitive Mapping",
            "observation_hash": json.dumps(raw_state, sort_keys=True)[:16],
            "manifold_metrics": {
                "eigenstate_norm": float(sum(eigenstate**2)**0.5),
                "embedding_signature": embedding[:8]
            },
            "interpretation": {
                "biome": plan.get("biome"),
                "detected_features": plan.get("generated_features"),
                "engine_target": plan.get("target_engine")
            },
            "status": "SETTLED"
        }
        
        return json.dumps(review, indent=2)
    except Exception as e:
        logger.error(f"Cognitive review failed: {e}")
        return json.dumps({"error": str(e), "status": "FAILED"})

if __name__ == "__main__":
    # Example usage
    test_state = {"location": 1000, "terrain": "rocky", "entities": ["dino"]}
    print(get_cognitive_manifold_review(test_state))
