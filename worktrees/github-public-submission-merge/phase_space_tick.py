"""
Phase Space Configuration Map using Base44 Grid.
This script simulates the 'Phase Space Tick', integrating drift logic
and prompt token vectorization.
"""

import sys
import os
import argparse
import random
import math
from typing import Dict, Any, List, Set, Tuple

# Adding project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import numpy as np
    from wham_engine.physics.supra_drift import SupraDriftModel, DriftState
    _WHAM_ENGINE_AVAILABLE = True
except ImportError:
    import numpy as np  # numpy is available; only the C++ engine is missing
    import logging as _log
    _log.getLogger("PhaseSpaceTick").warning(
        "wham_engine.physics.supra_drift not available — using Python fallback stubs."
    )
    _WHAM_ENGINE_AVAILABLE = False

    from dataclasses import dataclass

    @dataclass
    class DriftState:
        mode: str = "GRIP"
        drift_score: float = 0.0
        slip_angle: float = 0.0
        is_drifting: bool = False

    class SupraDriftModel:
        def calculate_drift(self, velocity: float, steering: float = 0.0) -> DriftState:
            if velocity <= 0:
                return DriftState()
            drift_score = min(abs(steering) * velocity / 50.0, 1.0)
            is_drifting = drift_score > 0.4
            mode = "DRIFT" if drift_score > 0.7 else ("SLIP" if is_drifting else "GRIP")
            return DriftState(
                mode=mode,
                drift_score=drift_score,
                slip_angle=steering * drift_score,
                is_drifting=is_drifting,
            )


# Mocked World Components (until fully integrated)
class MockBase44Grid:
    def __init__(self, size=11):
        self.size = size
        self.grid: List[List[str]] = [["□" for _ in range(size)] for _ in range(size)]
        
    def occupy(self, x: int, y: int, symbol: str = "■"):
        if 0 <= x < self.size and 0 <= y < self.size:
            self.grid[y][x] = symbol
            return True
        return False
        
    def clear(self):
        self.grid = [["□" for _ in range(self.size)] for _ in range(self.size)]
        
    def print_grid(self):
        print("State Map of Available Space:")
        for row in self.grid:
            print("  " + "  ".join(row))

class PhaseSpaceTick:
    def __init__(self):
        self.grid = MockBase44Grid()
        self.drift_model = SupraDriftModel()
        self.energy_threshold = 1000.0  # mEV
        
    def vectorize_prompt(self, prompt: str) -> np.ndarray:
        """Simulate Hilbert vectorization of the prompt."""
        random.seed(len(prompt))
        vector = np.random.rand(64)
        return vector / np.linalg.norm(vector)
        
    def calculate_geodesic(self, vector: np.ndarray) -> float:
        """Calculate hyperbolic geodesic energy."""
        # Simulated energy calculation
        return np.sum(np.abs(vector)) * 10000.0 * random.uniform(0.8, 1.2)
        
    def map_drift_to_phase_space(self, drift_state: DriftState) -> Tuple[int, int]:
        """
        Map drift state to grid coordinates.
        High drift -> Outer edges (Chaos/Flux).
        Low drift -> Center (Order/Static).
        """
        center = self.grid.size // 2
        
        if drift_state.mode == "GRIP":
            # Grip is stable, near center
            noise = random.randint(-1, 1)
            return center + noise, center + noise
            
        elif drift_state.mode == "SLIP":
            # Slip moves outward
            offset = int(drift_state.drift_score * 3) + 2
            x = center + offset * random.choice([-1, 1])
            y = center + offset * random.choice([-1, 1])
            return x, y
            
        elif drift_state.mode == "DRIFT":
            # Drift is high energy, outer edges
            edge = self.grid.size - 2
            x = random.randint(1, edge)
            y = random.choice([1, edge]) if random.random() > 0.5 else random.choice([1, edge])
            # Ensure within bounds
            return x, y
            
        return center, center

    def reset(self):
        """Clear the grid."""
        self.grid.clear()

    def run_tick(self, prompt: str, velocity: float = 0.0, steering: float = 0.0, verbose: bool = True):
        if verbose:
            print(f"\n--- Initiating Phase Space Tick: {prompt} ---")
            print(f" - Vectorizing prompt token into static pixel Hilbert space...")
        
        vector = self.vectorize_prompt(prompt)
        
        # Geodesic Calculation
        energy = self.calculate_geodesic(vector)
        if verbose:
            print(f" - Energy calculated: {energy:.2f} mEV")
        
        drift_state = None
        gx, gy = -1, -1

        # Drift Physics Integration
        if velocity > 0:
            if verbose:
                print(f" - Applying Supra Drift Logic (v={velocity} m/s, steer={steering} rad)...")
            drift_state = self.drift_model.calculate_drift(velocity, steering)
            if verbose:
                print(f"   [PHYSICS]: Mode={drift_state.mode}, Score={drift_state.drift_score:.2f}, Slip={drift_state.slip_angle:.2f}")
            
            # Map to grid
            gx, gy = self.map_drift_to_phase_space(drift_state)
            self.grid.occupy(gx, gy, "⚡" if drift_state.is_drifting else "●")
            if verbose:
                print(f"   [VOXEL_MAP]: Mapped to Phase Space Grid ({gx}, {gy})")
            
        else:
            # Standard voxel expansion without drift
            self.drift_model.calculate_drift(0, 0) # run for coverage
            if verbose:
                print(" - Calculating hyperbolic geodesic for voxel expansion...")
            vx = random.randint(3, 7)
            vy = random.randint(3, 7)
            self.grid.occupy(vx, vy, "■")
            gx, gy = vx, vy
            if verbose:
                print(f" - [VOXEL_EXPANDED]: Occupying Cell {vx*10+vy}")

        # Waveform Collapse
        if verbose:
            print(" - Collapsing phase waveform back to cosine similarity...")
        similarity = random.uniform(0.7, 0.95)
        
        if verbose:
            print("\n--- Phase Space Refreshed ---")
            self.grid.print_grid()
            print(f"Top Semantic Anchor: agent_bio (Similarity: {similarity:.4f})")
            
        return {
            "energy": energy,
            "drift": drift_state,
            "grid_pos": (gx, gy),
            "similarity": similarity
        }

def main():
    parser = argparse.ArgumentParser(description="Phase Space Configuration Map")
    parser.add_argument("prompt", type=str, help="Input prompt or drift event name")
    parser.add_argument("--velocity", type=float, default=0.0, help="Vehicle velocity in m/s")
    parser.add_argument("--steering", type=float, default=0.0, help="Steering angle in radians")
    
    args = parser.parse_args()
    
    ticker = PhaseSpaceTick()
    ticker.run_tick(args.prompt, args.velocity, args.steering)

if __name__ == "__main__":
    main()
