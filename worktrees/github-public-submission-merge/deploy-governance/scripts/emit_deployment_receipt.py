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
    # Deterministic JSON: sorted keys, compact, utf-8, fail closed on NaN/Inf.
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def utc_now_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(cmd: list[str]) -> str:
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    return out.decode("utf-8", errors="strict").strip()


def env_hash_redacted(env_path: Path) -> str:
    """
    Hashes .env file content without leaking secrets:
    - Hash the normalized line structure (KEY=<redacted>) preserving key order.
    - Fail closed if file contains non-utf8.
    """
    raw = env_path.read_text(encoding="utf-8")
    lines = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            # Fail closed: env files must be KEY=VALUE
            raise ValueError(f"env_hash: invalid line (missing '='): {line!r}")
        k, _v = s.split("=", 1)
        k = k.strip()
        if not re.fullmatch(r"[A-Z0-9_]+", k):
            raise ValueError(f"env_hash: invalid key: {k!r}")
        lines.append(f"{k}=<redacted>")
    norm = "\n".join(lines).encode("utf-8")
    return sha256_bytes(norm)


def image_digest_from_compose(compose_file: Path, service: str) -> str:
    """
    Resolve the image digest actually selected by compose for a given service.
    Requires docker compose v2.
    """
    cfg = run(["docker", "compose", "-f", str(compose_file), "config", "--format", "json"])
    cfgj = json.loads(cfg)
    services = cfgj.get("services", {})
    if service not in services:
        raise ValueError(f"compose: service not found: {service}")
    img_ref = services[service].get("image")
    if not img_ref:
        raise ValueError(f"compose: service has no image: {service}")

    # If img_ref includes a digest already, normalize it.
    if "@sha256:" in img_ref:
        digest = "sha256:" + img_ref.split("@sha256:", 1)[1]
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
            raise ValueError(f"invalid digest in image ref: {img_ref}")
        return digest

    # Inspect RepoDigests; pick the first matching digest.
    inspect = run(["docker", "image", "inspect", img_ref, "--format", "{{json .RepoDigests}}"])
    repodigests = json.loads(inspect)
    if not repodigests:
        raise ValueError(
            f"docker inspect: no RepoDigests for image {img_ref} (image may not be pulled/built)"
        )
    digest = repodigests[0].split("@", 1)[-1].strip()
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError(f"docker inspect: unexpected digest format: {digest}")
    return digest


def compute_deployment_id(payload: dict[str, Any]) -> str:
    # deployment_id binds the pre-deploy snapshot + digests + mode.
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--compose", required=True)
    ap.add_argument("--dockerfile-bot", required=True)
    ap.add_argument("--env", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument(
        "--service",
        action="append",
        required=True,
        help="Service name(s) to bind digest for (repeatable)",
    )
    ap.add_argument("--mode", choices=["dry_run", "apply"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--status", choices=["success", "fail"], required=True)
    ap.add_argument("--exit-code", type=int, required=True)
    ap.add_argument("--summary", default="")
    args = ap.parse_args()

    compose = Path(args.compose)
    dockerfile = Path(args.dockerfile_bot)
    envp = Path(args.env)
    policy = Path(args.policy)

    for p in (compose, dockerfile, envp, policy):
        if not p.exists():
            raise SystemExit(f"missing file: {p}")

    payload: dict[str, Any] = {
        "schema_version": "deployment.receipt.v1",
        "ts_utc": utc_now_z(),
        "mode": args.mode,
        "status": args.status,
        "inputs": {
            "compose_file": str(compose),
            "dockerfile_bot": str(dockerfile),
            "env_file": str(envp),
        },
        "hashes": {
            "compose_sha256": sha256_file(compose),
            "dockerfile_sha256": sha256_file(dockerfile),
            "env_sha256": env_hash_redacted(envp),
            "policy_sha256": sha256_file(policy),
        },
        "images": [],
        "result": {
            "exit_code": args.exit_code,
            "summary": args.summary[:4096],
        },
        "governance": {"seal_phrase": SEAL_PHRASE},
    }

    for svc in args.service:
        digest = image_digest_from_compose(compose, svc)
        payload["images"].append({"name": svc, "digest": digest})

    # Deterministic ordering
    payload["images"] = sorted(payload["images"], key=lambda x: x["name"])

    payload["deployment_id"] = compute_deployment_id(payload)

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(jcs_dumps(payload) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
