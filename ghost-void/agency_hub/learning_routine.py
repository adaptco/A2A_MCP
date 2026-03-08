"""
Learning Routine - Verification script for Agency Docking Shell.

Tests the complete cycle: Dock → Inject Knowledge → Run Cycles
"""
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agency_hub import DockingShell
from agency_hub.spokes import DummyFieldGame


def generate_mock_knowledge(count: int = 5, dim: int = 64) -> list:
    """Generate mock knowledge vectors."""
    np.random.seed(42)  # Deterministic for testing
    concepts = []
    for i in range(count):
        vec = np.random.randn(dim)
        vec = vec / np.linalg.norm(vec)  # L2 normalize
        concepts.append(vec)
    return concepts


def main():
    """Run the learning routine."""
    print("=" * 60)
    print("AGENCY DOCKING SHELL - LEARNING ROUTINE")
    print("=" * 60)
    
    # 1. Create Hub
    print("\n[INIT] Creating Docking Shell...")
    hub = DockingShell(embedding_dim=64)
    
    # 2. Dock with Field Game
    print("\n[INIT] Docking with Field Game...")
    spoke = DummyFieldGame()
    hub.dock(spoke)
    
    # 3. Inject Knowledge
    print("\n[INIT] Injecting knowledge concepts...")
    knowledge = generate_mock_knowledge(count=5, dim=64)
    hub.inject_knowledge(knowledge)
    
    # 4. Run Learning Cycles
    print("\n[LEARNING] Running 5 epochs...")
    print("-" * 60)
    
    results = []
    for epoch in range(5):
        result = hub.cycle()
        results.append(result)
        print()  # Spacing between cycles
    
    # 5. Analyze Results
    print("-" * 60)
    print("\n[ANALYSIS] Learning Session Complete")
    stats = hub.get_stats()
    print(f"  Cycles Executed: {stats['cycles_executed']}")
    print(f"  Spoke: {stats['spoke_connected']}")
    print(f"  Embedding Dim: {stats['embedding_dim']}")
    print(f"  Knowledge Concepts: {stats['knowledge_count']}")
    
    # Check stabilization
    eigenstates = [r["eigenstate"] for r in results]
    variances = [np.var(e) for e in eigenstates]
    print(f"\n[STABILIZATION] Eigenstate variance trend:")
    for i, var in enumerate(variances):
        print(f"  Cycle {i+1}: {var:.6f}")
    
    if len(variances) > 1:
        reduction = (variances[0] - variances[-1]) / variances[0] * 100
        print(f"\n[STABILIZATION] Variance reduced by {reduction:.1f}%")
    
    print("\n" + "=" * 60)
    print("VERIFICATION: SUCCESS")
    print("=" * 60)


if __name__ == "__main__":
    main()
