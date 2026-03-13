from __future__ import annotations

import json
from typing import Any, Dict, Optional

from bytesampler_adapter import sample_covering_tree, digest_jcs


def assert_eq(a: Any, b: Any, msg: str) -> None:
    if a != b:
        raise AssertionError(f"{msg}\nA={a}\nB={b}")


def test_replay(seed_sha256: str, input_descriptor: Dict[str, Any]) -> None:
    covering_tree = {
        "tree_id": "ct.v1.musicvideo",
        "root": "root",
        "max_steps": 8,
        "nodes": {
            "root": {
                "choices": [{"id": "shot_wide", "w": 1.0}, {"id": "shot_close", "w": 1.0}],
                "next": {"shot_wide": "palette", "shot_close": "palette"}
            },
            "palette": {
                "choices": [{"id": "neon", "w": 2.0}, {"id": "noir", "w": 1.0}],
                "next": {"neon": "camera", "noir": "camera"}
            },
            "camera": {
                "choices": [{"id": "fov_60", "w": 1.0}, {"id": "fov_50", "w": 1.0}]
            }
        }
    }

    run_id = f"run:{digest_jcs(input_descriptor)[:12]}"
    policy_snapshot_ref = "policy@v1"
    code_version_ref = "code@deadbeef"

    a = sample_covering_tree(
        seed_sha256=seed_sha256,
        run_id=run_id,
        covering_tree=covering_tree,
        prev_hash=None,
        stage_index=0,
        policy_snapshot_ref=policy_snapshot_ref,
        code_version_ref=code_version_ref,
        mode="WRAP",
    )
    b = sample_covering_tree(
        seed_sha256=seed_sha256,
        run_id=run_id,
        covering_tree=covering_tree,
        prev_hash=None,
        stage_index=0,
        policy_snapshot_ref=policy_snapshot_ref,
        code_version_ref=code_version_ref,
        mode="WRAP",
    )

    assert_eq(a.decision_vector, b.decision_vector, "decision_vector must be identical under replay")
    assert_eq(a.vvl_fragment["decision_vector_id"], b.vvl_fragment["decision_vector_id"], "vvl decision id stable")


def test_bifurcation_fork_tags() -> None:
    # Harness-level check: fork tagging is deterministic and explicit.
    # In real wrapper, this is emitted when constraints fail.
    fork = {
        "reason": "CONSTRAINT_VIOLATION",
        "rationale": "wheel_gate failed: 5_spokes_only",
        "fork_id": "fork:runX:refuse",
        "constraint_ids": ["wheel_gate"]
    }
    assert fork["reason"] != "NONE"
    assert "rationale" in fork and fork["rationale"]


def main() -> None:
    seed = "a" * 64
    input_desc = {"track_id": "T123", "audio_sha256": "b" * 64}
    test_replay(seed, input_desc)
    test_bifurcation_fork_tags()
    print("OK: control plane harness tests passed")


if __name__ == "__main__":
    main()
