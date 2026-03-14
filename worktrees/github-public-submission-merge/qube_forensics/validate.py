"""Schema validation helpers for forensic reports."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

SCHEMA_PATH = Path(__file__).parent / "schemas" / "forensic_report.schema.json"

_FORMAT_CHECKER = FormatChecker()


@_FORMAT_CHECKER.checks("date-time")
def _check_datetime(value: object) -> bool:
    if not isinstance(value, str):
        return False

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False

    return True


def load_schema() -> Dict[str, Any]:
    """Load the forensic report schema from disk."""
    with SCHEMA_PATH.open("r", encoding="utf-8") as schema_file:
        return json.load(schema_file)


def validate_forensic_report(report: Dict[str, Any]) -> None:
    """Validate a forensic report payload.

    Raises:
        ValidationError: when the report is invalid.
    """
    schema = load_schema()
    validator = Draft202012Validator(schema, format_checker=_FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(report), key=lambda err: err.path)
    if errors:
        raise ValidationError(errors[0].message)
