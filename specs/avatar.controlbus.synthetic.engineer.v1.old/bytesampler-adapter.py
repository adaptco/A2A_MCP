from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def jcs_dumps(obj: Any) -> str:
    # Minimal stable JSON (JCS-like): sort keys, compact separators.
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_jcs(obj: Any) -> str:
    return sha256_hex(jcs_dumps(obj).encode("utf-8"))


@dataclass(frozen=True)
class SampleResult:
    sample_id: str
    decision_vector: Dict[str, Any]
    vvl_fragment: Dict[str, Any]
    vct_proof: Optional[Dict[str, Any]] = None


class Mulberry32:
    # Deterministic PRNG from a u32 seed (matches common TS mulberry32 behavior).
    def __init__(self, seed_u32: int):
        self.t = seed_u32 & 0xFFFFFFFF

    def next(self) -> float:
        self.t = (self.t + 0x6D2B79F5) & 0xFFFFFFFF
        r = self.t
        r = (r ^ (r >> 15)) * (1 | r) & 0xFFFFFFFF
        r ^= (r + ((r ^ (r >> 7)) * (61 | r) & 0xFFFFFFFF)) & 0xFFFFFFFF
        r ^= (r >> 14)
        return (r & 0xFFFFFFFF) / 4294967296.0


def seed_u32_from_sha256_hex(hex64: str) -> int:
    h = (hex64 or "").lower().replace("0x", "")
    h = (h + "0" * 8)[:8]
    return int(h, 16) & 0xFFFFFFFF


def weighted_choice(rng: Mulberry32, items: List[Tuple[str, float]]) -> str:
    # Fail-closed on invalid weights.
    if not items:
        raise ValueError("weighted_choice: empty items")
    total = 0.0
    for _, w in items:
        if not (w >= 0.0):
            raise ValueError("weighted_choice: negative weight")
        total += w
    if total <= 0.0:
        raise ValueError("weighted_choice: total weight <= 0")

    u = rng.next() * total
    acc = 0.0
    for k, w in items:
        acc += w
        if u <= acc:
            return k
    return items[-1][0]


def sample_covering_tree(
    seed_sha256: str,
    run_id: str,
    covering_tree: Dict[str, Any],
    prev_hash: Optional[str],
    stage_index: int,
    policy_snapshot_ref: str,
    code_version_ref: str,
    mode: str = "WRAP",
) -> SampleResult:
    """
    covering_tree shape (minimal):
      {
        "tree_id": "ct.v1",
        "nodes": {
           "root": { "choices": [{"id":"A","w":1.0},{"id":"B","w":2.0}], "next": {...} }
        }
      }

    Output:
      decision_vector with path + weights + seed
      vvl_fragment append-ready (caller writes to ledger)
    """
    if mode not in ("WRAP", "STRICT"):
        raise ValueError("mode invalid")

    tree_id = covering_tree.get("tree_id")
    nodes = covering_tree.get("nodes")
    root = covering_tree.get("root", "root")

    if not isinstance(tree_id, str) or not tree_id:
        raise ValueError("covering_tree.tree_id required")
    if not isinstance(nodes, dict):
        raise ValueError("covering_tree.nodes required")
    if root not in nodes:
        raise ValueError("covering_tree.root missing in nodes")

    rng = Mulberry32(seed_u32_from_sha256_hex(seed_sha256))

    path: List[str] = []
    weights: List[float] = []

    cur = root
    steps = 0
    max_steps = int(covering_tree.get("max_steps", 32))

    while True:
        if steps >= max_steps:
            break
        node = nodes.get(cur)
        if not isinstance(node, dict):
            raise ValueError(f"node missing: {cur}")

        choices = node.get("choices", [])
        if not isinstance(choices, list) or len(choices) == 0:
            break

        items: List[Tuple[str, float]] = []
        for c in choices:
            cid = c.get("id")
            w = c.get("w")
            if not isinstance(cid, str) or not cid:
                raise ValueError("choice.id invalid")
            if not isinstance(w, (int, float)):
                raise ValueError("choice.w invalid")
            items.append((cid, float(w)))

        chosen = weighted_choice(rng, items)
        path.append(chosen)

        # record normalized-ish weights for trace (not used for choice; only for audit)
        total = sum(w for _, w in items)
        wmap = {k: (w / total) for k, w in items}
        weights.append(wmap.get(chosen, 0.0))

        nxt = node.get("next", {})
        if isinstance(nxt, dict) and chosen in nxt:
            cur = nxt[chosen]
            steps += 1
            continue
        break

    decision_vector = {
        "decision_vector_id": f"dv:{run_id}:{stage_index}:{digest_jcs({'seed':seed_sha256,'path':path,'tree_id':tree_id})[:16]}",
        "seed_sha256": seed_sha256,
        "path": path,
        "weights": weights,
        "tree_id": tree_id,
        "mode": mode
    }

    # VVL fragment (append-only record; wrapper should embed receipt_digest_sha256 later)
    vvl_fragment = {
        "vvl_version": "vvl.record.v1",
        "run_id": run_id,
        "stage": "SAMPLE",
        "stage_index": stage_index,
        "prev_hash": prev_hash,
        "receipt_digest_sha256": None,  # filled by wrapper after receipt is built
        "decision_vector_id": decision_vector["decision_vector_id"],
        "bifurcation": {
            "reason": "NONE",
            "rationale": "",
            "fork_id": f"fork:{run_id}:main"
        },
        "policy_snapshot_ref": policy_snapshot_ref,
        "code_version_ref": code_version_ref
    }

    sample_id = f"sample:{run_id}:{stage_index}:{digest_jcs(decision_vector)[:16]}"
    return SampleResult(sample_id=sample_id, decision_vector=decision_vector, vvl_fragment=vvl_fragment)
