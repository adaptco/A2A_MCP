import hashlib
import json
from typing import Any, Dict, List


def _normalize_numbers(value: Any) -> Any:
    """
    Recursively normalize numbers to int if they are integers,
    otherwise keep float representation.
    """
    if isinstance(value, float):
        # Check if float is actually an integer (e.g., 1.0)
        if value.is_integer():
            return int(value)
        return value

    if isinstance(value, list):
        return [_normalize_numbers(item) for item in value]

    if isinstance(value, dict):
        return {key: _normalize_numbers(item) for key, item in value.items()}

    return value


def jcs_canonical_bytes(obj: Any) -> bytes:
    """
    RFC8785-style JSON canonicalization.
    Returns canonical JSON bytes for deterministic hashing.
    """
    normalized_obj = _normalize_numbers(obj)
    canonical_str = json.dumps(
        normalized_obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
        allow_nan=False,
    )
    return canonical_str.encode('utf-8')


def sha256_hex(b: bytes) -> str:
    """
    Compute SHA256 hex digest of bytes.
    """
    return hashlib.sha256(b).hexdigest()


def compute_merkle_root(nodes: List[Dict[str, Any]]) -> str:
    """
    Compute the Merkle Root hash of a list of nodes (canonicalized).
    """
    if not nodes:
        return hashlib.sha256(b"").hexdigest()

    hashes = [sha256_hex(jcs_canonical_bytes(node)) for node in nodes]

    while len(hashes) > 1:
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])
        new_hashes = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i+1]
            new_hashes.append(sha256_hex(combined.encode('utf-8')))
        hashes = new_hashes

    return hashes[0]
