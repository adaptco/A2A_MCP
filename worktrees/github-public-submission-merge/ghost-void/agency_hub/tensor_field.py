"""
TensorField - Voxelized state management and eigen-embedding.

Handles the mathematical core of state normalization:
- Voxelization: Converts arbitrary states to n-dimensional tensors
- Eigenstate: Normalizes variance via PCA/SVD
- RAG Unification: Maps eigenstate to knowledge vectors
"""
import numpy as np
from typing import Dict, List, Any, Optional
from sklearn.decomposition import PCA


class TensorField:
    """Manages voxelized state and eigen-embedding for cognitive manifold."""
    
    def __init__(self, embedding_dim: int = 64, voxel_resolution: int = 16):
        """
        Initialize TensorField.
        
        Args:
            embedding_dim: Dimensionality of the eigenstate manifold
            voxel_resolution: Resolution for spatial voxelization
        """
        self.embedding_dim = embedding_dim
        self.voxel_resolution = voxel_resolution
        self.pca = PCA(n_components=embedding_dim)
        self.is_fitted = False
        self.knowledge_vectors: List[np.ndarray] = []
        
    def voxelize_state(self, raw_state: Dict[str, Any]) -> np.ndarray:
        """
        Convert arbitrary state dictionary to voxelized tensor.
        
        Args:
            raw_state: Dictionary containing environmental state
            
        Returns:
            Flattened voxel tensor
        """
        # Extract numerical features from state
        features = []
        
        # Handle common state patterns
        if "position" in raw_state:
            pos = raw_state["position"]
            if isinstance(pos, dict):
                features.extend([pos.get("x", 0), pos.get("y", 0)])
            elif isinstance(pos, (list, tuple)):
                features.extend(pos[:2])
                
        if "tiles" in raw_state:
            # Voxelize tile positions
            tiles = raw_state["tiles"]
            if isinstance(tiles, list):
                # Create spatial grid
                grid = np.zeros((self.voxel_resolution, self.voxel_resolution))
                for tile in tiles[:100]:  # Limit for performance
                    if isinstance(tile, dict) and "bounds" in tile:
                        bounds = tile["bounds"]
                        # Normalize to grid coordinates
                        x = int((bounds.get("min", {}).get("x", 0) + 200) / 400 * self.voxel_resolution)
                        y = int((bounds.get("min", {}).get("y", 0) + 200) / 400 * self.voxel_resolution)
                        x = np.clip(x, 0, self.voxel_resolution - 1)
                        y = np.clip(y, 0, self.voxel_resolution - 1)
                        grid[y, x] = 1.0
                features.extend(grid.flatten())
                
        if "state_hash" in raw_state:
            # Convert hash to numerical features
            hash_val = raw_state["state_hash"]
            if isinstance(hash_val, str):
                # Simple hash to numbers
                hash_num = sum(ord(c) for c in hash_val[:8])
                features.append(hash_num / 1000.0)
                
        # Pad or truncate to fixed size
        target_size = self.voxel_resolution * self.voxel_resolution + 10
        if len(features) < target_size:
            features.extend([0.0] * (target_size - len(features)))
        else:
            features = features[:target_size]
            
        return np.array(features, dtype=np.float32)
    
    def compute_eigenstate(self, voxel_tensor: np.ndarray) -> np.ndarray:
        """
        Normalize variance via PCA to create stable eigenstate.
        
        Args:
            voxel_tensor: Flattened voxel representation
            
        Returns:
            Eigenstate vector (normalized)
        """
        # For single samples, we can't fit PCA properly
        # Instead, use a simple projection to the embedding dimension
        if not self.is_fitted:
            # Create a simple random projection matrix for initialization
            input_dim = len(voxel_tensor)
            self.projection_matrix = np.random.randn(input_dim, self.embedding_dim) / np.sqrt(input_dim)
            self.is_fitted = True
            
        # Project to eigenstate
        eigenstate = np.dot(voxel_tensor, self.projection_matrix)
        
        # L2 normalize
        norm = np.linalg.norm(eigenstate)
        if norm > 1e-8:
            eigenstate = eigenstate / norm
            
        return eigenstate
    
    def rag_unify(self, eigenstate: np.ndarray, top_k: int = 3) -> Dict[str, Any]:
        """
        Map eigenstate to knowledge vectors via dot-product similarity.
        
        Args:
            eigenstate: Normalized eigenstate vector
            top_k: Number of top knowledge vectors to retrieve
            
        Returns:
            Dictionary with unified state and retrieved knowledge
        """
        if not self.knowledge_vectors:
            return {
                "eigenstate": eigenstate.tolist(),
                "knowledge_retrieved": [],
                "similarity_scores": []
            }
            
        # Compute cosine similarity with all knowledge vectors
        similarities = []
        for i, kv in enumerate(self.knowledge_vectors):
            # Ensure same dimensionality
            if len(kv) != len(eigenstate):
                continue
            sim = np.dot(eigenstate, kv)
            similarities.append((i, sim))
            
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_matches = similarities[:top_k]
        
        return {
            "eigenstate": eigenstate.tolist(),
            "knowledge_retrieved": [idx for idx, _ in top_matches],
            "similarity_scores": [float(score) for _, score in top_matches]
        }
    
    def inject_knowledge(self, concepts: List[np.ndarray]):
        """
        Prime the RAG system with knowledge vectors.
        
        Args:
            concepts: List of embedding vectors representing concepts
        """
        self.knowledge_vectors = concepts
        print(f"[TENSOR_FIELD] Injected {len(concepts)} knowledge concepts")
        
    def get_embedding_dim(self) -> int:
        """Return dimensionality of the eigenstate manifold."""
        return self.embedding_dim
