"""
Ghost Void Spoke
Wraps the World Model (Base44) and Drift Logic for Agentic Interaction.
"""

from typing import Dict, Any, Tuple
import sys
import os
import subprocess
import json
import threading

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agency_hub.spoke_adapter import SpokeAdapter
from phase_space_tick import PhaseSpaceTick

class GhostVoidSpoke(SpokeAdapter):
    """
    Connects the Agency Docking Shell to the Ghost Void Engine via PhaseSpaceTick simulation.
    """
    
    def __init__(self, binary_path: str = None):
        self.binary_path = binary_path
        self.process = None
        
        if self.binary_path and os.path.exists(self.binary_path):
             self._start_subprocess()
        else:
             self.world = PhaseSpaceTick()
             print("GhostVoidSpoke: Initialized. Connected to PhaseSpaceTick (Python Simulation).")
        self.current_state = {
            "energy": 0.0,
            "drift_mode": "GRIP",
            "grid_pos": (5, 5),
            "similarity": 0.0
        }

    def __str__(self):
        if self.process:
            return f"GhostVoidSpoke: Connected to Engine at {self.binary_path}"
        return "GhostVoidSpoke: Connected to PhaseSpaceTick (Python Simulation)."
    def _start_subprocess(self):
        """Spawn the C++ engine process."""
        try:
            self.process = subprocess.Popen(
                [self.binary_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1 # Line buffered
            )
            print(f"GhostVoidSpoke: Connected to Engine at {self.binary_path}")
            
            # Consume initial output
            if self.process.stdout:
                print(f"Engine Output: {self.process.stdout.readline().strip()}") 
                print(f"Engine Output: {self.process.stdout.readline().strip()}") 
                
        except Exception as e:
            print(f"Failed to start engine: {e}")
            self.process = None
            self.world = PhaseSpaceTick()

    def observe(self) -> Dict[str, Any]:
        """
        Return current state of the Phase Space.
        """
        return self.current_state

    def act(self, token: Dict[str, Any]) -> bool:
        """
        Execute action token.
        Token Expected: {"action": "drive", "params": {"velocity": float, "steering": float, "prompt": str}}
        """
        action_type = token.get("action")
        params = token.get("params", {})
        
        if self.process:
            # C++ Engine Bridge
            cmd = json.dumps(token)
            try:
                self.process.stdin.write(cmd + "\n")
                self.process.stdin.flush()
                
                # Synchronous read for 'Tick' protocol
                response = self.process.stdout.readline()
                if response:
                    data = json.loads(response)
                    self.current_state["last_engine_response"] = data
                    # For now, we trust the engine is alive. 
                    # Real simulation would parse pos/energy from 'data'
                    return True
            except Exception as e:
                print(f"Engine Communication Error: {e}")
                return False

        elif action_type == "drive":
            vel = params.get("velocity", 0.0)
            steer = params.get("steering", 0.0)
            prompt = params.get("prompt", "Agent Drive")
            
            result = self.world.run_tick(prompt, vel, steer, verbose=False)
            
            # Map result back to state schema
            drift_state = result["drift"]
            mode = drift_state.mode if drift_state else "STATIC"
            
            self.current_state = {
                "energy": result["energy"],
                "drift_mode": mode,
                "grid_pos": result["grid_pos"],
                "similarity": result["similarity"]
            }
            return True
            
        elif action_type == "reset":
            if self.process:
                 pass # Send reset command to engine if supported
            else:
                self.world.reset()
                self.current_state["grid_pos"] = (5, 5)
                self.current_state["drift_mode"] = "GRIP"
            return True
            
        print(f"GhostVoidSpoke: Unknown action '{action_type}'")
        return False

    def get_state_schema(self) -> Dict[str, str]:
        return {
            "energy": "float",
            "drift_mode": "string",
            "grid_pos": "tuple(int, int)",
            "similarity": "float"
        }
