import pytest
from llm.decision_engine import DecisionEngine
from llm.decision_schema import ParkerDecision

class FakeClient:
    def __init__(self, fixed_response: dict):
        self.fixed_response = fixed_response

    def generate_json(self, system: str, user: str, schema_hint: dict) -> dict:
        return self.fixed_response

def test_decision_engine_valides_schema():
    # Setup a valid raw response
    raw_valid = {
        "action": "continue",
        "rationale": "Path is clear.",
        "confidence": 0.95
    }
    
    engine = DecisionEngine(client=FakeClient(raw_valid))
    decision = engine.decide(system="test_sys", user="test_user")
    
    assert isinstance(decision, ParkerDecision)
    assert decision.action == "continue"
    assert decision.rationale == "Path is clear."
    assert decision.confidence == 0.95

def test_decision_engine_invalid_schema():
    # Setup an invalid raw response (missing confidence)
    raw_invalid = {
        "action": "continue",
        "rationale": "Feeling lucky"
    }
    
    engine = DecisionEngine(client=FakeClient(raw_invalid))
    
    with pytest.raises(Exception):
        engine.decide(system="sys", user="user")
