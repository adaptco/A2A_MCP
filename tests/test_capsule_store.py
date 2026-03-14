from __future__ import annotations

import json
from pathlib import Path

from orchestrator.capsule_store import (
    append_capsule_hybrid,
    init_capsule_mirror_db,
    search_capsules,
    verify_capsule_signature,
)


def _capsule(digest_id: str, state_id: str, reasoning: str) -> dict:
    return {
        "state_id": state_id,
        "lineage": {
            "digest_id": digest_id,
            "input_hash": "abc123",
            "rule30_seed": "0001000",
            "env_version": "2026.03.13-v1.0",
        },
        "computational_grid": [0, 0, 0, 1, 0, 0, 0],
        "agent_reasoning": reasoning,
        "is_terminal": False,
    }


def test_hybrid_write_and_fts_search_matches_archive(tmp_path):
    db_path = tmp_path / "capsules.db"
    archive_dir = tmp_path / "archive"
    key = b"test-hmac-key"

    conn = init_capsule_mirror_db(str(db_path))
    try:
        first = _capsule(
            digest_id="d1",
            state_id="RUN-1",
            reasoning="Applied Rule 30 and detected resonance spike",
        )
        second = _capsule(
            digest_id="d2",
            state_id="RUN-2",
            reasoning="Fallback branch with nominal stabilization",
        )

        first_result = append_capsule_hybrid(conn, str(archive_dir), first, hmac_key=key)
        append_capsule_hybrid(conn, str(archive_dir), second, hmac_key=key)

        archive_path = Path(first_result["archive_path"])
        signature_path = Path(first_result["signature_path"])
        assert archive_path.exists()
        assert signature_path.exists()

        archived_capsule = json.loads(archive_path.read_text(encoding="utf-8"))
        signature = signature_path.read_text(encoding="utf-8").strip()
        assert verify_capsule_signature(archived_capsule, signature, key)

        results = search_capsules(conn, "resonance", limit=5)
        assert results, "expected at least one FTS hit"
        assert results[0]["digest_id"] == "d1"

        hit_archive = Path(results[0]["archive_path"])
        hit_capsule = json.loads(hit_archive.read_text(encoding="utf-8"))
        assert hit_capsule["lineage"]["digest_id"] == results[0]["digest_id"]
    finally:
        conn.close()
