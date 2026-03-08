"""
DummyFieldGame - Test implementation of SpokeAdapter.

A simple mock environment for testing the Agency Hub.
"""
import random
from typing import Dict, Any
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agency_hub.spoke_adapter import SpokeAdapter


class DummyFieldGame(SpokeAdapter):
    """Mock Field Game for testing."""
    
    def __init__(self):
        self.position = {"x": 0.0, "y": 0.0}
        self.tiles = [
            {"bounds": {"min": {"x": -100, "y": 10}, "max": {"x": 100, "y": 15}}},
            {"bounds": {"min": {"x": 50, "y": 5}, "max": {"x": 70, "y": 6}}}
        ]
        self.state_hash = "GENESIS_DUMMY"
        self.action_count = 0
        
    def observe(self) -> Dict[str, Any]:
        """Return current state."""
        return {
            "position": self.position,
            "tiles": self.tiles,
            "state_hash": self.state_hash,
            "action_count": self.action_count
        }
    
    def act(self, token: Dict[str, Any]) -> bool:
        """Execute action token."""
        action = token.get("action", "unknown")
        params = token.get("params", {})
        
        self.action_count += 1
        
        if action == "explore":
            # Random walk
            self.position["x"] += random.uniform(-10, 10)
            self.position["y"] += random.uniform(-10, 10)
            self.state_hash = f"STATE_{self.action_count}"
            return True
            
        elif action == "spawn_structure":
            # Add a new tile
            new_tile = {
                "bounds": {
                    "min": {"x": random.randint(-50, 50), "y": random.randint(0, 10)},
                    "max": {"x": random.randint(60, 100), "y": random.randint(11, 15)}
                }
            }
            self.tiles.append(new_tile)
            self.state_hash = f"STATE_{self.action_count}_SPAWN"
            return True
            
        return False
    
    def get_state_schema(self) -> Dict[str, Any]:
        """Return state schema."""
        return {
            "position": {"type": "dict", "keys": ["x", "y"]},
            "tiles": {"type": "list", "item_type": "dict"},
            "state_hash": {"type": "str"},
            "action_count": {"type": "int"}
        }
