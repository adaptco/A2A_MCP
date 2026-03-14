import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

class SystemsArchitect:
    """
    Agent responsible for spawning Orthogonal Directory Structures.
    Embeds ZKP Gate Policies at the node level to enforce access control.
    """
    
    def __init__(self, root_path: str = "src/nodes"):
        self.root_path = Path(root_path)
        
    def spawn_directory(self, node_id: str, feature_name: str, required_proofs: List[str] = None):
        """
        Creates the feature directory at the specified Base44 node.
        Embeds a gate_policy.json file.
        """
        if required_proofs is None:
            required_proofs = ["physics_compliance"]
            
        # 1. Calculate Path
        # Sanitize feature name
        safe_name = "".join([c if c.isalnum() else "_" for c in feature_name]).lower()
        target_dir = self.root_path / node_id / "features" / safe_name
        
        # 2. Create Directory Structure
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 3. Generate Gate Policy
        policy = {
            "$schema": "https://adk.io/schemas/v0/gate_policy.schema.json",
            "gate_id": str(uuid4()),
            "allowed_roles": ["coder", "architect", "manager"],
            "required_proofs": [
                {
                    "proof_type": proof,
                    "circuit_id": f"circuit_{proof}_v1",
                    "parameters": {"node_id": node_id}
                } for proof in required_proofs
            ],
            "enforcement_level": "strict"
        }
        
        # 4. Write Policy
        policy_path = target_dir / "gate_policy.json"
        with open(policy_path, "w") as f:
            json.dump(policy, f, indent=2)
            
        return str(target_dir)

if __name__ == "__main__":
    # Test run
    architect = SystemsArchitect(root_path="temp_nodes")
    path = architect.spawn_directory("B7", "Supra Drift Logic", ["physics_compliance", "integrity_check"])
    print(f"Spawned: {path}")
