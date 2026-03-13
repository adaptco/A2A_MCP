import json

import pytest

from pipeline.lib.canonical import jcs_canonical_bytes


def test_canonical_json_normalizes_float_whole_numbers() -> None:
    payload = {"a": 1.0, "b": [2.0, 2.5], "c": {"d": 3.0}}

    canonical = jcs_canonical_bytes(payload)

    assert canonical == b'{"a":1,"b":[2,2.5],"c":{"d":3}}'


def test_canonical_json_rejects_nan() -> None:
    with pytest.raises(ValueError):
        jcs_canonical_bytes({"value": float("nan")})


def test_canonical_json_rejects_infinity() -> None:
    with pytest.raises(ValueError):
        jcs_canonical_bytes({"value": float("inf")})


def test_canonical_json_remains_valid_json() -> None:
    payload = {"x": 1.0, "y": 1.25}
    canonical = jcs_canonical_bytes(payload)

    decoded = json.loads(canonical.decode("utf-8"))

    assert decoded == {"x": 1, "y": 1.25}
