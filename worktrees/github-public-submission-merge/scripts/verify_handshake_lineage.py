#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class SessionState:
  last_event_id: Optional[str] = None
  revoked: bool = False
  seen_event_ids: set[str] = field(default_factory=set)


def compute_han_eigenvalue(event: dict) -> float:
  basis = "|".join(
    [
      str(event.get("kind", "")),
      str(event.get("session_id", "")),
      str(event.get("event_id", "")),
      str(event.get("prev", "")),
      str(event.get("entropy_threshold", "")),
    ]
  )
  digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]
  normalized = int(digest, 16) / float(16**12 - 1)
  return round(normalized, 6)


def find_files(pattern: str) -> List[Path]:
  return sorted(
    p
    for p in REPO_ROOT.rglob(pattern)
    if ".git" not in p.parts and "node_modules" not in p.parts
  )


def load_json(path: Path) -> dict:
  return json.loads(path.read_text(encoding="utf-8"))


def choose_schema_for_payload(payload: Path, schema_files: Iterable[Path]) -> Optional[Path]:
  payload_name = payload.stem.lower()
  ranked = []
  for schema in schema_files:
    schema_name = schema.stem.lower()
    score = 0
    if payload.parent == schema.parent:
      score += 3
    if "handshake" in schema_name:
      score += 2
    if any(token and token in schema_name for token in payload_name.split(".")):
      score += 1
    ranked.append((score, schema))

  ranked.sort(key=lambda t: (-t[0], str(t[1])))
  if not ranked or ranked[0][0] <= 0:
    return None
  return ranked[0][1]


def validate_payload(path: Path, validator: Draft202012Validator) -> List[str]:
  errors: List[str] = []
  sessions: Dict[str, SessionState] = {}

  lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
  for index, line in enumerate(lines, start=1):
    prefix = f"{path}:{index}"
    try:
      event = json.loads(line)
    except json.JSONDecodeError as exc:
      errors.append(f"{prefix} invalid JSON: {exc.msg}")
      continue

    for schema_error in validator.iter_errors(event):
      location = ".".join([str(x) for x in schema_error.path]) or "<root>"
      errors.append(f"{prefix} schema violation at {location}: {schema_error.message}")

    if "entropy_threshold" not in event or not isinstance(event.get("entropy_threshold"), (int, float)):
      errors.append(f"{prefix} missing numeric entropy_threshold")

    if "han_eigenvalue" not in event or not isinstance(event.get("han_eigenvalue"), (int, float)):
      errors.append(f"{prefix} missing numeric han_eigenvalue")
    else:
      expected = compute_han_eigenvalue(event)
      actual = round(float(event["han_eigenvalue"]), 6)
      if actual != expected:
        errors.append(f"{prefix} han_eigenvalue mismatch expected={expected} actual={actual}")

    witness = event.get("lineage_witness")
    if not isinstance(witness, dict):
      errors.append(f"{prefix} missing lineage_witness object")
    else:
      if witness.get("format") != "ndjson":
        errors.append(f"{prefix} lineage_witness.format must be 'ndjson'")
      if witness.get("line_number") != index:
        errors.append(
          f"{prefix} lineage_witness.line_number must match NDJSON line index ({index}), got {witness.get('line_number')}"
        )
      if not isinstance(witness.get("stream_id"), str) or not witness.get("stream_id"):
        errors.append(f"{prefix} lineage_witness.stream_id must be a non-empty string")

    session_id = event.get("session_id")
    event_id = event.get("event_id")
    if not isinstance(session_id, str) or not isinstance(event_id, str):
      continue

    state = sessions.setdefault(session_id, SessionState())

    if event_id in state.seen_event_ids:
      errors.append(f"{prefix} duplicate event_id {event_id} in session {session_id}")

    if state.last_event_id is not None and event.get("prev") != state.last_event_id:
      errors.append(
        f"{prefix} invalid prev pointer for session {session_id}: expected {state.last_event_id}, got {event.get('prev')}"
      )

    kind = event.get("kind")
    if state.revoked and kind in {"handshake.bound", "handshake.fossilized"}:
      errors.append(f"{prefix} lineage violation: {kind} after handshake.revoked in session {session_id}")

    if kind == "handshake.revoked":
      state.revoked = True

    state.last_event_id = event_id
    state.seen_event_ids.add(event_id)

  return errors


def main() -> int:
  parser = argparse.ArgumentParser(description="Validate handshake lineage, Han eigenvalue, and NDJSON witness rules.")
  parser.add_argument("--ndjson-glob", default="*handshake*.ndjson")
  parser.add_argument("--schema-glob", default="*handshake*.schema.json")
  parser.add_argument("--allow-empty", action="store_true", help="Allow no matching handshake NDJSON files.")
  args = parser.parse_args()

  ndjson_files = find_files(args.ndjson_glob)
  schema_files = find_files(args.schema_glob)

  if not ndjson_files:
    if args.allow_empty:
      print("No handshake NDJSON payload files found; nothing to validate.")
      return 0
    print("ERROR: no handshake NDJSON payload files found.", file=sys.stderr)
    return 1

  if not schema_files:
    print("ERROR: found handshake NDJSON files but no handshake schema files.", file=sys.stderr)
    return 1

  all_errors: List[str] = []
  for ndjson in ndjson_files:
    schema_path = choose_schema_for_payload(ndjson, schema_files)
    if schema_path is None:
      all_errors.append(f"{ndjson} could not match a handshake schema file")
      continue

    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    all_errors.extend(validate_payload(ndjson, validator))

  if all_errors:
    print("Handshake lineage validation failed:", file=sys.stderr)
    for err in all_errors:
      print(f"- {err}", file=sys.stderr)
    return 1

  print("Handshake lineage validation passed.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
