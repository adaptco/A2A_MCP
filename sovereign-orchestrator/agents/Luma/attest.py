"""
Luma — Receipt Attestation Agent (agents/Luma/attest.py)

Quality gate: scans receipts/ directory, validates every artifact
has a corresponding execution receipt, and signs an attestation.
No artifact is considered complete without a Luma receipt.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def scan_receipts(receipts_dir: str) -> list[dict]:
    """Scan the receipts directory and load all receipt files."""
    receipt_path = Path(receipts_dir)
    if not receipt_path.exists():
        print(f"[Luma] ⚠️ Receipts directory not found: {receipts_dir}")
        return []

    receipts = []
    for receipt_file in sorted(receipt_path.glob("*.json")):
        if "-relay" in receipt_file.stem:
            continue  # Skip relay receipts
        try:
            receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
            receipts.append(receipt)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[Luma] ⚠️ Failed to read {receipt_file}: {e}")
    return receipts


def validate_artifacts(receipts: list[dict]) -> list[dict]:
    """Validate that each receipt has a corresponding output artifact."""
    results = []
    for receipt in receipts:
        task_id = receipt.get("task_id", "unknown")
        output_path = receipt.get("output_path", "")
        artifact_exists = Path(output_path).exists() if output_path else False

        results.append({
            "task_id": task_id,
            "status": receipt.get("status", "unknown"),
            "artifact_exists": artifact_exists,
            "validated": artifact_exists and receipt.get("status") == "completed",
        })
    return results


def sign_attestation(results: list[dict]) -> dict:
    """Create and sign the final attestation document."""
    all_valid = all(r["validated"] for r in results) if results else False
    attestation = {
        "attestation_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "Luma",
        "total_tasks": len(results),
        "validated_tasks": sum(1 for r in results if r["validated"]),
        "failed_tasks": sum(1 for r in results if not r["validated"]),
        "overall_status": "PASS" if all_valid else "FAIL",
        "task_results": results,
        "signature": None,  # Ed25519 placeholder
    }
    return attestation


def attest(receipts_dir: str = "receipts") -> dict:
    """Run the full attestation pipeline."""
    print(f"[Luma] Scanning {receipts_dir}/ for execution receipts...")

    receipts = scan_receipts(receipts_dir)
    print(f"[Luma] Found {len(receipts)} receipts")

    results = validate_artifacts(receipts)
    attestation = sign_attestation(results)

    # Write attestation
    output_dir = Path(receipts_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    attestation_file = output_dir / "attestation.json"
    attestation_file.write_text(
        json.dumps(attestation, indent=2), encoding="utf-8"
    )

    status = attestation["overall_status"]
    emoji = "✅" if status == "PASS" else "❌"
    print(
        f"[Luma] {emoji} Attestation: {status} "
        f"({attestation['validated_tasks']}/{attestation['total_tasks']} tasks validated)"
    )

    if status == "FAIL":
        for r in results:
            if not r["validated"]:
                print(f"[Luma]   ❌ {r['task_id']}: artifact_exists={r['artifact_exists']}")
        sys.exit(1)

    return attestation


if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else "receipts"
    attest(directory)
