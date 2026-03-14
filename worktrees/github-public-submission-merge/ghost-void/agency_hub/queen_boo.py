"""
Queen Boo Tensor Manifold Generator

Generates worldline vectors from speedrun trajectories and
fits a geodesic manifold for optimal path synthesis.
"""

import json
import hashlib
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
import numpy as np


@dataclass
class Trajectory:
    """A recorded speedrun trajectory."""
    positions: np.ndarray  # [N, 2] x,y positions
    actions: np.ndarray    # [N, A] action vectors
    rewards: np.ndarray    # [N] reward signals
    timestamps: np.ndarray # [N] frame timestamps
    worldline_id: str = ""
    
    def __post_init__(self):
        if not self.worldline_id:
            self.worldline_id = self._compute_worldline_id()
    
    def _compute_worldline_id(self) -> str:
        """Deterministic ID from trajectory content."""
        data = json.dumps({
            "positions": self.positions.tolist(),
            "actions": self.actions.tolist()
        }).encode()
        return f"wv_{hashlib.sha256(data).hexdigest()[:12]}"


@dataclass
class WorldlineVector:
    """High-dimensional encoding of a trajectory."""
    vector: np.ndarray      # [D] latent representation
    worldline_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def dimension(self) -> int:
        return len(self.vector)


class TensorField:
    """Encodes trajectories into worldline vectors."""
    
    def __init__(self, latent_dim: int = 128):
        self.latent_dim = latent_dim
        # Initialize random projection matrix (for demo)
        self._projection = None
        
    def _init_projection(self, input_dim: int):
        """Lazy initialization of projection matrix."""
        np.random.seed(42)  # Deterministic
        self._projection = np.random.randn(input_dim, self.latent_dim)
        self._projection /= np.linalg.norm(self._projection, axis=0)
    
    def encode(self, trajectory: Trajectory) -> WorldlineVector:
        """Encode trajectory into latent worldline vector."""
        # Flatten trajectory features
        features = np.concatenate([
            trajectory.positions.flatten(),
            trajectory.actions.flatten(),
            trajectory.rewards
        ])
        
        # Project to latent space
        if self._projection is None or self._projection.shape[0] != len(features):
            self._init_projection(len(features))
        
        vector = features @ self._projection
        vector /= np.linalg.norm(vector) + 1e-8  # Normalize
        
        return WorldlineVector(
            vector=vector,
            worldline_id=trajectory.worldline_id,
            metadata={
                "n_frames": len(trajectory.positions),
                "total_reward": float(trajectory.rewards.sum())
            }
        )
    
    def similarity(self, wv1: WorldlineVector, wv2: WorldlineVector) -> float:
        """Cosine similarity between worldline vectors."""
        return float(np.dot(wv1.vector, wv2.vector))


