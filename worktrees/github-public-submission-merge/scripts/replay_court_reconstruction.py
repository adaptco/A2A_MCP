import hashlib
import json
from pathlib import Path

import yaml


def canonicalize_jcs(data: dict) -> str:
    """Implements JSON Canonicalization Scheme (RFC 8785) for YAML objects."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def verify_fossil(path_to_yaml: str) -> bool:
    """Verifies the integrity of a fossil artifact against its digest."""
    artifact_path = Path(path_to_yaml)
    artifact = yaml.safe_load(artifact_path.read_text(encoding="utf-8"))

    provided_digest = artifact.pop("digest")
    computed_digest = hashlib.sha256(canonicalize_jcs(artifact).encode()).hexdigest()

    return provided_digest == computed_digest


if __name__ == "__main__":
    fossil_path = "validation/fossils/AgentProposalReceipt.v1.yaml"
    if verify_fossil(fossil_path):
        print("Replay court verified.")
    else:
        raise SystemExit("Replay court verification failed.")
