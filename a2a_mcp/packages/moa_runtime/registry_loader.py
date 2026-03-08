import json
from pathlib import Path
from typing import Any, Dict, Optional


def load_registry(path: str) -> Dict[str, Any]:
    registry_path = Path(path)
    with registry_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def select_agent(registry: Dict[str, Any], project_id: str, vertical_id: str) -> Optional[Dict[str, Any]]:
    for agent in registry.get("agents", []):
        if agent.get("project_id") == project_id and agent.get("vertical_id") == vertical_id:
            return agent
    return None
