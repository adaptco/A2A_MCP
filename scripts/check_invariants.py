import argparse
import json
from pathlib import Path

from jsonschema import Draft7Validator


def load_json(path: Path):
    return json.loads(path.read_text())


def validate_jsonl(schema_path: Path, jsonl_path: Path) -> None:
    schema = load_json(schema_path)
    validator = Draft7Validator(schema)
    errors = []
    for line_number, line in enumerate(jsonl_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        for error in validator.iter_errors(payload):
            errors.append(
                f"{jsonl_path}:{line_number}: {error.message} (path: {list(error.path)})"
            )
    if errors:
        raise ValueError("\n".join(errors))


def check_cie_manifest(manifest_path: Path) -> None:
    manifest = load_json(manifest_path)
    required_modules = {
        "synthetic.noise.injector.v1",
        "synthetic.contradiction.synth.v1",
    }

    module_ids = {module["moduleId"] for module in manifest.get("modules", [])}
    missing_modules = required_modules - module_ids
    if missing_modules:
        raise ValueError(
            f"Missing modules in manifest: {', '.join(sorted(missing_modules))}"
        )

    allowed_modules = set(
        manifest.get("operationalDirectives", {}).get("allowed_modules", [])
    )
    if not required_modules.issubset(allowed_modules):
        raise ValueError(
            "Manifest operationalDirectives.allowed_modules does not include all "
            "required modules."
        )

    validation_chain = manifest.get("audit_inputs", {}).get("validation_chain", [])
    if validation_chain != [
        "synthetic.noise.injector.v1",
        "synthetic.contradiction.synth.v1",
    ]:
        raise ValueError("Manifest audit_inputs.validation_chain must be SNI -> SCS.")

    routing = manifest.get("input_profile", {}).get("routing", {})
    for payload_type in ("text", "json"):
        route = routing.get(payload_type)
        if route != validation_chain:
            raise ValueError(
                f"Manifest input_profile.routing.{payload_type} must match validation_chain."
            )

    neutrality_modules = set(
        manifest.get("validation", {}).get("neutrality", {}).get("modules", [])
    )
    if neutrality_modules != required_modules:
        raise ValueError(
            "Manifest validation.neutrality.modules must exactly list SNI and SCS."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate core CI invariants.")
    parser.add_argument(
        "--cie-manifest",
        type=Path,
        default=Path("manifests/content_integrity_eval.json"),
    )
    parser.add_argument(
        "--audit-schema",
        type=Path,
        default=Path("schemas/cie_v1.audit_run.schema.json"),
    )
    parser.add_argument(
        "--audit-runs",
        type=Path,
        default=Path("ledger/cie_v1/audit_runs.stub.jsonl"),
    )
    args = parser.parse_args()

    check_cie_manifest(args.cie_manifest)
    validate_jsonl(args.audit_schema, args.audit_runs)


if __name__ == "__main__":
    main()
