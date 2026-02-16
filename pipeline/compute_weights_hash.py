#!/usr/bin/env python3
"""
Compute SHA256 hash of model weights for determinism anchoring.
"""

import hashlib
from pathlib import Path
from sentence_transformers import SentenceTransformer

MODEL_ID = "sentence-transformers/all-mpnet-base-v2"


def compute_model_weights_hash(model_id: str) -> str:
    """
    Compute SHA256 hash of model weights.
    
    Args:
        model_id: HuggingFace model identifier
    
    Returns:
        SHA256 hex digest of concatenated weight tensors
    """
    print(f"Loading model: {model_id}")
    model = SentenceTransformer(model_id)
    
    # Collect all model parameters
    hasher = hashlib.sha256()
    
    print("Hashing model parameters...")
    param_count = 0
    for name, param in model.named_parameters():
        # Convert tensor to bytes and update hash
        param_bytes = param.detach().cpu().numpy().tobytes()
        hasher.update(param_bytes)
        param_count += 1
    
    weights_hash = hasher.hexdigest()
    
    print(f"\nModel: {model_id}")
    print(f"Parameters hashed: {param_count}")
    print(f"Weights SHA256: {weights_hash}")
    
    return weights_hash


if __name__ == "__main__":
    weights_hash = compute_model_weights_hash(MODEL_ID)
    
    # Write to file
    output_file = Path("model_weights_hash.txt")
    with open(output_file, 'w') as f:
        f.write(f"Model: {MODEL_ID}\n")
        f.write(f"SHA256: {weights_hash}\n")
    
    print(f"\nHash written to: {output_file}")
