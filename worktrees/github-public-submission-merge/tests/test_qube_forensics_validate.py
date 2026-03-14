import pytest

pytest.importorskip("jsonschema", reason="Skipping due to rpds-py C-extension environment issue")
from jsonschema.exceptions import ValidationError

from qube_forensics.validate import validate_forensic_report


def test_validate_forensic_report_accepts_valid_payload() -> None:
    payload = {
        "report_id": "rep-1",
        "sha256": "a" * 64,
        "captured_at": "2025-01-01T00:00:00Z",
    }

    validate_forensic_report(payload)


def test_validate_forensic_report_rejects_short_sha256() -> None:
    payload = {
        "report_id": "rep-1",
        "sha256": "abcdef12",
        "captured_at": "2025-01-01T00:00:00Z",
    }

    with pytest.raises(ValidationError):
        validate_forensic_report(payload)


def test_validate_forensic_report_rejects_invalid_timestamp_format() -> None:
    payload = {
        "report_id": "rep-1",
        "sha256": "b" * 64,
        "captured_at": "not-a-timestamp",
    }

    with pytest.raises(ValidationError):
        validate_forensic_report(payload)
