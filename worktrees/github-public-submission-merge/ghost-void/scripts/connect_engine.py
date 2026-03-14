
import sys
import os
import time
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agency_hub.docking_shell import DockingShell
from agency_hub.spokes.ghost_void_spoke import GhostVoidSpoke

def main():
    engine_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "bin", "Debug", "ghost-void_engine.exe"
    )
    
    # Check if engine exists, if not try release or just bin
    if not os.path.exists(engine_path):
        engine_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "bin", "ghost-void_engine.exe"
    )
    
    print(f"Connecting to Engine at: {engine_path}")
    
    try:
        spoke = GhostVoidSpoke(binary_path=engine_path)
        shell = DockingShell()
        shell.dock(spoke)
        
        # Simple Loop
        commands = [
            {"action": "drive", "params": {"velocity": 10.0, "steering": 0.0}},
            {"action": "drive", "params": {"velocity": 20.0, "steering": 0.5}},
            {"action": "drive", "params": {"velocity": 0.0, "steering": 0.0}}
        ]
        
        for cmd in commands:
            print(f"\nSending Command: {cmd}")
            success = spoke.act(cmd)
            state = spoke.observe()
            print(f"Success: {success}")
            print(f"Spoke State: {state}")
            time.sleep(0.5)
            
        print("\nConnection Verification Complete.")
        
    except Exception as e:
        print(f"Verification Failed: {e}")

if __name__ == "__main__":
    main()
