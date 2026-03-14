#!/usr/bin/env python3
"""Check for drift between deployed state and the source of truth."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from validate_ssot import ManifestError, ensure_keys, load_yaml, validate_modules


ROOT_KEYS = {"service", "version", "modules"}


def normalize_modules(modules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    for module in modules:
        ensure_keys(module, {"name", "status", "last_updated"}, f"module {module}")
        normalized[module["name"]] = module
    return normalized


def check_drift(ssot: dict[str, Any], deployed: dict[str, Any]) -> list[str]:
    drift: list[str] = []

    if ssot.get("service") != deployed.get("service"):
        drift.append("Service identifiers do not match")

    if ssot.get("version") == deployed.get("version"):
        pass
    else:
        drift.append(
            "Deployed version is out of sync with source of truth"
        )

    ssot_modules = normalize_modules(ssot["modules"])
    deployed_modules = normalize_modules(deployed["modules"])

    for name, module in ssot_modules.items():
        deployed_module = deployed_modules.get(name)
        if not deployed_module:
            drift.append(f"Module {name} missing from deployed state")
            continue

        if module["status"] != deployed_module["status"]:
            drift.append(
                f"Module {name} status mismatch: SSOT={module['status']} "
                f"deployed={deployed_module['status']}"
            )

    for name in deployed_modules.keys() - ssot_modules.keys():
        drift.append(f"Module {name} present in deployment but not SSOT")

    return drift


def validate_root(document: Any, context: str) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ManifestError(f"{context} manifest must be a mapping")
    ensure_keys(document, ROOT_KEYS, f"{context} manifest root")
    validate_modules(document["modules"])
    return document


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "ssot",
        nargs="?",
        default="manifests/ssot.yaml",
        help="Path to the source-of-truth manifest.",
    )
    parser.add_argument(
        "deployed",
        nargs="?",
        default="manifests/deployed.yaml",
        help="Path to the deployed manifest.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ssot_doc = validate_root(load_yaml(Path(args.ssot)), "Source-of-truth")
    deployed_doc = validate_root(load_yaml(Path(args.deployed)), "Deployed")

    drift = check_drift(ssot_doc, deployed_doc)
    if drift:
        for item in drift:
            print(f"DRIFT: {item}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        raise SystemExit(main())
    except ManifestError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
