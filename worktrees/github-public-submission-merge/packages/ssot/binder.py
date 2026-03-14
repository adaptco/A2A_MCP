"""SSOT binder capsule models and utilities.

This module loads the sovereign archive registry capsule and exposes
helpers to reason about entries and the Merkle root used to seal the
binder.  The structures mirror the specification outlined in the relay
architecture so downstream services (orchestration, PreViz, clip
assembly) can rely on deterministic provenance metadata.
"""
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from pydantic import BaseModel, Field, ValidationError, field_validator

# ---------------------------------------------------------------------------
# Pydantic models describing the SSOT registry entries and context
# ---------------------------------------------------------------------------


class RegistryContext(BaseModel):
    """Metadata describing the registry capsule itself."""

    name: str
    version: str
    maintainer: str


class CouncilAttestation(BaseModel):
    """Attestation payload with signatures and quorum rules."""

    signatures: List[str] = Field(default_factory=list)
    quorum_rule: str


class Lineage(BaseModel):
    """Describes parentage and forks for a registry entry."""

    parent: Optional[str] = None
    forks: List[str] = Field(default_factory=list)
    immutable: bool = True


class ReplayRules(BaseModel):
    """Replay governance data for the entry."""

    authorized: bool
    conditions: List[str] = Field(default_factory=list)
    override_protocol: Optional[str] = None


class RegistryEntry(BaseModel):
    """Represents one artifact entry inside the SSOT binder."""

    artifact_id: str
    entry_type: str = Field(alias="type")
    author: str
    created_at: datetime
    canonical_sha256: str
    council_attestation: CouncilAttestation
    lineage: Lineage
    replay: ReplayRules
    capsule_ref: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        """Pydantic config."""
        populate_by_name = True
        str_strip_whitespace = True

    @field_validator("entry_type")
    @classmethod
    def validate_entry_type(cls, value: str) -> str:
        """Validate the canonical registry entry types."""
        allowed = {
            "asset",
            "checkpoint",
            "clip",
            "design",
            "relay",
            "script",
            "simulation",
            "storyboard",
        }
        if value not in allowed:
            raise ValueError(f"entry type '{value}' is not part of the canonical binder")
        return value

    def leaf_hash(self) -> str:
        """Return the SHA-256 hash of the entry payload.

        The JSON serialization is deterministic to ensure the Merkle root is
        reproducible across runs and environments.
        """

        data = self.model_dump(by_alias=True, exclude={"notes"}, mode="json")
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class RegistryEnvelope(BaseModel):
    """Top-level capsule structure holding the registry."""

    capsule_id: str
    registry: RegistryContext
    entries: List[RegistryEntry]

    class Config:
        """Pydantic config."""
        populate_by_name = True
        str_strip_whitespace = True

    @field_validator("entries")
    @classmethod
    def ensure_sorted_entries(cls, value: Sequence[RegistryEntry]) -> List[RegistryEntry]:
        """Keep entries sorted locally by artifact_id before sealing."""
        return sorted(value, key=lambda entry: entry.artifact_id)


# ---------------------------------------------------------------------------
# Merkle helpers
# ---------------------------------------------------------------------------


def _hash_pair(left: str, right: str) -> str:
    """Return the hash of two sibling nodes in the Merkle tree."""

    payload = f"{left}{right}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass
class MerkleTree:
    """Represents a simple binary Merkle tree built from entry hashes."""

    leaves: List[str]

    def root(self) -> str:
        """Compute the root hash."""
        if not self.leaves:
            return ""
        level = self.leaves[:]
        while len(level) > 1:
            if len(level) % 2 == 1:
                level.append(level[-1])
            level = [_hash_pair(level[i], level[i + 1]) for i in range(0, len(level), 2)]
        return level[0]


# ---------------------------------------------------------------------------
# Binder runtime utilities
# ---------------------------------------------------------------------------


class SSOTBinder:
    """Utility wrapper around the registry envelope with helper methods."""

    def __init__(self, envelope: RegistryEnvelope):
        self._envelope = envelope
        self._entry_map: Dict[str, RegistryEntry] = {
            entry.artifact_id: entry for entry in self._envelope.entries
        }
        self._merkle = MerkleTree([entry.leaf_hash() for entry in self._envelope.entries])

    @property
    def capsule_id(self) -> str:
        """Return the capsule id."""
        return self._envelope.capsule_id

    @property
    def registry(self) -> RegistryContext:
        """Return the registry context."""
        return self._envelope.registry

    @property
    def entries(self) -> List[RegistryEntry]:
        """Return a copy of the entries list."""
        return list(self._envelope.entries)

    @property
    def merkle_root(self) -> str:
        """Return the calculated Merkle root."""
        return self._merkle.root()

    def get_entry(self, artifact_id: str) -> Optional[RegistryEntry]:
        """Fetch an entry by its artifact id."""
        return self._entry_map.get(artifact_id)

    def as_dict(self) -> Dict[str, object]:
        """Serialize the binder envelope with Merkle metadata."""

        entries = []
        for entry in self._envelope.entries:
            payload = entry.model_dump(by_alias=True)
            payload["leaf_hash"] = entry.leaf_hash()
            entries.append(payload)
        return {
            "capsule_id": self.capsule_id,
            "registry": self.registry.model_dump(),
            "entries": entries,
            "merkle_root": self.merkle_root,
        }

    def validate_candidate(self, candidate_data: Dict[str, object]) -> Dict[str, object]:
        """Validate a prospective entry and preview its Merkle root."""

        try:
            candidate = RegistryEntry.model_validate(candidate_data)
        except ValidationError as exc:
            return {"valid": False, "errors": exc.errors()}

        if candidate.artifact_id in self._entry_map:
            return {
                "valid": False,
                "errors": [
                    {
                        "loc": ["artifact_id"],
                        "msg": "artifact already registered",
                        "type": "value_error.duplicate",
                    }
                ],
            }

        preview_root = self._candidate_merkle_root(candidate)
        payload = candidate.model_dump(by_alias=True)
        payload["leaf_hash"] = candidate.leaf_hash()
        return {"valid": True, "candidate": payload, "merkle_preview": preview_root}

    def _candidate_merkle_root(self, candidate: RegistryEntry) -> str:
        leaves = [entry.leaf_hash() for entry in self._envelope.entries]
        leaves.append(candidate.leaf_hash())
        tree = MerkleTree(leaves)
        return tree.root()


# ---------------------------------------------------------------------------
# Module-level helpers for loading data from disk
# ---------------------------------------------------------------------------


def _data_root() -> Path:
    return Path(__file__).resolve().parents[0] / "data"


def _registry_path() -> Path:
    return _data_root() / "ssot_registry.json"


@lru_cache()
def load_binder() -> SSOTBinder:
    """Load the SSOT binder from disk and return a helper wrapper."""

    path = _registry_path()
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    envelope = RegistryEnvelope.model_validate(payload)
    return SSOTBinder(envelope)


# Expose a module-level singleton for convenience.
binder = load_binder()

__all__ = [
    "CouncilAttestation",
    "Lineage",
    "MerkleTree",
    "RegistryContext",
    "RegistryEntry",
    "RegistryEnvelope",
    "ReplayRules",
    "SSOTBinder",
    "binder",
    "load_binder",
]
