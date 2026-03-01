"""
Integration Test for GhostVoidSpoke
Verifies the Agency Docking Shell can cycle with the World Model.
"""

import sys
import os
import json

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agency_hub.docking_shell import DockingShell
from agency_hub.spokes.ghost_void_spoke import GhostVoidSpoke

def test_integration():
    print("--- Testing GhostVoidSpoke Integration ---")
    
    # 1. Initialize
    shell = DockingShell()
    spoke = GhostVoidSpoke()
    
    # 2. Dock
    shell.dock(spoke)
    
    # 3. Inject Knowledge (Simulated Policy)
    shell.inject_knowledge("fast_drift", [0.8, 0.5, -0.2] + [0.0]*61)
    print("[INIT] Knowledge Injected.")
    
    # 4. Run Cycle (Manual Action Override for Test)
    print("\n[CYCLE 1] Observing...")
    # Override policy for deterministic test
    # In a real cycle, shell._synthesize_token would use vectors
    token = {
        "action": "drive",
        "params": {
            "velocity": 45.0,
            "steering": 0.8,
            "prompt": "Test Drift Integration"
        }
    }
    
    success = spoke.act(token)
    state = spoke.observe()
    
    print(f"[RESULT] Success: {success}")
    print(f"[STATE] Mode: {state.get('drift_mode')}, Grid: {state.get('grid_pos')}")
    
    assert success is True
    assert state.get("drift_mode") in ["DRIFT", "SLIP", "GRIP"]
    
    print("\n✅ Integration Test Passed!")

if __name__ == "__main__":
    test_integration()
