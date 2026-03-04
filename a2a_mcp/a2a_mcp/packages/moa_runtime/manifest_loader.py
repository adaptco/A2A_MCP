import json
from pathlib import Path
from typing import Any, Dict


def load_manifest(path: str) -> Dict[str, Any]:
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    _validate_manifest(manifest)
    return manifest


def _validate_manifest(manifest: Dict[str, Any]) -> None:
    required_fields = ["manifest_id", "retrieval", "vector_index", "embedding"]
    missing = [field for field in required_fields if field not in manifest]
    if missing:
        raise ValueError(f"Manifest missing required fields: {missing}")