class QueenBoo:
    """
    Tensor manifold for optimal path synthesis.
    
    Fits a geodesic manifold from successful speedrun worldlines
    and generates optimal paths via interpolation.
    """
    
    def __init__(self, worldlines: List[WorldlineVector] = None):
        self.worldlines: List[WorldlineVector] = worldlines or []
        self.manifold_center: np.ndarray = None
        self.manifold_basis: np.ndarray = None
        
        if self.worldlines:
            self._fit_manifold()
    
    def add_worldline(self, wv: WorldlineVector):
        """Add a worldline to the manifold."""
        self.worldlines.append(wv)
        self._fit_manifold()
    
    def _fit_manifold(self):
        """Fit manifold from worldline vectors using PCA."""
        if len(self.worldlines) < 2:
            return
            
        # Stack vectors
        X = np.stack([wv.vector for wv in self.worldlines])
        
        # Compute manifold center
        self.manifold_center = X.mean(axis=0)
        
        # Compute principal components (manifold basis)
        X_centered = X - self.manifold_center
        _, _, Vt = np.linalg.svd(X_centered, full_matrices=False)
        self.manifold_basis = Vt[:min(len(self.worldlines), 8)]  # Top 8 components
    
    def project_to_manifold(self, vector: np.ndarray) -> np.ndarray:
        """Project a vector onto the manifold."""
        if self.manifold_center is None:
            return vector
            
        centered = vector - self.manifold_center
        coords = centered @ self.manifold_basis.T
        projected = coords @ self.manifold_basis + self.manifold_center
        return projected
    
    def geodesic(self, start: WorldlineVector, goal: WorldlineVector, 
                 steps: int = 10) -> List[np.ndarray]:
        """
        Generate geodesic path on manifold between start and goal.
        
        Returns list of interpolated vectors representing optimal path.
        """
        if self.manifold_center is None:
            # Linear interpolation fallback
            return [
                (1 - t) * start.vector + t * goal.vector
                for t in np.linspace(0, 1, steps)
            ]
        
        # Project to manifold coordinates
        start_proj = self.project_to_manifold(start.vector)
        goal_proj = self.project_to_manifold(goal.vector)
        
        # Interpolate on manifold
        path = []
        for t in np.linspace(0, 1, steps):
            point = (1 - t) * start_proj + t * goal_proj
            path.append(point)
        
        return path
    
    def generate_optimal_path(self, start_pos: Tuple[float, float],
                               goal_pos: Tuple[float, float]) -> Dict[str, Any]:
        """
        Generate optimal trajectory from start to goal positions.
        
        Uses manifold geodesic to synthesize action sequence.
        """
        if not self.worldlines:
            return {"error": "No worldlines in manifold"}
        
        # Find closest worldlines to start and goal
        start_array = np.array(start_pos)
        goal_array = np.array(goal_pos)
        
        # Use first and last worldline as reference (simplified)
        start_wv = self.worldlines[0]
        goal_wv = self.worldlines[-1]
        
        # Generate geodesic
        path = self.geodesic(start_wv, goal_wv, steps=20)
        
        return {
            "status": "generated",
            "n_waypoints": len(path),
            "start_worldline": start_wv.worldline_id,
            "goal_worldline": goal_wv.worldline_id,
            "manifold_dim": len(self.manifold_basis) if self.manifold_basis is not None else 0,
            "path_vectors": [p.tolist() for p in path]
        }
    
    def export(self) -> Dict[str, Any]:
        """Export manifold state for serialization."""
        return {
            "n_worldlines": len(self.worldlines),
            "manifold_center": self.manifold_center.tolist() if self.manifold_center is not None else None,
            "worldline_ids": [wv.worldline_id for wv in self.worldlines]
        }


# Factory function for integration with LLM handoff
def create_queen_boo_from_trajectories(trajectories: List[Dict]) -> QueenBoo:
    """Create Queen Boo manifold from trajectory dictionaries."""
    field = TensorField(latent_dim=128)
    worldlines = []
    
    for traj_dict in trajectories:
        trajectory = Trajectory(
            positions=np.array(traj_dict["positions"]),
            actions=np.array(traj_dict["actions"]),
            rewards=np.array(traj_dict["rewards"]),
            timestamps=np.array(traj_dict.get("timestamps", []))
        )
        worldlines.append(field.encode(trajectory))
    
    return QueenBoo(worldlines)


if __name__ == "__main__":
    # Demo: Create manifold from sample trajectories
    sample_trajectories = [
        {
            "positions": [[0, 0], [1, 1], [2, 1], [3, 2]],
            "actions": [[1, 0], [1, 1], [1, 0], [0, 1]],
            "rewards": [0, 0, 1, 10],
            "timestamps": [0, 1, 2, 3]
        },
        {
            "positions": [[0, 0], [1, 0], [2, 0], [3, 1]],
            "actions": [[1, 0], [1, 0], [1, 0], [0, 1]],
            "rewards": [0, 1, 1, 10],
            "timestamps": [0, 1, 2, 3]
        }
    ]
    
    queen_boo = create_queen_boo_from_trajectories(sample_trajectories)
    print("Queen Boo Manifold Created:")
    print(json.dumps(queen_boo.export(), indent=2))
    
    path = queen_boo.generate_optimal_path((0, 0), (3, 2))
    print("\nOptimal Path:")
    print(json.dumps({k: v for k, v in path.items() if k != "path_vectors"}, indent=2))
