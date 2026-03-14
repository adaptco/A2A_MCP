#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.capsule_verifier import pretty_print_report, walk_and_verify_archive


def _read_hmac_key(args: argparse.Namespace) -> bytes:
    if args.hmac_key:
        return args.hmac_key.encode("utf-8")
    env_key = os.getenv(args.hmac_key_env, "")
    if env_key:
        return env_key.encode("utf-8")
    raise ValueError(
        f"HMAC key is required. Set --hmac-key or provide env var {args.hmac_key_env}."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify capsule archive integrity (detached HMAC + lineage digest) and optionally repair DB mirror."
    )
    parser.add_argument("--archive", required=True, help="Archive root path containing capsule JSON files.")
    parser.add_argument("--db", help="SQLite mirror path used when --repair is set.")
    parser.add_argument("--repair", action="store_true", help="Upsert verified entries into SQLite mirror.")
    parser.add_argument("--no-marker", action="store_true", help="Do not write .verified marker files.")
    parser.add_argument("--hmac-key", help="Raw HMAC key string (prefer env var in production).")
    parser.add_argument(
        "--hmac-key-env",
        default="RULIOLOGY_HMAC_KEY",
        help="Environment variable name containing HMAC key.",
    )
    parser.add_argument(
        "--env-version",
        default=None,
        help="Optional env version override for lineage recomputation.",
    )
    parser.add_argument(
        "--allow-missing-signatures",
        action="store_true",
        help="Treat missing .sig as non-fatal (still checks digest).",
    )
    args = parser.parse_args()

    if args.repair and not args.db:
        print("--db is required when --repair is enabled.", file=sys.stderr)
        return 2

    try:
        hmac_key = _read_hmac_key(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    report = walk_and_verify_archive(
        args.archive,
        hmac_key=hmac_key,
        db_path=args.db,
        repair=args.repair,
        marker=not args.no_marker,
        enforce_signature=not args.allow_missing_signatures,
        env_version=args.env_version,
    )
    pretty_print_report(report)
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
