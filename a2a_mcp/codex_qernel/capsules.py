"""Capsule discovery utilities for the CODEX qernel."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Dict, Iterable, List, Any


MANDATORY_KEYS = {"id", "version", "name"}


@dataclass(frozen=True)
class CapsuleManifest:
    """Representation of a capsule manifest."""

    capsule_id: str
    version: str
    name: str
    manifest_path: Path
    raw: Dict[str, Any]

    @classmethod
    def from_path(cls, path: Path) -> "CapsuleManifest":
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = MANDATORY_KEYS - data.keys()
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"capsule manifest {path} missing keys: {missing_list}")
        return cls(
            capsule_id=str(data["id"]),
            version=str(data["version"]),
            name=str(data["name"]),
            manifest_path=path,
            raw=data,
        )

    def short_dict(self) -> Dict[str, Any]:
        """Return a trimmed representation used by APIs."""

        return {
            "id": self.capsule_id,
            "version": self.version,
            "name": self.name,
            "manifest_path": self.manifest_path.as_posix(),
        }


def discover_capsule_manifests(directory: Path) -> List[CapsuleManifest]:
    """Return all capsule manifests beneath the given directory."""

    manifests: List[CapsuleManifest] = []
    if not directory.exists():
        return manifests
    for candidate in sorted(directory.rglob("*.json")):
        try:
            manifests.append(CapsuleManifest.from_path(candidate))
        except ValueError:
            continue
    return manifests


def map_capsules_by_id(manifests: Iterable[CapsuleManifest]) -> Dict[str, CapsuleManifest]:
    """Create a dictionary keyed by capsule identifier."""

    result: Dict[str, CapsuleManifest] = {}
    for manifest in manifests:
        result[manifest.capsule_id] = manifest
    return result
