#!/usr/bin/env python3
"""Package Scrollstream capsule bundle into Format B (.qcap)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence
import zipfile


@dataclass
class Attachment:
    source: Path
    arcname: str
    data: bytes
    sha256: str
    size: int

    @classmethod
    def from_path(cls, source: Path, arcname: str) -> "Attachment":
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        return cls(source=source, arcname=arcname, data=data, sha256=digest, size=len(data))


def parse_attachment_specs(specs: Sequence[str]) -> List[Attachment]:
    attachments: List[Attachment] = []
    for spec in specs:
        if ":" in spec:
            path_str, arcname = spec.split(":", 1)
        else:
            path_str, arcname = spec, None
        path = Path(path_str)
        if not path.is_file():
            raise FileNotFoundError(f"Attachment not found: {path}")
        if arcname is None or not arcname:
            arcname = path.as_posix()
        attachments.append(Attachment.from_path(path, arcname))
    return attachments


def canonicalize_json(path: Path) -> bytes:
    data = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return canonical.encode("utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_metadata(manifest_bytes: bytes, manifest: dict, attachments: Sequence[Attachment]) -> bytes:
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    metadata = {
        "format": "scrollstream/capsule-b",
        "version": "1.0",
        "generated_at": now_iso(),
        "capsule_id": manifest.get("capsule_id"),
        "capsule_version": manifest.get("version"),
        "manifest_sha256": manifest_sha,
        "attachments": [
            {
                "path": attachment.arcname,
                "bytes": attachment.size,
                "sha256": attachment.sha256,
            }
            for attachment in attachments
        ],
    }
    return json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a Scrollstream Capsule Format B (.qcap)")
    parser.add_argument("--manifest", required=True, type=Path, help="Primary capsule manifest JSON")
    parser.add_argument(
        "--attachment",
        action="append",
        default=[],
        help="Attachment spec as <path>[:<arcname>] (can be repeated)",
    )
    parser.add_argument("--output", required=True, type=Path, help="Output .qcap path")
    args = parser.parse_args(argv)

    manifest_path: Path = args.manifest
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    attachments = parse_attachment_specs(args.attachment)

    manifest_bytes = canonicalize_json(manifest_path)
    manifest = json.loads(manifest_bytes)

    metadata_bytes = build_metadata(manifest_bytes, manifest, attachments)

    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("FORMAT", b"Scrollstream Capsule B\n")
        zf.writestr("capsule.json", manifest_bytes)
        zf.writestr("metadata.json", metadata_bytes)
        for attachment in attachments:
            zf.writestr(f"attachments/{attachment.arcname}", attachment.data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
