from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from orchestrator.capsule_store import (
    canonical_json,
    init_capsule_mirror_db,
    upsert_capsule_mirror,
    verify_capsule_signature,
    verify_lineage_digest,
)

STATUS_OK = "OK"
STATUS_MISSING_SIG = "MISSING_SIG"
STATUS_SIG_MISMATCH = "SIG_MISMATCH"
STATUS_DIGEST_MISMATCH = "DIGEST_MISMATCH"
STATUS_MALFORMED_JSON = "MALFORMED_JSON"
STATUS_IO_ERROR = "IO_ERROR"


@dataclass
class VerificationResult:
    path: str
    status: str
    message: str


def iter_capsule_files(archive_dir: str) -> Iterable[Path]:
    base = Path(archive_dir)
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*.json") if not str(p).endswith(".json.sig"))


def verify_capsule_file(
    path: str,
    *,
    hmac_key: bytes,
    enforce_signature: bool = True,
    env_version: Optional[str] = None,
) -> VerificationResult:
    sig_path = path + ".sig"
    if enforce_signature and not os.path.exists(sig_path):
        return VerificationResult(path=path, status=STATUS_MISSING_SIG, message="Detached signature not found.")

    try:
        with open(path, "r", encoding="utf-8") as f:
            capsule = json.load(f)
    except Exception as exc:
        return VerificationResult(path=path, status=STATUS_MALFORMED_JSON, message=f"JSON parse error: {exc}")

    if enforce_signature:
        try:
            with open(sig_path, "r", encoding="utf-8") as f:
                signature_hex = f.read().strip()
        except Exception as exc:
            return VerificationResult(path=path, status=STATUS_IO_ERROR, message=f"Signature read error: {exc}")

        if not verify_capsule_signature(capsule, signature_hex, hmac_key):
            return VerificationResult(
                path=path,
                status=STATUS_SIG_MISMATCH,
                message="HMAC signature does not match canonical payload.",
            )

    try:
        if not verify_lineage_digest(capsule, env_version=env_version):
            return VerificationResult(
                path=path,
                status=STATUS_DIGEST_MISMATCH,
                message="Lineage digest mismatch.",
            )
    except Exception as exc:
        return VerificationResult(path=path, status=STATUS_MALFORMED_JSON, message=f"Lineage validation error: {exc}")

    return VerificationResult(path=path, status=STATUS_OK, message="Verified.")


def walk_and_verify_archive(
    archive_dir: str,
    *,
    hmac_key: bytes,
    db_path: Optional[str] = None,
    repair: bool = False,
    marker: bool = True,
    enforce_signature: bool = True,
    env_version: Optional[str] = None,
) -> Dict[str, Any]:
    summary: Dict[str, int] = {
        STATUS_OK: 0,
        STATUS_MISSING_SIG: 0,
        STATUS_SIG_MISMATCH: 0,
        STATUS_DIGEST_MISMATCH: 0,
        STATUS_MALFORMED_JSON: 0,
        STATUS_IO_ERROR: 0,
    }
    results: list[VerificationResult] = []

    conn = init_capsule_mirror_db(db_path) if (repair and db_path) else None
    try:
        for json_path in iter_capsule_files(archive_dir):
            result = verify_capsule_file(
                str(json_path),
                hmac_key=hmac_key,
                enforce_signature=enforce_signature,
                env_version=env_version,
            )
            results.append(result)
            summary[result.status] = summary.get(result.status, 0) + 1

            if result.status == STATUS_OK and marker:
                try:
                    Path(str(json_path) + ".verified").write_text("", encoding="utf-8")
                except Exception:
                    pass

            if result.status == STATUS_OK and conn is not None:
                with open(json_path, "r", encoding="utf-8") as f:
                    capsule = json.load(f)
                upsert_capsule_mirror(conn, capsule, archive_path=str(json_path))
    finally:
        if conn is not None:
            conn.close()

    critical_failures = (
        summary.get(STATUS_SIG_MISMATCH, 0)
        + summary.get(STATUS_DIGEST_MISMATCH, 0)
        + summary.get(STATUS_MALFORMED_JSON, 0)
    )
    return {
        "ok": critical_failures == 0,
        "summary": summary,
        "results": [result.__dict__ for result in results],
    }


def pretty_print_report(report: Dict[str, Any]) -> None:
    for result in report["results"]:
        print(f"{result['path']} -> {result['status']}: {result['message']}")
    print("\nSummary:")
    for key in (
        STATUS_OK,
        STATUS_MISSING_SIG,
        STATUS_SIG_MISMATCH,
        STATUS_DIGEST_MISMATCH,
        STATUS_MALFORMED_JSON,
        STATUS_IO_ERROR,
    ):
        print(f"  {key}: {report['summary'].get(key, 0)}")
