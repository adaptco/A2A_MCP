from packages.moa_runtime import contracts


def test_deterministic_embedding_length():
    emb = contracts.deterministic_embedding("hello world", dim=16)
    assert len(emb) == 16


def test_contract_hash_changes_with_manifest():
    agent = {"a": 1}
    routing = {"r": 1}
    expert = {"e": 1}
    manifest = {"manifest_id": "m1"}
    h1 = contracts.compute_contract_hash(agent, routing, expert, manifest)
    manifest["manifest_id"] = "m2"
    h2 = contracts.compute_contract_hash(agent, routing, expert, manifest)
    assert h1 != h2


def test_citation_validation():
    text = "[t1] claim one\n[t2] claim two"
    assert contracts.validate_response_has_citations(text, ["t1", "t2"])
    assert not contracts.validate_response_has_citations("missing", ["t1"])
