from prime_directive.validators.preflight import validate_preflight


def test_preflight_gate_fails_on_empty_payload():
    assert not validate_preflight({}).passed
