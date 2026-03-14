"""Deterministically mirror canonical chatgpt-app package into warped-cosmic worktree."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


CANONICAL_ROOT = Path(__file__).resolve().parents[1] / "chatgpt-app"
DEFAULT_MIRROR = Path(r"C:\Users\eqhsp\.codex\worktrees\47cf\projects\chatgpt-app")
MIRROR_ROOT = Path(os.getenv("CHATGPT_APP_MIRROR_PATH", str(DEFAULT_MIRROR)))
MANIFEST_NAME = "mirror-manifest.json"
IGNORED_PARTS = {"node_modules", "dist", ".git", "__pycache__"}


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.name == MANIFEST_NAME:
            continue
        files.append(path)
    return files


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_remove_empty_dirs(root: Path) -> None:
    for directory in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            continue


def _sync() -> dict[str, object]:
    if not CANONICAL_ROOT.exists():
        raise SystemExit(f"Canonical path does not exist: {CANONICAL_ROOT}")

    MIRROR_ROOT.mkdir(parents=True, exist_ok=True)
    source_files = _iter_files(CANONICAL_ROOT)
    copied_rel_paths: set[Path] = set()
    manifest_files: list[dict[str, object]] = []

    for source in source_files:
        rel = source.relative_to(CANONICAL_ROOT)
        target = MIRROR_ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied_rel_paths.add(rel)
        manifest_files.append(
            {
                "path": rel.as_posix(),
                "sha256": _sha256(source),
                "bytes": source.stat().st_size,
            }
        )

    # Remove stale files from mirror.
    for target_file in _iter_files(MIRROR_ROOT):
        rel = target_file.relative_to(MIRROR_ROOT)
        if rel not in copied_rel_paths:
            target_file.unlink()
    _safe_remove_empty_dirs(MIRROR_ROOT)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(CANONICAL_ROOT),
        "target": str(MIRROR_ROOT),
        "file_count": len(manifest_files),
        "files": manifest_files,
    }
    canonical_manifest = CANONICAL_ROOT / MANIFEST_NAME
    mirror_manifest = MIRROR_ROOT / MANIFEST_NAME
    canonical_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    mirror_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = _sync()
    print(
        json.dumps(
            {
                "status": "ok",
                "source": result["source"],
                "target": result["target"],
                "file_count": result["file_count"],
            },
            indent=2,
        )
    )
