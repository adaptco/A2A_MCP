from prime_directive.validators.provenance import validate_provenance


def test_provenance_gate_rejects_false_bool():
    assert not validate_provenance({"provenance": False}).passed


def test_provenance_gate_rejects_non_boolean_falsey_string():
    assert not validate_provenance({"provenance": "false"}).passed


def test_provenance_gate_accepts_true_bool():
    assert validate_provenance({"provenance": True}).passed
