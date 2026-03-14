#!/usr/bin/env python3
"""
Compute canonical JSON (JCS-style) strings plus SHA-256 and base64 encodings
for JSON or NDJSON inputs.

Usage:
  python scripts/jcs_checksum_helper.py path/to/file.json
  python scripts/jcs_checksum_helper.py path/to/file.ndjson --ndjson

The script prints one block per JSON value, including:
- canonical JCS string (compact, sorted keys)
- SHA-256 hex digest of the canonical string
- base64 (standard) of the canonical string

This helper is intended for pre-flight CI ingestion checks where
placeholder artifacts must be replaced with canonicalized values.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute JCS-style canonical strings and digests for JSON/NDJSON inputs.",
    )
    parser.add_argument("input", type=Path, help="Path to a JSON or NDJSON file")
    parser.add_argument(
        "--ndjson",
        action="store_true",
        help="Treat the input as NDJSON (one JSON object per line)",
    )
    return parser.parse_args()


def iter_json_values(path: Path, ndjson: bool) -> Iterable[Tuple[int, object]]:
    text = path.read_text(encoding="utf-8")
    if not ndjson:
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Failed to parse JSON from {path}: {exc}") from exc
        yield 1, obj
        return

    for idx, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Failed to parse JSON on line {idx} of {path}: {exc}") from exc
        yield idx, obj


def canonicalize(value: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Unable to canonicalize value: {exc}") from exc


def encode_summary(canonical: str) -> Tuple[str, str]:
    data = canonical.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    b64 = base64.b64encode(data).decode("ascii")
    return digest, b64


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    for line_no, value in iter_json_values(args.input, args.ndjson):
        canonical = canonicalize(value)
        digest, b64 = encode_summary(canonical)
        header = f"Line {line_no}" if args.ndjson else "Document"
        print(f"=== {header} ===")
        print("canonical:")
        print(canonical)
        print("sha256:", digest)
        print("payload_b64:", b64)
        print()


if __name__ == "__main__":
    main()
