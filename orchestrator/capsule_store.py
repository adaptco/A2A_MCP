from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def canonical_json(payload: Dict[str, Any]) -> str:
    """Deterministic JSON representation used for signatures and persistence."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _lineage(capsule: Dict[str, Any]) -> Dict[str, Any]:
    lineage = capsule.get("lineage")
    if not isinstance(lineage, dict):
        raise ValueError("capsule.lineage must be a dict")
    return lineage


def _required_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _extract_capsule_record(capsule: Dict[str, Any], created_at: float) -> Dict[str, Any]:
    lineage = _lineage(capsule)
    return {
        "digest_id": _required_str(lineage.get("digest_id"), "lineage.digest_id"),
        "state_id": _required_str(capsule.get("state_id"), "state_id"),
        "created_at": float(created_at),
        "env_version": _required_str(lineage.get("env_version"), "lineage.env_version"),
        "input_hash": _required_str(lineage.get("input_hash"), "lineage.input_hash"),
        "rule30_seed": _required_str(lineage.get("rule30_seed"), "lineage.rule30_seed"),
        "agent_reasoning": str(capsule.get("agent_reasoning", "")),
    }


def recompute_lineage_digest(lineage: Dict[str, Any], *, env_version: Optional[str] = None) -> str:
    """Recompute digest_id from lineage fields using canonical composite format."""
    input_hash = _required_str(lineage.get("input_hash"), "lineage.input_hash")
    seed = _required_str(lineage.get("rule30_seed"), "lineage.rule30_seed")
    effective_env = env_version or _required_str(lineage.get("env_version"), "lineage.env_version")
    composite = f"{input_hash}|{seed}|{effective_env}"
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()


def verify_lineage_digest(capsule: Dict[str, Any], *, env_version: Optional[str] = None) -> bool:
    lineage = _lineage(capsule)
    digest_id = _required_str(lineage.get("digest_id"), "lineage.digest_id")
    expected = recompute_lineage_digest(lineage, env_version=env_version)
    return hmac.compare_digest(digest_id, expected)


def init_capsule_mirror_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=FULL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS capsules (
          digest_id TEXT PRIMARY KEY,
          state_id TEXT NOT NULL,
          created_at REAL NOT NULL,
          env_version TEXT NOT NULL,
          input_hash TEXT NOT NULL,
          rule30_seed TEXT NOT NULL,
          agent_reasoning TEXT NOT NULL,
          capsule_json TEXT NOT NULL,
          archive_path TEXT NOT NULL
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_capsules_created_at ON capsules(created_at);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_capsules_input_hash ON capsules(input_hash);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_capsules_rule30_seed ON capsules(rule30_seed);")

    # External-content FTS table keeps canonical source in capsules.capsule_json.
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS capsules_fts USING fts5(
          agent_reasoning,
          state_id UNINDEXED,
          digest_id UNINDEXED,
          content='capsules',
          content_rowid='rowid',
          tokenize='porter'
        );
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS capsules_ai AFTER INSERT ON capsules BEGIN
          INSERT INTO capsules_fts(rowid, agent_reasoning, state_id, digest_id)
          VALUES (new.rowid, new.agent_reasoning, new.state_id, new.digest_id);
        END;
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS capsules_ad AFTER DELETE ON capsules BEGIN
          INSERT INTO capsules_fts(capsules_fts, rowid, agent_reasoning, state_id, digest_id)
          VALUES ('delete', old.rowid, old.agent_reasoning, old.state_id, old.digest_id);
        END;
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS capsules_au AFTER UPDATE ON capsules BEGIN
          INSERT INTO capsules_fts(capsules_fts, rowid, agent_reasoning, state_id, digest_id)
          VALUES ('delete', old.rowid, old.agent_reasoning, old.state_id, old.digest_id);
          INSERT INTO capsules_fts(rowid, agent_reasoning, state_id, digest_id)
          VALUES (new.rowid, new.agent_reasoning, new.state_id, new.digest_id);
        END;
        """
    )
    return conn


