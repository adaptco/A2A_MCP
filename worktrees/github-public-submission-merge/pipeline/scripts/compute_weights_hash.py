"""
Utility to compute SHA256 hash of model weights.
Run this after loading a model to get the deterministic weights hash.
"""
import hashlib
import torch
from sentence_transformers import SentenceTransformer

def compute_weights_hash(model_id: str) -> str:
    """
    Compute SHA256 hash of all model weights.
    
    Args:
        model_id: HuggingFace model identifier
        
    Returns:
        SHA256 hash prefixed with 'sha256:'
    """
    model = SentenceTransformer(model_id)
    
    # Collect all parameter tensors in deterministic order
    hasher = hashlib.sha256()
    
    for name, param in sorted(model.named_parameters()):
        # Convert to bytes in a deterministic way
        param_bytes = param.detach().cpu().numpy().tobytes()
        hasher.update(name.encode('utf-8'))
        hasher.update(param_bytes)
    
    return f"sha256:{hasher.hexdigest()}"

if __name__ == "__main__":
    import sys
    
    model_id = sys.argv[1] if len(sys.argv) > 1 else "sentence-transformers/all-mpnet-base-v2"
    
    print(f"Computing weights hash for: {model_id}")
    weights_hash = compute_weights_hash(model_id)
    print(f"\nWEIGHTS_HASH={weights_hash}")
    print(f"\nAdd this to your docker-compose.yml or .env file")
