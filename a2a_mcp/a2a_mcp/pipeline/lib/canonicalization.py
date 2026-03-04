"""
Canonicalization module.
"""
import json
import hashlib
from typing import Dict, Any, List

def canonicalize_docling_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms a single Docling node into a canonical representation.
    Ensures sorted keys and stable IDs for deterministic hashing.
    """
    # 1. Clean whitespace and non-deterministic attributes
    text = str(node.get("text", "")).strip()

    # 2. Extract stable metadata
    metadata = node.get("metadata", {})
    source = metadata.get("source", "unknown")
    page = metadata.get("page", 0)

    # 3. Create a canonical JSON structure
    canonical = {
        "text": text,
        "source": source,
        "page": page,
        "provenance": metadata.get("provenance", "Docling_v1")
    }

    # 4. Sort keys for deterministic JSON serialization
    serialized = json.dumps(canonical, sort_keys=True)

    # 5. Assign content-addressed ID (SHA-256)
    node_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    canonical["id"] = node_hash

    return canonical

def canonicalize_batch(batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Canonicalizes a list of Docling nodes and sorts them by their hash ID.
    """
    canonical_list = [canonicalize_docling_node(n) for n in batch]
    # Sort by ID to ensure batch-level determinism
    canonical_list.sort(key=lambda x: x["id"])
    return canonical_list

def get_batch_hash(canonical_batch: List[Dict[str, Any]]) -> str:
    """
    Compute a SHA-256 hash for an entire canonicalized batch.
    """
    serialized = json.dumps(canonical_batch, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
