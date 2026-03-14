
import pytest
from agents import TesterAgent, GatingAgent, ActionModelingAgent

def test_agent_imports_and_instantiation():
    """Verify that all main agents can be imported and instantiated."""
    tester = TesterAgent()
    gater = GatingAgent()
    modeler = ActionModelingAgent()
    
    assert tester is not None
    assert gater is not None
    assert modeler is not None
