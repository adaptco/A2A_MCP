#!/usr/bin/env python3
"""Verify cross-repo SSOT contract sync and legacy subtree boundaries."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Iterable

import yaml


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid manifest payload in {path}")
    return payload


def ensure_schema_sync(root: Path, manifest: dict) -> list[str]:
    errors: list[str] = []
    sync = manifest.get("policies", {}).get("schema_sync", {})
    canonical_path = sync.get("canonical_path")
    mirror_paths = sync.get("mirrors", [])
    if not canonical_path or not isinstance(mirror_paths, list):
        return ["Missing schema_sync policy in ownership manifest"]

    paths = [canonical_path, *mirror_paths]
    resolved = [(root / rel).resolve() for rel in paths]
    for rel, absolute in zip(paths, resolved):
        if not absolute.exists():
            errors.append(f"Missing contract file: {rel}")
    if errors:
        return errors

    hashes = [sha256_file(path) for path in resolved]
    if len(set(hashes)) != 1:
        for rel, digest in zip(paths, hashes):
            errors.append(f"{rel}: {digest}")
        errors.insert(0, "Schema contract drift detected across repos")
    return errors


def ensure_legacy_boundaries(root: Path, manifest: dict) -> list[str]:
    errors: list[str] = []
    legacy_paths = manifest.get("legacy_read_only_paths", [])
    if not isinstance(legacy_paths, list):
        return ["legacy_read_only_paths must be a list"]

    for rel in legacy_paths:
        path = (root / rel).resolve()
        if not path.exists():
            errors.append(f"Missing legacy subtree listed in manifest: {rel}")

    # Prevent new runtime coupling to legacy mirrors.
    runtime_roots = [
        root / "core-orchestrator" / "app",
        root / "core-orchestrator" / "apps",
        root / "core-orchestrator" / "src",
        root / "core-orchestrator" / "packages",
    ]
    needles = ("adaptco-core-orchestrator", "adaptco-ssot", "adaptco-previz")
    for runtime_root in runtime_roots:
        if not runtime_root.exists():
            continue
        for file_path in runtime_root.rglob("*"):
            if file_path.suffix not in {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs"}:
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            if any(needle in text for needle in needles):
                errors.append(f"Legacy subtree referenced by runtime file: {file_path}")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default="..",
        help="Path to workspace root containing core-orchestrator, SSOT, and ground",
    )
    parser.add_argument(
        "--manifest",
        default="core-orchestrator/manifests/federation_ownership.v1.yaml",
        help="Relative path to the ownership manifest from repo root",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.repo_root).resolve()
    manifest_path = (root / args.manifest).resolve()
    if not manifest_path.exists():
        print(f"Missing ownership manifest: {manifest_path}")
        return 1

    manifest = load_manifest(manifest_path)
    errors: list[str] = []
    errors.extend(ensure_schema_sync(root, manifest))
    errors.extend(ensure_legacy_boundaries(root, manifest))

    if errors:
        for error in errors:
            print(error)
        return 1

    print("Federation contract verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
