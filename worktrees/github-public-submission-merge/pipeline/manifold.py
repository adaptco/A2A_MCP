import random
import json
import hashlib
from typing import Dict, List, Any

class Manifold:
    """
    Simulates a high-dimensional manifold for Game State -> Vector -> Reformatted Content.
    """
    
    def __init__(self, check_mount: bool = False):
        self.embedding_dim = 128
        if check_mount:
            print("🔮 Manifold mounted and ready.")

    def encode_state(self, state: Dict[str, Any]) -> List[float]:
        """
        Encodes a game state (JSON dict) into a 128-dim vector.
        Uses a consistent hash-based pseudo-random generation to be deterministic.
        """
        # Create a seed from the state content
        state_str = json.dumps(state, sort_keys=True)
        seed = int(hashlib.sha256(state_str.encode("utf-8")).hexdigest(), 16)
        
        # Generate vector
        rng = random.Random(seed)
        vector = [rng.uniform(-1.0, 1.0) for _ in range(self.embedding_dim)]
        return vector

    def decode_plan(self, embedding: List[float]) -> Dict[str, Any]:
        """
        Decodes a vector embedding into a Unity Remodel Plan (Scaffolding).
        Heuristic: Inspects vector properties to determine terrain features.
        """
        # Use the first few dimensions to decide the biome/features
        avg_val = sum(embedding) / len(embedding)
        
        biome = "Standard"
        if avg_val > 0.1:
            biome = "Volcanic_Glass"
        elif avg_val < -0.1:
            biome = "Crystal_Caves"
            
        features = []
        if embedding[0] > 0.5:
            features.append("Floating_Platforms")
        if embedding[1] < -0.5:
            features.append("Lava_Moats")
        if embedding[2] > 0.0:
            features.append("Ancient_Ruins")

        return {
            "target_engine": "Unity 6",
            "pipeline": "HDRP",
            "biome": biome,
            "generated_features": features,
            "terrain_shader": f"ShaderGraphs/{biome}_Base",
            "physics_material": f"PhysicMaterials/{biome}_Friction",
            "vector_signature": embedding[:5]  # efficient storage
        }
