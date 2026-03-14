#!/usr/bin/env python3
"""Verify that a remix capsule preserves its parent's motion ledger reference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Tuple


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _first_present(data: Any, keys: Iterable[Tuple[str, ...]]) -> str | None:
    for key_path in keys:
        current = data
        for key in key_path:
            if not isinstance(current, dict) or key not in current:
                break
            current = current[key]
        else:
            if isinstance(current, str):
                return current
    return None


_PARENT_CANDIDATES: Tuple[Tuple[str, ...], ...] = (
    ("payload", "motion_profile"),
    ("capsule", "telemetry_links", "motion_profile"),
    ("payload", "kinematics", "motion_ledger_ref"),
)


_CHILD_CANDIDATES: Tuple[Tuple[str, ...], ...] = (
    ("payload", "kinematics", "motion_ledger_ref"),
    ("payload", "motion_profile"),
)


def verify_kinematic_lock(parent_path: Path, remix_path: Path) -> Tuple[bool, str]:
    parent_data = _load_json(parent_path)
    remix_data = _load_json(remix_path)

    parent_motion = _first_present(parent_data, _PARENT_CANDIDATES)
    if parent_motion is None:
        return False, (
            f"Unable to locate motion ledger reference in parent capsule: {parent_path}"
        )

    remix_motion = _first_present(remix_data, _CHILD_CANDIDATES)
    if remix_motion is None:
        return False, (
            "Remix capsule does not expose a motion ledger reference; "
            "expected payload.kinematics.motion_ledger_ref"
        )

    if parent_motion != remix_motion:
        return False, (
            "Kinematic lock violation: parent motion ledger reference "
            f"({parent_motion}) does not match remix reference ({remix_motion})."
        )

    return True, (
        "Kinematic lock verified: remix capsule motion ledger reference matches parent."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate that a remix capsule preserves its parent's motion ledger reference."
    )
    parser.add_argument(
        "parent",
        type=Path,
        help="Path to the parent capsule JSON file",
    )
    parser.add_argument(
        "remix",
        type=Path,
        help="Path to the remix capsule JSON file",
    )
    args = parser.parse_args()

    ok, message = verify_kinematic_lock(args.parent, args.remix)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
