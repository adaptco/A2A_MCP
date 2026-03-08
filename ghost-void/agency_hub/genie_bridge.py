import logging
from typing import Dict, Any
from agency_hub.spoke_adapter import SpokeAdapter

logger = logging.getLogger(__name__)

class GenieBridge:
    """
    Translates WASD keyboard intents into GameEngine actions via the Qube protocol.
    Provides a low-latency simulation interface for agent exploration.
    """
    
    ACTION_MAP = {
        "w": {"action": "move", "params": {"direction": "up", "magnitude": 1.0}},
        "a": {"action": "move", "params": {"direction": "left", "magnitude": 1.0}},
        "s": {"action": "move", "params": {"direction": "down", "magnitude": 1.0}},
        "d": {"action": "move", "params": {"direction": "right", "magnitude": 1.0}},
        "space": {"action": "interact", "params": {"type": "primary"}},
        "e": {"action": "interact", "params": {"type": "secondary"}}
    }

    def __init__(self, spoke: SpokeAdapter):
        self.spoke = spoke
        self.last_intent = None

    async def handle_intent(self, intent: str) -> bool:
        """
        Processes a WASD intent and executes the corresponding engine action.
        """
        action_data = self.ACTION_MAP.get(intent.lower())
        if not action_data:
            logger.warning(f"Unknown intent received by GenieBridge: {intent}")
            return False

        self.last_intent = intent
        logger.debug(f"GenieBridge translating {intent} -> {action_data}")
        
        # Execute via Spoke (which uses Qube execute_action)
        return self.spoke.act(action_data)

    def get_explorer_projection(self) -> Dict[str, Any]:
        """
        Returns a 'Genie-style' projection of the current world state.
        This provides the Foundation Model with a spatial representation of its surroundings.
        """
        raw_state = self.spoke.observe()
        
        # In a real implementation, this might include Voxel data or a mini-map
        projection = {
            "view_type": "top_down_voxel",
            "last_intent": self.last_intent,
            "local_passability": raw_state.get("passability", {}),
            "nearby_entities": raw_state.get("entities", []),
            "timestamp": raw_state.get("timestamp")
        }
        return projection
