from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from orchestrator.capsule_store import (
    append_capsule_hybrid,
    init_capsule_mirror_db,
    recompute_lineage_digest,
)
from orchestrator.capsule_verifier import (
    STATUS_DIGEST_MISMATCH,
    STATUS_MISSING_SIG,
    STATUS_OK,
    STATUS_SIG_MISMATCH,
    verify_capsule_file,
    walk_and_verify_archive,
)


def _capsule(state_id: str, seed: str = "0001000") -> dict:
    lineage = {
        "input_hash": "abchash",
        "rule30_seed": seed,
        "env_version": "2026.03.13-v1.0",
    }
    lineage["digest_id"] = recompute_lineage_digest(lineage)
    return {
        "state_id": state_id,
        "lineage": lineage,
        "computational_grid": [0, 0, 0, 1, 0, 0, 0],
        "agent_reasoning": "Applied Rule 30 for audit trace.",
        "is_terminal": False,
    }


def test_verify_good_file_ok(tmp_path):
    key = b"test-key"
    archive = tmp_path / "archive"
    db = init_capsule_mirror_db(str(tmp_path / "capsules.db"))
    try:
        result = append_capsule_hybrid(db, str(archive), _capsule("RUN-1"), hmac_key=key)
    finally:
        db.close()

    status = verify_capsule_file(result["archive_path"], hmac_key=key)
    assert status.status == STATUS_OK


def test_verify_tampered_file_sig_mismatch(tmp_path):
    key = b"test-key"
    archive = tmp_path / "archive"
    db = init_capsule_mirror_db(str(tmp_path / "capsules.db"))
    try:
        result = append_capsule_hybrid(db, str(archive), _capsule("RUN-2"), hmac_key=key)
    finally:
        db.close()

    path = Path(result["archive_path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["agent_reasoning"] = "tampered after signing"
    path.write_text(json.dumps(payload), encoding="utf-8")

    status = verify_capsule_file(str(path), hmac_key=key)
    assert status.status == STATUS_SIG_MISMATCH


def test_verify_digest_mismatch(tmp_path):
    key = b"test-key"
    archive = tmp_path / "archive"
    db = init_capsule_mirror_db(str(tmp_path / "capsules.db"))
    try:
        capsule = _capsule("RUN-3")
        result = append_capsule_hybrid(db, str(archive), capsule, hmac_key=key)
    finally:
        db.close()

    path = Path(result["archive_path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["lineage"]["rule30_seed"] = "1111111"
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    # rewrite signature to force signature success and isolate digest failure
    sig = hmac.new(key, path.read_text(encoding="utf-8").encode("utf-8"), hashlib.sha256).hexdigest()
    Path(str(path) + ".sig").write_text(sig, encoding="utf-8")

    status = verify_capsule_file(str(path), hmac_key=key)
    assert status.status == STATUS_DIGEST_MISMATCH


def test_verify_missing_sig(tmp_path):
    key = b"test-key"
    archive = tmp_path / "archive"
    db = init_capsule_mirror_db(str(tmp_path / "capsules.db"))
    try:
        result = append_capsule_hybrid(db, str(archive), _capsule("RUN-4"), hmac_key=key)
    finally:
        db.close()

    sig_path = Path(result["signature_path"])
    sig_path.unlink()

    status = verify_capsule_file(result["archive_path"], hmac_key=key)
    assert status.status == STATUS_MISSING_SIG


def test_walk_verify_repair_upserts_mirror(tmp_path):
    key = b"test-key"
    archive = tmp_path / "archive"
    db_path = tmp_path / "mirror.db"
    conn = init_capsule_mirror_db(str(db_path))
    try:
        append_capsule_hybrid(conn, str(archive), _capsule("RUN-5"), hmac_key=key)
    finally:
        conn.close()

    report = walk_and_verify_archive(
        str(archive),
        hmac_key=key,
        db_path=str(db_path),
        repair=True,
        marker=True,
    )
    assert report["ok"] is True
    assert report["summary"][STATUS_OK] == 1

    with init_capsule_mirror_db(str(db_path)) as verify_conn:
        row = verify_conn.execute("SELECT COUNT(*) AS c FROM capsules").fetchone()
        assert int(row["c"]) >= 1
