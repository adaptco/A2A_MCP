#!/usr/bin/env python3
"""Append governance events to the workflow ledger and audit trail."""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

LEDGER_PATH = Path("ledger/workflow_ledger.json")
AUDIT_TRAIL_PATH = Path("ledger/audit_trail.csv")
REQUIRED_EVENT_KEYS = {"event", "message", "ticket", "timestamp"}


@dataclass
class LedgerEvent:
    event: str
    message: str
    ticket: str
    timestamp: float

    def to_row(self) -> list[str]:
        return [self.event, self.message, self.ticket, str(self.timestamp)]


def ensure_files() -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LEDGER_PATH.exists():
        LEDGER_PATH.write_text("[]", encoding="utf-8")

    AUDIT_TRAIL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not AUDIT_TRAIL_PATH.exists():
        AUDIT_TRAIL_PATH.write_text("event,message,ticket,timestamp\n", encoding="utf-8")


def load_ledger() -> list[dict[str, Any]]:
    ensure_files()
    with LEDGER_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def append_event(event: LedgerEvent) -> None:
    entries = load_ledger()
    entries.append(asdict(event))
    LEDGER_PATH.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")

    with AUDIT_TRAIL_PATH.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(event.to_row())


def check_only() -> None:
    entries = load_ledger()
    if not isinstance(entries, list):
        raise RuntimeError("Ledger must be a list of events")
    for idx, entry in enumerate(entries):
        missing = REQUIRED_EVENT_KEYS - entry.keys()
        if missing:
            raise RuntimeError(f"Ledger entry {idx} missing keys: {', '.join(sorted(missing))}")

    with AUDIT_TRAIL_PATH.open("r", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header != ["event", "message", "ticket", "timestamp"]:
            raise RuntimeError("Audit trail header is invalid")


def summarize() -> str:
    entries = load_ledger()
    summary: dict[str, int] = {}
    for entry in entries:
        summary[entry.get("event", "unknown")] = summary.get(entry.get("event", "unknown"), 0) + 1

    lines = ["Event Counts:"]
    for event, count in sorted(summary.items()):
        lines.append(f"- {event}: {count}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", help="Event type to log (e.g., override, sync)")
    parser.add_argument("--message", default="", help="Human-friendly message for the ledger entry")
    parser.add_argument("--ticket", default="n/a", help="Reference ticket or issue identifier")
    parser.add_argument("--check-only", action="store_true", help="Validate ledger formatting and exit")
    parser.add_argument("--summarize", action="store_true", help="Print a quick ledger summary")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.check_only and args.summarize:
        print("--check-only and --summarize are mutually exclusive", file=sys.stderr)
        return 2

    ensure_files()

    if args.check_only:
        check_only()
        print("Ledger formatting OK")
        return 0

    if args.summarize:
        print(summarize())
        return 0

    if not args.event:
        print("--event is required when logging", file=sys.stderr)
        return 2

    entry = LedgerEvent(
        event=args.event,
        message=args.message,
        ticket=args.ticket,
        timestamp=time.time(),
    )
    append_event(entry)
    print(f"Logged event '{args.event}'")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
