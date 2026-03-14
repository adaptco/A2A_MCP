"""
Fossil Chain — Merkle-chained tamper-evident audit log for the Agentic Runtime.
Every event is SHA-256 hashed against the previous event, forming a verifiable chain.
Ported from: sovereign-mcp/src/event_store/event_store.py
"""
import hashlib
import json
import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("FossilChain")


class FossilChain:
    """
    Append-only, cryptographically hash-chained event log.
    Compatible with AgenticRuntime as a drop-in audit layer.
    """

    def __init__(self, db_path: str = "fossil_chain.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    # ------------------------------------------------------------------
    # Internal DB setup
    # ------------------------------------------------------------------

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS fossil_events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT    NOT NULL,
                event_type      TEXT    NOT NULL,
                artifact_id     TEXT,
                state           TEXT,
                data            TEXT    NOT NULL,
                previous_hash   TEXT,
                hash            TEXT    NOT NULL
            )
        """)
        self.conn.commit()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def _calculate_hash(self, event_type: str, data: str, previous_hash: Optional[str]) -> str:
        payload = f"{event_type}{data}{previous_hash or ''}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def append_event(self, event_type: str, artifact_id: str, state: str, data: Dict[str, Any]) -> str:
        """
        Append a new event to the chain. Returns the event hash.
        """
        data_json = json.dumps(data, sort_keys=True, default=str)
        timestamp = datetime.utcnow().isoformat()

        cursor = self.conn.cursor()
        cursor.execute("SELECT hash FROM fossil_events ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        previous_hash = row[0] if row else None

        event_hash = self._calculate_hash(event_type, data_json, previous_hash)

        cursor.execute("""
            INSERT INTO fossil_events (timestamp, event_type, artifact_id, state, data, previous_hash, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, event_type, artifact_id, state, data_json, previous_hash, event_hash))
        self.conn.commit()

        logger.debug(f"FossilChain: Appended [{event_type}] hash={event_hash[:10]}...")
        return event_hash

    def verify_chain(self) -> bool:
        """
        Walk the entire chain and verify SHA-256 integrity.
        Returns True only if no tampering is detected.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT event_type, data, previous_hash, hash FROM fossil_events ORDER BY id ASC"
        )
        rows = cursor.fetchall()

        expected_previous_hash = None
        for event_type, data, previous_hash, stored_hash in rows:
            if previous_hash != expected_previous_hash:
                logger.warning("FossilChain: previous_hash mismatch — chain broken!")
                return False
            calculated_hash = self._calculate_hash(event_type, data, previous_hash)
            if calculated_hash != stored_hash:
                logger.warning(f"FossilChain: Hash collision on [{event_type}] — tamper detected!")
                return False
            expected_previous_hash = stored_hash

        return True

    def get_history(self) -> List[Dict[str, Any]]:
        """Return all events in chronological order."""
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM fossil_events ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]
