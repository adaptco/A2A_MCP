from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from copy import deepcopy

from bytesampler_adapter import sample_covering_tree, build_vvl_record, digest_jcs

def assert_eq(a: any, b: any, msg: str):
    if a != b:
        raise AssertionError(f"{msg}")

def test_replay():
    print("Running test: test_replay")
    seed = "a" * 64
    covering_tree = {
        "tree_id": "ct.v1.musicvideo",
        "root": "root",
        "nodes": {
            "root": {"choices": [{"id": "wide", "w": 1}, {"id": "close", "w": 1}], "next": {"wide": "palette", "close": "palette"}},
            "palette": {"choices": [{"id": "neon", "w": 2}, {"id": "noir", "w": 1}], "next": {"neon": "camera", "noir": "camera"}},
            "camera": {"choices": [{"id": "fov_60", "w": 1}, {"id": "fov_50", "w": 1}]}
        }
    }
    
    res1 = sample_covering_tree(seed, covering_tree, session_id="s1", phase="SAMPLE", prev_hash="0"*64)
    res2 = sample_covering_tree(seed, covering_tree, session_id="s1", phase="SAMPLE", prev_hash="0"*64)

    assert_eq(res1["decision_vector"], res2["decision_vector"], "Replay should yield identical decision vectors")
    print("... PASSED")

def test_bifurcation():
    print("Running test: test_bifurcation")
    seed = "a" * 64
    covering_tree = {
        "tree_id": "ct.v1.musicvideo",
        "root": "root",
        "nodes": { "root": {"choices": [{"id": "wide", "w": 0}, {"id": "close", "w": 0}]} }
    }
    
    res = sample_covering_tree(seed, covering_tree, session_id="s2", phase="SAMPLE", prev_hash="0"*64)
    assert_eq(res["bifurcation"]["status"], "forked_refusal", "Bifurcation status should be 'forked_refusal'")
    assert_eq(res["bifurcation"]["reason"], "invalid_covering_tree", "Bifurcation reason should be 'invalid_covering_tree'")
    print("... PASSED")

def test_multimodel_ensemble():
    print("Running test: test_multimodel_ensemble")
    seed = "b" * 64
    tree1 = {
        "tree_id": "ct.v1.ensemble",
        "root": "root",
        "nodes": { "root": {"choices": [{"id": "model_a", "w": 1}, {"id": "model_b", "w": 2}]} }
    }
    tree2 = deepcopy(tree1)
    tree2["nodes"]["root"]["choices"].reverse()

    res1 = sample_covering_tree(seed, tree1, session_id="s3", phase="SAMPLE", prev_hash="0"*64)
    res2 = sample_covering_tree(seed, tree2, session_id="s3", phase="SAMPLE", prev_hash="0"*64)
    
    assert_eq(res1["decision_vector"], res2["decision_vector"], "Ensemble should be invariant to choice order")
    print("... PASSED")

def test_vvl_record_creation():
    print("Running test: test_vvl_record_creation")
    decision_vector = {"path": ["a", "b"], "weights": [0.5, 0.5], "records": []}
    
    record = build_vvl_record(
        session_id="s4",
        phase="SAMPLE",
        prev_hash="0"*64,
        decision_vector=decision_vector,
        bifurcation_reason="none"
    )
    
    core = {
        "session_id": "s4",
        "phase": "SAMPLE",
        "prev_hash": "0"*64,
        "timestamp": record["timestamp"],
        "decision_vector": decision_vector,
        "bifurcation_reason": "none"
    }
    expected_hash = digest_jcs(core)
    
    assert_eq(record["record_hash"], expected_hash, "Record hash should match core content")
    assert_eq(record["prev_ledger_hash"], record["prev_hash"], "prev_ledger_hash alias should match prev_hash")
    assert_eq(record["integrity_hash"], record["record_hash"], "integrity_hash alias should match record_hash")
    print("... PASSED")

def main():
    try:
        test_replay()
        test_bifurcation()
        test_multimodel_ensemble()
        test_vvl_record_creation()
        print("\nAll harness tests passed!")

    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")

        sys.exit(1)

if __name__ == "__main__":
    main()
