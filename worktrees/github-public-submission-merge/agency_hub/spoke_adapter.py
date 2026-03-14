"""
Spoke Adapter Base Class
Defines the interface for all Field Game Spokes.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List

class SpokeAdapter(ABC):
    """
    Abstract Base Class for integrating external environments (Spokes)
    into the Agency Docking Shell.
    """
    
    @abstractmethod
    def observe(self) -> Dict[str, Any]:
        """
        Return current environmental state as a JSON-serializable dictionary.
        This raw state will be normalized by the TensorField.
        """
        pass
        
    @abstractmethod
    def act(self, token: Dict[str, Any]) -> bool:
        """
        Execute an action token.
        
        Args:
            token: A dictionary containing 'action' and 'params'.
            
        Returns:
            bool: True if action was successfully executed.
        """
        pass
        
    @abstractmethod
    def get_state_schema(self) -> Dict[str, str]:
        """
        Return a schema defining the expected structure of the state.
        Mapping of key -> type (e.g., 'position': 'vector3').
        """
        pass

    def teardown(self):
        """Optional cleanup method."""
        pass
