from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(data: Any) -> str:
    """Return deterministic JSON encoding for hashing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(payload: str | bytes) -> str:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def deterministic_seed(*parts: str) -> int:
    material = "::".join(parts)
    # avoid Python's process-randomized hash(); keep deterministic across runs
    return int(sha256_hex(material)[:16], 16)
