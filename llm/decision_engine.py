from typing import Any, Dict
from llm.gemini_client import GeminiClient
from llm.decision_schema import ParkerDecision

DECISION_SCHEMA_HINT: Dict[str, Any] = ParkerDecision.model_json_schema()

class DecisionEngine:
    def __init__(self, client: GeminiClient):
        self.client = client

    def decide(self, system: str, user: str) -> ParkerDecision:
        raw = self.client.generate_json(system=system, user=user, schema_hint=DECISION_SCHEMA_HINT)
        return ParkerDecision.model_validate(raw)
