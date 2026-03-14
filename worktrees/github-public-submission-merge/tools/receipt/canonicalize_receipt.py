#!/usr/bin/env python3
"""Build canonical hash surface JSON for merge receipts and write digest metadata."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from collections import OrderedDict
from pathlib import Path

import yaml

HASH_SURFACE_ORDER = [
    "receipt_version",
    "type",
    "repo.slug",
    "repo.origin_url",
    "pull_request.number",
    "pull_request.base_ref",
    "pull_request.head_ref",
    "pointers.base_before",
    "pointers.head_sha",
    "merge.method",
    "merge.no_ff",
    "toolchain.git_version",
    "toolchain.gh_version",
]

GITHUB_SSH_RE = re.compile(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$")
GITHUB_HTTPS_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value).replace("\r\n", "\n")


def get_path(obj: dict, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def set_path(obj: dict, dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cur = obj
    for idx, part in enumerate(parts):
        if idx == len(parts) - 1:
            cur[part] = value
            return
        if part not in cur or not isinstance(cur[part], dict):
            cur[part] = {}
        cur = cur[part]


def build_hash_surface(receipt: dict, strict: bool) -> OrderedDict:
    flat = OrderedDict()
    missing = []

    for key in HASH_SURFACE_ORDER:
        value = get_path(receipt, key)
        if value is None:
            missing.append(key)
        if isinstance(value, str):
            value = nfc(value)
        flat[key] = value if value is not None else None

    if strict and missing:
        raise ValueError(f"Missing required hash-surface field(s): {', '.join(missing)}")

    nested = OrderedDict()
    for dotted, value in flat.items():
        cur = nested
        for idx, part in enumerate(dotted.split(".")):
            if idx == len(dotted.split(".")) - 1:
                cur[part] = value
            else:
                if part not in cur:
                    cur[part] = OrderedDict()
                cur = cur[part]
    return nested


def canonical_json(obj: dict) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False, sort_keys=True)


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def normalize_origin_url(url: str) -> str:
    url = url.strip()
    ssh_match = GITHUB_SSH_RE.match(url)
    if ssh_match:
        org, repo = ssh_match.group(1), ssh_match.group(2)
        return f"https://github.com/{org}/{repo}.git"

    https_match = GITHUB_HTTPS_RE.match(url)
    if https_match:
        org, repo = https_match.group(1), https_match.group(2)
        return f"https://github.com/{org}/{repo}.git"

    return url


def gpg_detached_sign(input_path: Path, sig_out: Path) -> None:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    # You might want to log result.stdout or result.stderr if needed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt_path")
    parser.add_argument("--strict", action="store_true", help="Fail if any hash-surface field is missing")
    parser.add_argument(
        "--normalize-origin-url",
        action="store_true",
        help="Normalize repo.origin_url to https://github.com/...git when possible",
    )
    parser.add_argument("--write-back", action="store_true", help="Write updates back to the input YAML file")
    parser.add_argument("--out", default=None, help="Write updated YAML to this path instead of in-place")
    parser.add_argument("--emit-hash-surface", action="store_true", help="Embed hash_surface object in output YAML")
    parser.add_argument("--gpg-sign", action="store_true", help="Produce detached GPG signature for the output YAML")
    parser.add_argument("--sig-out", default=None, help="Signature output path (default: <out>.asc)")
    args = parser.parse_args()

    input_path = Path(args.receipt_path)
    if not input_path.exists():
        print(f"File not found: {input_path}", file=sys.stderr)
        return 2

    receipt = yaml.safe_load(input_path.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        print("Receipt must be a YAML mapping/object at root.", file=sys.stderr)
        return 2

    origin = get_path(receipt, "repo.origin_url")
    if args.normalize_origin_url and isinstance(origin, str):
        set_path(receipt, "repo.origin_url", normalize_origin_url(origin))

    try:
        hash_surface = build_hash_surface(receipt, strict=args.strict)
    except ValueError as err:
        print(str(err), file=sys.stderr)
        return 2

    hash_surface_json = canonical_json(hash_surface)
    digest = sha256_hex(hash_surface_json.encode("utf-8"))

    if "integrity" not in receipt or not isinstance(receipt["integrity"], dict):
        receipt["integrity"] = {}
    receipt["integrity"]["hash_surface_sha256"] = digest

    if args.emit_hash_surface:
        receipt["hash_surface"] = json.loads(hash_surface_json)

    if args.out:
        out_path = Path(args.out)
    elif args.write_back:
        out_path = input_path
    else:
        out_path = input_path.with_suffix(input_path.suffix + ".final.yaml")

    out_path.write_text(yaml.safe_dump(receipt, sort_keys=True, allow_unicode=True), encoding="utf-8")

    canon_path = out_path.with_suffix(out_path.suffix + ".hash_surface.canonical.json")
    canon_path.write_text(hash_surface_json, encoding="utf-8")

    if args.gpg_sign:
        sig_out = Path(args.sig_out) if args.sig_out else out_path.with_suffix(out_path.suffix + ".asc")
        gpg_detached_sign(out_path, sig_out)

        signed_receipt = yaml.safe_load(out_path.read_text(encoding="utf-8"))
        if "integrity" not in signed_receipt or not isinstance(signed_receipt["integrity"], dict):
            signed_receipt["integrity"] = {}
        signed_receipt["integrity"]["signature_sha256"] = sha256_hex(sig_out.read_bytes())
        signed_receipt["integrity"]["signature_method"] = "gpg-detached-armor"
        out_path.write_text(yaml.safe_dump(signed_receipt, sort_keys=True, allow_unicode=True), encoding="utf-8")

    print("=== Canonical Hash Surface JSON ===")
    print(hash_surface_json)
    print("\n=== SHA-256 (hex) ===")
    print(digest)
    print(f"\nWrote YAML: {out_path}")
    print(f"Wrote canonical surface: {canon_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
