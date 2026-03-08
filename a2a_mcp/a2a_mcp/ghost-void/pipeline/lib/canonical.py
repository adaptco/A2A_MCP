"""
Canonical JSON hashing and ledger management.
Implements RFC8785-style JSON canonicalization for deterministic hashing.
"""

import json
import hashlib
import math
from pathlib import Path
from typing import Any, Dict


def _normalize_numbers(value: Any) -> Any:
    """Normalize numbers so JSON serialization is stable across runtimes."""
    if isinstance(value, bool) or value is None:
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NaN or infinite values are not allowed in canonical JSON")
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
    # Python's json.dumps with separators and sort_keys approximates JCS
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


def hash_canonical_without_integrity(payload: Dict[str, Any]) -> str:
    """
    Hash a payload after stripping the 'integrity_hash' field.
    Re-injects the hash after computation.
    
    Args:
        payload: Dictionary to hash (will be modified in-place)
    
    Returns:
        SHA256 hex digest
    """
    # Remove integrity_hash if present
    payload.pop('integrity_hash', None)
    
    # Compute hash
    canonical = jcs_canonical_bytes(payload)
    hash_value = sha256_hex(canonical)
    
    # Re-inject hash
    payload['integrity_hash'] = hash_value
    
    return hash_value


def append_to_ledger(record: Dict[str, Any], ledger_path: Path) -> None:
    """
    Append a record to the ledger with hash chaining.
    
    Args:
        record: Record to append
        ledger_path: Path to the ledger file (JSONL format)
    """
    # Ensure ledger directory exists
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read last hash if ledger exists
    prev_hash = "0" * 64  # Genesis hash
    if ledger_path.exists():
        with open(ledger_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                last_record = json.loads(lines[-1])
                prev_hash = last_record.get('integrity_hash', prev_hash)
    
    # Add previous hash to record
    record['prev_ledger_hash'] = prev_hash
    
    # Compute integrity hash
    hash_canonical_without_integrity(record)
    
    # Append to ledger
    with open(ledger_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
