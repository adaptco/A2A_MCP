from __future__ import annotations

import hashlib
import json
import datetime
from typing import Any, Dict, List, Optional, Tuple

def jcs_dumps(obj: Any) -> str:
    """Minimal stable JSON (JCS-like): sort keys, compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_hex(b: bytes) -> str:
    """Computes the lowercase hex representation of the SHA256 hash of a byte string."""
    return hashlib.sha256(b).hexdigest()

def digest_jcs(obj: Any) -> str:
    """Computes the hash of a JSON-serializable object."""
    return sha256_hex(jcs_dumps(obj).encode("utf-8"))

def deterministic_draw(seed: bytes, node_path: str, draw_index: int, total_weight: float) -> float:
    """Derives a deterministic draw value from a hash stream."""
    h = hashlib.sha256()
    h.update(seed)
    h.update(node_path.encode('utf-8'))
    h.update(str(draw_index).encode('utf-8'))
    # Use first 8 bytes of hash for a float value
    draw_bytes = h.digest()[:8]
    draw_int = int.from_bytes(draw_bytes, 'big')
    return (draw_int / (2**64 - 1)) * total_weight

def sample_covering_tree(
    seed: str,
    covering_tree: Dict[str, Any],
    *,
    session_id: str,
    phase: str,
    prev_hash: str,
    constraints: Optional[List[Dict[str, Any]]] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Deterministically samples a path from a covering tree."""
    seed_bytes = seed.encode('utf-8')
    path = []
    weights = []
    decision_records = []
    
    current_node_key = "root"
    draw_index = 0
    
    while current_node_key:
        node = covering_tree.get("nodes", {}).get(current_node_key)
        if not node:
            break
            
        choices = node.get("choices", [])
        if not choices:
            break

        # Normalize candidate ordering
        choices.sort(key=lambda c: c.get('id', ''))
        
        total_weight = sum(c.get("w", 0) for c in choices)
        if total_weight <= 0:
            return {
                "bifurcation": {
                    "status": "forked_refusal",
                    "reason": "invalid_covering_tree"
                }
            }

        draw = deterministic_draw(seed_bytes, current_node_key, draw_index, total_weight)
        
        chosen_item = None
        acc_weight = 0
        for item in choices:
            item_weight = item.get("w", 0)
            if acc_weight + item_weight >= draw:
                chosen_item = item
                break
            acc_weight += item_weight
        
        if not chosen_item:
            chosen_item = choices[-1]

        path.append(chosen_item["id"])
        weights.append(chosen_item["w"])
        
        decision_records.append({
            "node": current_node_key,
            "candidates": choices,
            "normalized_probabilities": [{c["id"]: c["w"]/total_weight} for c in choices],
            "sampled_threshold": draw,
            "selected": chosen_item["id"]
        })

        next_nodes = node.get("next", {})
        current_node_key = next_nodes.get(chosen_item["id"])
        draw_index += 1

    decision_vector = {
        "path": path,
        "weights": weights,
        "records": decision_records
    }
    
    return {
        "sample_id": f"sample_{digest_jcs(decision_vector)}",
        "decision_vector": decision_vector,
        "bifurcation": {
            "status": "ok",
            "reason": ""
        }
    }

def build_vvl_record(
    *,
    session_id: str,
    phase: str,
    prev_hash: str,
    decision_vector: Dict[str, Any],
    bifurcation_reason: str,
    timestamp: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Builds a Versioned Vector Ledger record."""
    if not timestamp:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
    record_core = {
        "session_id": session_id,
        "phase": phase,
        "prev_hash": prev_hash,
        "timestamp": timestamp,
        "decision_vector": decision_vector,
        "bifurcation_reason": bifurcation_reason,
    }
    record_hash = digest_jcs(record_core)
    
    vvl_record = {
        "vvl_id": f"vvl_{record_hash}",
        "record_hash": record_hash,
        **record_core,
        # Compatibility aliases
        "prev_ledger_hash": prev_hash,
        "integrity_hash": record_hash,
    }
    return vvl_record

def to_music_video_control(seed: str, analyzer_output: Dict[str, Any]) -> List[Dict[str, Any]]:
    """(Stub) Converts analyzer output to music video control signals."""
    return []

def to_cici_tool_sequence(seed: str, requested_tools: List[str]) -> List[Dict[str, Any]]:
    """(Stub) Converts requested tools to a CiCi tool sequence."""
    return []
