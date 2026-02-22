import hashlib
import json
import re
from typing import Dict, Iterable, List


def canonical_json(data: Dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def compute_contract_hash(agent: Dict, routing: Dict, expert: Dict, manifest: Dict) -> str:
    manifest_copy = dict(manifest)
    manifest_copy.pop("contract_hash", None)
    material = (
        canonical_json(agent)
        + canonical_json(routing)
        + canonical_json(expert)
        + canonical_json(manifest_copy)
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def deterministic_embedding(text: str, dim: int = 1536) -> List[float]:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    seed = int(digest[:16], 16) % (2**31)
    # Simple LCG for deterministic float generation
    values: List[float] = []
    state = seed
    for _ in range(dim):
        state = (1103515245 * state + 12345) % (2**31)
        values.append(state / float(2**31))
    # L2 normalize
    norm = sum(v * v for v in values) ** 0.5 or 1.0
    return [v / norm for v in values]


def validate_response_has_citations(text: str, thread_ids: Iterable[str]) -> bool:
    if not thread_ids:
        return True
    citation_pattern = re.compile(r"\\[(" + "|".join(map(re.escape, thread_ids)) + r")\\]")
    for line in text.splitlines():
        if line.strip() and not citation_pattern.search(line):
            return False
    return True