def write_capsule_file(
    base_dir: str,
    capsule: Dict[str, Any],
    *,
    created_at: Optional[float] = None,
    hmac_key: Optional[bytes] = None,
) -> Dict[str, str]:
    timestamp = float(created_at if created_at is not None else time.time())
    record = _extract_capsule_record(capsule, timestamp)
    day = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
    out_dir = Path(base_dir) / day
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"CAP-{int(timestamp)}-{record['digest_id']}.json"
    final_path = out_dir / filename
    payload = canonical_json(capsule)

    fd, tmp_name = tempfile.mkstemp(prefix=filename + ".", suffix=".tmp", dir=str(out_dir))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, final_path)
    except Exception:
        try:
            os.remove(tmp_name)
        except OSError:
            pass
        raise

    result = {"archive_path": str(final_path)}
    if hmac_key is not None:
        signature = hmac.new(hmac_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        sig_path = str(final_path) + ".sig"
        with open(sig_path, "w", encoding="utf-8") as sig_file:
            sig_file.write(signature)
            sig_file.flush()
            os.fsync(sig_file.fileno())
        result["signature_path"] = sig_path

    return result


def append_capsule_hybrid(
    conn: sqlite3.Connection,
    archive_dir: str,
    capsule: Dict[str, Any],
    *,
    created_at: Optional[float] = None,
    hmac_key: Optional[bytes] = None,
) -> Dict[str, Any]:
    timestamp = float(created_at if created_at is not None else time.time())
    record = _extract_capsule_record(capsule, timestamp)
    write_result = write_capsule_file(archive_dir, capsule, created_at=timestamp, hmac_key=hmac_key)
    payload = canonical_json(capsule)

    with conn:
        conn.execute(
            """
            INSERT INTO capsules (
              digest_id, state_id, created_at, env_version, input_hash, rule30_seed,
              agent_reasoning, capsule_json, archive_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(digest_id) DO UPDATE SET
              state_id=excluded.state_id,
              created_at=excluded.created_at,
              env_version=excluded.env_version,
              input_hash=excluded.input_hash,
              rule30_seed=excluded.rule30_seed,
              agent_reasoning=excluded.agent_reasoning,
              capsule_json=excluded.capsule_json,
              archive_path=excluded.archive_path
            """,
            (
                record["digest_id"],
                record["state_id"],
                record["created_at"],
                record["env_version"],
                record["input_hash"],
                record["rule30_seed"],
                record["agent_reasoning"],
                payload,
                write_result["archive_path"],
            ),
        )

    output = dict(record)
    output.update(write_result)
    return output


def upsert_capsule_mirror(
    conn: sqlite3.Connection,
    capsule: Dict[str, Any],
    *,
    archive_path: str,
    created_at: Optional[float] = None,
) -> Dict[str, Any]:
    """Upsert a verified capsule into SQLite mirror without rewriting archive files."""
    timestamp = float(created_at if created_at is not None else time.time())
    record = _extract_capsule_record(capsule, timestamp)
    payload = canonical_json(capsule)
    with conn:
        conn.execute(
            """
            INSERT INTO capsules (
              digest_id, state_id, created_at, env_version, input_hash, rule30_seed,
              agent_reasoning, capsule_json, archive_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(digest_id) DO UPDATE SET
              state_id=excluded.state_id,
              created_at=excluded.created_at,
              env_version=excluded.env_version,
              input_hash=excluded.input_hash,
              rule30_seed=excluded.rule30_seed,
              agent_reasoning=excluded.agent_reasoning,
              capsule_json=excluded.capsule_json,
              archive_path=excluded.archive_path
            """,
            (
                record["digest_id"],
                record["state_id"],
                record["created_at"],
                record["env_version"],
                record["input_hash"],
                record["rule30_seed"],
                record["agent_reasoning"],
                payload,
                archive_path,
            ),
        )
    out = dict(record)
    out["archive_path"] = archive_path
    return out


def search_capsules(conn: sqlite3.Connection, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
          c.digest_id,
          c.state_id,
          c.created_at,
          c.archive_path,
          bm25(capsules_fts) AS score
        FROM capsules_fts
        JOIN capsules c ON c.rowid = capsules_fts.rowid
        WHERE capsules_fts MATCH ?
        ORDER BY score ASC
        LIMIT ?
        """,
        (query, int(limit)),
    ).fetchall()
    return [dict(row) for row in rows]


def reindex_capsules_fts(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute("INSERT INTO capsules_fts(capsules_fts) VALUES ('rebuild')")


def verify_capsule_signature(capsule: Dict[str, Any], signature_hex: str, hmac_key: bytes) -> bool:
    payload = canonical_json(capsule).encode("utf-8")
    expected = hmac.new(hmac_key, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_hex)
