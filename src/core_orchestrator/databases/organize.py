"""Utilities for maintaining the Organize-backed SSOT snapshot."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping

from ..router import Event

Snapshot = Dict[str, Any]


@dataclass(frozen=True)
class SnapshotMetadata:
    """Metadata describing the current snapshot state."""

    updated_at: str
    count: int
    repo_root: str


class OrganizeSentinel:
    """Persist events into a repository-scoped snapshot acting as the SSOT."""

    def __init__(
        self,
        repo_path: str | Path,
        *,
        relative_path: str | Path = "data/core-orchestrator/events.json",
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self.repo_path = Path(repo_path)
        rel_path = Path(relative_path)
        self.database_path = rel_path if rel_path.is_absolute() else self.repo_path / rel_path
        self._extra_metadata = dict(metadata or {})

    # ------------------------------------------------------------------
    def record(self, event: Event) -> Snapshot:
        """Record ``event`` in the SSOT snapshot and return the stored record."""

        records = self._load_records()
        key = self._make_key(event.source, event.type, event.payload)
        records[key] = self._build_record(key, event)
        self._write_records(records)
        return records[key]

    def sync(self, events: Iterable[Event]) -> list[Snapshot]:
        """Persist a collection of events in a single transaction."""

        records = self._load_records()
        snapshots: list[Snapshot] = []
        for event in events:
            key = self._make_key(event.source, event.type, event.payload)
            snapshot = self._build_record(key, event)
            records[key] = snapshot
            snapshots.append(snapshot)
        self._write_records(records)
        return snapshots

    # ------------------------------------------------------------------
    def read(self) -> dict[str, Any]:
        """Return the full SSOT payload currently stored on disk."""

        records = self._load_records()
        payload = self._serialize_records(records)
        return payload

    # ------------------------------------------------------------------
    def _build_record(self, key: str, event: Event) -> Snapshot:
        tags = sorted(event.tags)
        return {
            "key": key,
            "source": event.source,
            "type": event.type,
            "payload": event.payload,
            "raw": event.raw,
            "tags": tags,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

    def _load_records(self) -> MutableMapping[str, Snapshot]:
        path = self.database_path
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON payload in {path}") from exc
        records: MutableMapping[str, Snapshot] = {}
        if isinstance(data, Mapping):
            events = data.get("events")
            if events is None and all(isinstance(k, str) for k in data):
                events = [dict(value, key=key) for key, value in data.items() if isinstance(value, Mapping)]
        elif isinstance(data, list):
            events = data
        else:
            events = []
        if events:
            for item in events:
                if not isinstance(item, Mapping):
                    continue
                key = item.get("key")
                if not key:
                    key = self._make_key(
                        str(item.get("source", "")),
                        str(item.get("type", "")),
                        item.get("payload") if isinstance(item.get("payload"), Mapping) else {},
                    )
                record = dict(item)
                record["key"] = str(key)
                records[str(key)] = record
        return records

    def _write_records(self, records: Mapping[str, Snapshot]) -> None:
        payload = self._serialize_records(records)
        path = self.database_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def _serialize_records(self, records: Mapping[str, Snapshot]) -> dict[str, Any]:
        ordered_keys = sorted(records)
        events = [dict(records[key]) for key in ordered_keys]
        metadata = dict(self._extra_metadata)
        metadata.update(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "count": len(events),
                "repo_root": str(self.repo_path),
            }
        )
        return {"metadata": metadata, "events": events}

    def _make_key(self, source: str, event_type: str, payload: Mapping[str, Any]) -> str:
        identifier_candidates = [
            payload.get("id"),
            payload.get("url"),
            payload.get("external_id"),
            payload.get("title"),
            payload.get("content"),
        ]
        identifier = next((str(value) for value in identifier_candidates if value), None)
        if not identifier:
            identifier = json.dumps(payload, sort_keys=True)
        return f"{source}:{event_type}:{identifier}"


__all__ = ["OrganizeSentinel", "Snapshot", "SnapshotMetadata"]
