#!/usr/bin/env python3
"""Validate the source-of-truth manifest for selector preview bundles."""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml


REQUIRED_ROOT_KEYS = {"service", "version", "modules"}
MODULE_REQUIRED_KEYS = {"name", "status", "last_updated"}
ALLOWED_STATUSES = {"active", "passive", "rehearsal-only"}


class ManifestError(RuntimeError):
    """Raised when the manifest fails validation."""


def load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except FileNotFoundError as exc:  # pragma: no cover - surfaced to CLI
        raise ManifestError(f"Manifest not found: {path}") from exc
    except yaml.YAMLError as exc:  # pragma: no cover - surfaced to CLI
        raise ManifestError(f"Invalid YAML in {path}: {exc}") from exc


def ensure_keys(section: dict[str, Any], required: Iterable[str], context: str) -> None:
    missing = [key for key in required if key not in section]
    if missing:
        raise ManifestError(f"Missing keys in {context}: {', '.join(sorted(missing))}")


def validate_modules(modules: Iterable[Any]) -> None:
    if not isinstance(modules, list) or not modules:
        raise ManifestError("modules must be a non-empty list")

    names: set[str] = set()
    for module in modules:
        if not isinstance(module, dict):
            raise ManifestError("Each module must be a mapping")
        ensure_keys(module, MODULE_REQUIRED_KEYS, f"module {module}")

        name = module["name"]
        if name in names:
            raise ManifestError(f"Duplicate module name detected: {name}")
        names.add(name)

        status = module["status"]
        if status not in ALLOWED_STATUSES:
            raise ManifestError(
                f"Invalid status '{status}' for module {name}. "
                f"Allowed: {', '.join(sorted(ALLOWED_STATUSES))}"
            )

        last_updated = module["last_updated"]
        if isinstance(last_updated, str):
            try:
                dt.date.fromisoformat(last_updated)
            except ValueError as exc:
                raise ManifestError(
                    f"Module {name} last_updated must be an ISO date string"
                ) from exc
        elif isinstance(last_updated, dt.date):
            module["last_updated"] = last_updated.isoformat()
        else:
            raise ManifestError(
                f"Module {name} last_updated must be a date or ISO string"
            )


def validate_manifest(document: Any) -> None:
    if not isinstance(document, dict):
        raise ManifestError("Manifest root must be a mapping")

    ensure_keys(document, REQUIRED_ROOT_KEYS, "manifest root")
    validate_modules(document["modules"])


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "manifest",
        nargs="?",
        default="manifests/ssot.yaml",
        help="Path to the SSOT manifest to validate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest_path = Path(args.manifest)
    document = load_yaml(manifest_path)
    validate_manifest(document)
    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        raise SystemExit(main())
    except ManifestError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
