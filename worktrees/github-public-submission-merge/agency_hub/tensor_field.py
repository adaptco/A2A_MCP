"""
Tensor Field: Cognitive Manifold
Normalize raw observations into a shared vector space.
"""

import numpy as np
from typing import Dict, Any, List
import hashlib
import json

class TensorField:
    """
    Manages the translation between Raw State (Spoke) -> Voxel Tensor -> Eigenstate (Manifold).
    """
    
    def __init__(self, embedding_dim: int = 64):
        self.embedding_dim = embedding_dim
        # Simple projection matrix for "hashing" raw data into vector space
        # In a real system, this would be a trained encoder (VAE/BERT)
        self.projection_seed = 42
        
    def voxelize_state(self, raw_state: Dict[str, Any]) -> np.ndarray:
        """
        Convert arbitrary dictionary state into a fixed-size tensor.
        Uses deterministic hashing to map keys/values to tensor indices.
        """
        # Linearize state
        flat_state = self._flatten_dict(raw_state)
        
        # Initialize tensor
        tensor = np.zeros(self.embedding_dim)
        
        for key, value in flat_state.items():
            # Hash key to index
            idx = int(hashlib.sha256(key.encode()).hexdigest(), 16) % self.embedding_dim
            
            # Hash value to magnitude (normalize simply)
            if isinstance(value, (int, float)):
                mag = float(value)
            elif isinstance(value, str):
                mag = float(len(value)) # Semantic len heuristic
            elif isinstance(value, bool):
                mag = 1.0 if value else -1.0
            else:
                mag = 0.0
                
            # Add to tensor (superposition)
            tensor[idx] += mag
            
        return tensor
        
    def compute_eigenstate(self, voxel_tensor: np.ndarray) -> np.ndarray:
        """
        Normalize the tensor to unit length (L2 norm) to create an 'Eigenstate'.
        """
        norm = np.linalg.norm(voxel_tensor)
        if norm == 0:
            return voxel_tensor
        return voxel_tensor / norm
        
    def rag_unify(self, eigenstate: np.ndarray, knowledge_base: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        Compute cosine similarity between current eigenstate and known concepts.
        """
        similarities = {}
        for concept, vector in knowledge_base.items():
            # Cosine similarity: (A . B) / (|A| |B|)
            # Assuming vectors are unit normalized
            sim = np.dot(eigenstate, vector)
            similarities[concept] = float(sim)
            
        return similarities
        
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, (dict, list)):
                         # simplified, ignore complex nested lists for now
                         raise NotImplementedError("Nested lists or dicts within lists are not supported.")
                    else:
                        items.append((f"{new_key}_{i}", item))
            else:
                items.append((new_key, v))
        return dict(items)
