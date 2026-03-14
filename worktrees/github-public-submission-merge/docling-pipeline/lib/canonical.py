"""
Canonicalization and hashing utilities for deterministic document processing.
Implements JCS-like canonicalization (RFC 8785) for hash-chain integrity.
"""
import hashlib
import json
from typing import Any


def jcs_canonical_bytes(obj: dict) -> bytes:
    """
    Convert a dictionary to canonical JSON bytes (JCS-like).
    - Keys sorted recursively
    - No whitespace
    - UTF-8 encoded
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Compute SHA-256 hash and return as hex string."""
    return hashlib.sha256(data).hexdigest()


def hash_canonical(payload: dict) -> str:
    """Hash a dictionary after canonical serialization."""
    return sha256_hex(jcs_canonical_bytes(payload))


def hash_canonical_without_integrity(payload: dict) -> str:
    """
    Hash payload excluding the 'integrity' field.
    Used to compute sha256_canonical before injecting it back.
    """
    tmp = dict(payload)
    tmp.pop("integrity", None)
    return sha256_hex(jcs_canonical_bytes(tmp))


def compute_doc_id(content: bytes) -> str:
    """Compute document ID from raw content bytes."""
    return f"sha256:{sha256_hex(content)}"


def compute_chunk_id(doc_id: str, chunk_index: int, chunk_text: str) -> str:
    """Compute chunk ID from document ID and chunk content."""
    data = f"{doc_id}:{chunk_index}:{chunk_text}".encode("utf-8")
    return f"sha256:{sha256_hex(data)}"
