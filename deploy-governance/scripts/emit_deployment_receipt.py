#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEAL_PHRASE = "Canonical truth, attested and replayable."


def jcs_dumps(obj: Any) -> str:
    """Deterministic JSON serialization."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(cmd: list[str]) -> str:
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    return output.decode("utf-8", errors="strict").strip()


def env_hash_redacted(env_path: Path) -> str:
    """
    Hash .env without revealing values:
    - Keep declared order.
    - Normalize lines to KEY=<redacted>.
    - Reject invalid env syntax.
    """
    raw = env_path.read_text(encoding="utf-8")
    normalized: list[str] = []

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ValueError(f"env_hash: invalid line (missing '='): {line!r}")
        key, _ = stripped.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Z0-9_]+", key):
            raise ValueError(f"env_hash: invalid key: {key!r}")
        normalized.append(f"{key}=<redacted>")

    return sha256_bytes("\n".join(normalized).encode("utf-8"))


def image_digest_from_compose(compose_file: Path, service: str) -> str:
    """Resolve digest selected by docker compose for a service."""
    config_json = run(
        [
            "docker",
            "compose",
            "-f",
            str(compose_file),
            "config",
            "--format",
            "json",
        ]
    )
    config = json.loads(config_json)
    services = config.get("services", {})
    if service not in services:
        raise ValueError(f"compose: service not found: {service}")

    image_ref = services[service].get("image")
    if not image_ref:
        raise ValueError(f"compose: service has no image: {service}")

    if "@sha256:" in image_ref:
        digest = "sha256:" + image_ref.split("@sha256:", 1)[1]
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
            raise ValueError(f"invalid digest in image ref: {image_ref}")
        return digest

    inspect = run(["docker", "image", "inspect", image_ref, "--format", "{{json .RepoDigests}}"])
    repo_digests = json.loads(inspect)
    if not repo_digests:
        raise ValueError(
            f"docker inspect: no RepoDigests for image {image_ref} "
            "(image may not be pulled/built)"
        )

    digest = repo_digests[0].split("@", 1)[-1].strip()
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError(f"docker inspect: unexpected digest format: {digest}")
    return digest


def compute_deployment_id(payload: dict[str, Any]) -> str:
    core = {
        "schema_version": payload["schema_version"],
        "ts_utc": payload["ts_utc"],
        "mode": payload["mode"],
        "hashes": payload["hashes"],
        "images": payload["images"],
        "inputs": payload["inputs"],
        "governance": payload["governance"],
    }
    return "sha256:" + sha256_bytes(jcs_dumps(core).encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compose", required=True)
    parser.add_argument("--dockerfile-bot", required=True)
    parser.add_argument("--env", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument(
        "--service",
        action="append",
        required=True,
        help="Service name(s) to bind digest for (repeatable)",
    )
    parser.add_argument("--mode", choices=["dry_run", "apply"], required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--status", choices=["success", "fail"], required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--summary", default="")
    args = parser.parse_args()

    compose = Path(args.compose)
    dockerfile = Path(args.dockerfile_bot)
    env_file = Path(args.env)
    policy = Path(args.policy)

    for required in (compose, dockerfile, env_file, policy):
        if not required.exists():
            raise SystemExit(f"missing file: {required}")

    payload: dict[str, Any] = {
        "schema_version": "deployment.receipt.v1",
        "ts_utc": utc_now_z(),
        "mode": args.mode,
        "status": args.status,
        "inputs": {
            "compose_file": str(compose),
            "dockerfile_bot": str(dockerfile),
            "env_file": str(env_file),
        },
        "hashes": {
            "compose_sha256": sha256_file(compose),
            "dockerfile_sha256": sha256_file(dockerfile),
            "env_sha256": env_hash_redacted(env_file),
            "policy_sha256": sha256_file(policy),
        },
        "images": [],
        "result": {
            "exit_code": args.exit_code,
            "summary": args.summary[:4096],
        },
        "governance": {
            "seal_phrase": SEAL_PHRASE,
        },
    }

    for service in args.service:
        payload["images"].append(
            {
                "name": service,
                "digest": image_digest_from_compose(compose, service),
            }
        )

    payload["images"] = sorted(payload["images"], key=lambda item: item["name"])
    payload["deployment_id"] = compute_deployment_id(payload)

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(jcs_dumps(payload) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
