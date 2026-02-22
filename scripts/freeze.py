#!/usr/bin/env python3
"""Create a manifest snapshot in manifests/artifacts."""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
from pathlib import Path

from validate_ssot import load_yaml, validate_manifest

ARTIFACT_DIR = Path("manifests/artifacts")
DEFAULT_SOURCE = Path("manifests/ssot.yaml")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tag",
        help="Tag name for the frozen artifact. Defaults to timestamp.",
    )
    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
        help="Manifest file to snapshot.",
    )
    return parser.parse_args(argv)


def ensure_directory() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def derive_tag(tag: str | None) -> str:
    if tag:
        return tag
    return dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")


def write_snapshot(source: Path, tag: str) -> Path:
    destination = ARTIFACT_DIR / f"{tag}.yaml"
    shutil.copy2(source, destination)
    return destination


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ensure_directory()

    source = Path(args.source)
    document = load_yaml(source)
    validate_manifest(document)

    tag = derive_tag(args.tag)
    destination = write_snapshot(source, tag)
    print(f"Snapshot created at {destination}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
