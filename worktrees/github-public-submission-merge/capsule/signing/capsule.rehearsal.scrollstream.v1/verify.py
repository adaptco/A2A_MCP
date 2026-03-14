#!/usr/bin/env python3
"""Verify the canonical preimage digest for the scrollstream capsule."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

EXPECTED_SHA256 = "8b3ad7f76ba29b478fffeead67475501a8f576afccbe7cf46117278413ef3909"
BASE_DIR = pathlib.Path(__file__).resolve().parent
CANONICAL_PATH = BASE_DIR / "canonical_preimage.json"


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b""):
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def validate_json_roundtrip(path: pathlib.Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    regen = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
    return regen == raw


def main() -> int:
    if not CANONICAL_PATH.is_file():
        print(f"error: missing canonical preimage at {CANONICAL_PATH}", file=sys.stderr)
        return 2

    digest = sha256_file(CANONICAL_PATH)
    if digest != EXPECTED_SHA256:
        print("error: canonical_preimage.json sha256 mismatch", file=sys.stderr)
        print(f"expected {EXPECTED_SHA256}", file=sys.stderr)
        print(f"found    {digest}", file=sys.stderr)
        return 1

    if not validate_json_roundtrip(CANONICAL_PATH):
        print("error: canonical_preimage.json is not canonicalized", file=sys.stderr)
        return 1

    print("canonical_preimage.json verified: sha256 matches expected digest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
