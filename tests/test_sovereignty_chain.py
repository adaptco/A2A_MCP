from prime_directive.sovereignty.chain import append_event, verify_chain


def test_sovereignty_chain_roundtrip() -> None:
    e1 = append_event(1, "state.transition", "rendered", {"step": "render"})
    e2 = append_event(2, "gate.preflight", "validated", {"passed": True}, prev_hash=e1.hash_current)
    assert verify_chain([e1, e2])


def test_sovereignty_chain_detects_tamper() -> None:
    e1 = append_event(1, "state.transition", "rendered", {"step": "render"})
    e2 = append_event(2, "gate.preflight", "validated", {"passed": True}, prev_hash=e1.hash_current)
    tampered = e2.__class__(event=e2.event, hash_current="deadbeef")
    assert not verify_chain([e1, tampered])
