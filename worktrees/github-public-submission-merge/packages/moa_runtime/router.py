from typing import Any, Dict, List


def route_experts(policy: Dict[str, Any], intent: str) -> List[str]:
    for rule in policy.get("rules", []):
        if intent in rule.get("intents", []):
            return list(rule.get("experts", []))
    return list(policy.get("default_experts", []))
