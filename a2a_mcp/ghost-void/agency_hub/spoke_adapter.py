"""
SpokeAdapter - Abstract Base Class for Field Games.

Any environment ("Spoke") that wants to dock with the Agency Hub
must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class SpokeAdapter(ABC):
    """Abstract interface for Field Game environments."""
    
    @abstractmethod
    def observe(self) -> Dict[str, Any]:
        """
        Return current environmental state.
        
        Returns:
            Dictionary containing observable state (positions, tiles, etc.)
        """
        pass
    
    @abstractmethod
    def act(self, token: Dict[str, Any]) -> bool:
        """
        Execute an action token in the environment.
        
        Args:
            token: Action dictionary with "action" and "params" keys
            
        Returns:
            True if action executed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_state_schema(self) -> Dict[str, Any]:
        """
        Return schema describing the state structure.
        
        Returns:
            Dictionary describing expected state keys and types
        """
        pass
    
    def get_name(self) -> str:
        """Return human-readable name of this spoke."""
        return self.__class__.__name__
