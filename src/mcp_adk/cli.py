"""CLI for mcp-adk scaffolding and schema validation."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from jsonschema import Draft202012Validator

PACKAGE_ROOT = Path(__file__).resolve().parent
CONTRACTS_DIR = PACKAGE_ROOT / "contracts"
ARTIFACT_SCHEMAS_DIR = PACKAGE_ROOT / "artifact_schemas"
TEMPLATES_DIR = PACKAGE_ROOT / "templates"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_file(target: Path, schema: Path) -> None:
    Draft202012Validator(_load_json(schema)).validate(_load_json(target))


def _copy_template(template_name: str, destination: Path) -> None:
    template_root = TEMPLATES_DIR / template_name
    if not template_root.exists():
        raise ValueError(f"Unknown template: {template_name}")
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")
    shutil.copytree(template_root, destination)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcp-adk")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate")
    generate_sub = generate.add_subparsers(dest="target", required=True)
    for target in ("python-agent", "ts-agent"):
        command = generate_sub.add_parser(target)
        command.add_argument("name")

    validate = subparsers.add_parser("validate")
    validate_sub = validate.add_subparsers(dest="target", required=True)
    validate_contract = validate_sub.add_parser("contract")
    validate_contract.add_argument("file")
    validate_contract.add_argument(
        "--schema",
        default=str(CONTRACTS_DIR / "actuator_contract.json"),
        help="Path to contract schema",
    )
    validate_artifact = validate_sub.add_parser("artifact")
    validate_artifact.add_argument("file")
    validate_artifact.add_argument(
        "--schema",
        default=str(ARTIFACT_SCHEMAS_DIR / "receipt.json"),
        help="Path to artifact schema",
    )

    scaffold = subparsers.add_parser("scaffold")
    scaffold.add_argument("target", choices=["codex-adapter", "orchestration-agent"])

    attest = subparsers.add_parser("attest")
    attest.add_argument("receipt")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "generate":
        template = "python_agent" if args.target == "python-agent" else "ts_agent"
        _copy_template(template, Path(args.name))
        return 0

    if args.command == "validate":
        _validate_file(Path(args.file), Path(args.schema))
        return 0

    if args.command == "scaffold":
        source = PACKAGE_ROOT / ("codex_adapter.py" if args.target == "codex-adapter" else "orchestration_agent.py")
        destination = Path(source.name)
        if destination.exists():
            raise FileExistsError(f"Refusing to overwrite existing file: {destination}")
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return 0

    if args.command == "attest":
        receipt = _load_json(Path(args.receipt))
        required = {
            "actor",
            "trajectory",
            "invariants_passed",
            "environment_fingerprint",
            "diff_hash",
            "ci_reproduction",
            "timestamp",
        }
        missing = required.difference(receipt)
        if missing:
            raise ValueError(f"Invalid receipt. Missing fields: {sorted(missing)}")
        print("Receipt attested")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
