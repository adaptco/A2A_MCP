"""
Hyperion Loop: The Manager Agent's Control Logic.
Integrates Feature Attractors, Vector Reranking, and Orthogonal Directory Spawning.
"""
import sys
import json
from pathlib import Path

# Fix path to include project root
sys.path.append(str(Path(__file__).resolve().parent.parent))

from adk.models.attractor import FeatureAttractor
from toolquest.semantic.reranker import VectorReranker
from agency_hub.architect.systems_architect import SystemsArchitect

def run_hyperion_cycle(attractor_data: dict, dry_run: bool = False):
    print(f"--- [Hyperion] Initiating Cycle for '{attractor_data['name']}' ---")
    
    # 1. Ingest Attractor
    attractor = FeatureAttractor(**attractor_data)
    print(f"[*] Attractor Ingested: Priority {attractor.priority}")
    
    # 2. Vector Rerank (Data Analyst)
    # Convert to request schema expected by reranker (using temporary object or direct calls)
    # The reranker expects AttractorRerankRequest which is slightly different
    from toolquest.semantic.schemas import AttractorRerankRequest
    
    rerank_req = AttractorRerankRequest(
        attractor_name=attractor.name,
        vector_queries=attractor.vector_queries,
        limit=5
    )
    
    reranker = VectorReranker()
    print("[*] Reranking Vector Vault...")
    manifest = reranker.rerank_tools(rerank_req)
    
    print(f"[*] Generated Manifest with {len(manifest)} items:")
    for item in manifest:
        print(f"    - {item.tool.tool_name} (Score: {item.similarity_score:.4f})")
        
    # 3. Spawn Orthogonal Directories (Systems Architect)
    architect = SystemsArchitect(root_path="src/nodes")
    
    # Map high-priority tools to Base44 nodes (Mock allocation logic)
    # In a real system, this would use the Base44 Grid logic
    allocations = {
        "A1": "physics_engine_core",
        "B7": "supra_drift_logic" # Using the feature name directly for now as a sub-feature
    }
    
    print("[*] Spawning Orthogonal Directories...")
    for node, feature_sub in allocations.items():
        if dry_run:
             print(f"    [DRY RUN] Would spawn {node}/{feature_sub}")
             continue
             
        path = architect.spawn_directory(
            node_id=node,
            feature_name=feature_sub,
            required_proofs=["physics_compliance", "integrity_check"]
        )
        print(f"    - Spawned Node {node}: {path}")
        
    print("--- [Hyperion] Cycle Complete ---")

if __name__ == "__main__":
    # Sample Input (Marketing Brief)
    sample_attractor = {
        "id": "12345678-1234-5678-1234-567812345678",
        "name": "Supra Drift Mode",
        "description": "High-angle drifting physics.",
        "vector_queries": ["drift", "tire friction", "lateral g"],
        "priority": 0.95
    }
    
    run_hyperion_cycle(sample_attractor)
