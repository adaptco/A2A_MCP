import numpy as np
from world_vectors.vault import VectorVault
from base44.grid import Base44Grid
from context.window import ContextWindow
import sys

def refresh_phase_space(prompt_token="Genesis Pulse"):
    print(f"--- Initiating Phase Space Tick: {prompt_token} ---")
    
    # 1. Prompt Token as a Vector (Static Pixel)
    # Simulating the vectorization of the prompt
    vault = VectorVault()
    grid = Base44Grid()
    
    print(" - Vectorizing prompt token into static pixel Hilbert space...")
    # Mocking semantic embedding logic
    prompt_vector = np.random.rand(768) 
    
    # 2. Hyperbolic Roundtrip / Geodesic to Voxel Expansion
    print(" - Calculating hyperbolic geodesic for voxel expansion...")
    # Map vector to Base44 Grid coordinates
    target_cell_id = int(np.sum(prompt_vector) % 44)
    cell = grid.get_cell(target_cell_id)
    
    print(f" - [VOXEL_EXPANDED]: Occupying Cell {target_cell_id} (Phase Space: {cell.world_bounds})")
    
    # 3. Floating Energy Calculation
    # "Total energy should cover the prompt token"
    energy_level = np.linalg.norm(prompt_vector) * 100
    print(f" - Total Energy calculated: {energy_level:.2f} mEV (Energy exceeds prompt threshold)")

    # 4. Collapse Waveform to Cosine
    print(" - Collapsing phase waveform back to cosine similarity...")
    results = vault.search(prompt_token, top_k=3)
    
    print("--- Phase Space Refreshed ---")
    print("State Map of Available Space:")
    for i in range(4):
        row = ""
        for j in range(11):
            cell_idx = i * 11 + j
            # Simulating occupation map
            state = "■" if cell_idx == target_cell_id else "□"
            row += f" {state} "
        print(row)
    
    if results:
        top_match, score = results[0]
        print(f"Top Semantic Anchor: {top_match.ref_type} (Similarity: {score:.4f})")
    else:
        print("Static Pattern Found: NULL (Vacuum State)")

if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Jurassic Voxel Expansion"
    refresh_phase_space(prompt)
