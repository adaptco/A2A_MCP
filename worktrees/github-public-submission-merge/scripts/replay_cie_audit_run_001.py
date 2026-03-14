#!/usr/bin/env python3
"""
scripts/replay_cie_audit_run_001.py

CIE-V1 Audit Run 001:
- fail-closed corpus hashing
- sealed queries
- deterministic artifact emission
- replay identity assertion (hash equality)

Usage examples:
  python scripts/replay_cie_audit_run_001.py --seal-corpus
  python scripts/replay_cie_audit_run_001.py --run --ingest-cmd "python -m your.ingest --corpus-index {corpus_index} --store {store} --capsules {capsules}" \
    --query-cmd "python -m your.query --store {store} --queries {queries} --out-report {report}"
  python scripts/replay_cie_audit_run_001.py --run --replay-assert \
    --ingest-cmd "..." --query-cmd "..."
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = REPO_ROOT / "artifacts"
CORPUS_INDEX = REPO_ROOT / "audit_corpus_pack" / "corpus.index.v1.json"
AUDIT_QUERIES = REPO_ROOT / "audit_corpus_pack" / "audit_queries.json"
MANIFEST = REPO_ROOT / "manifest.json"
MCP_EXPORT = ARTIFACTS / "mcp_tools.export.json"

OUT_STORE = ARTIFACTS / "store.sqlite"
OUT_CAPSULES = ARTIFACTS / "capsules.jsonl"
OUT_REPORT = ARTIFACTS / "audit_report.json"
OUT_RUN = ARTIFACTS / "cie.audit_run.001.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_stable_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json_dumps(obj), encoding="utf-8")


def remove_pycache(root: Path) -> List[str]:
    removed = []
    for p in root.rglob("__pycache__"):
        if p.is_dir():
            shutil.rmtree(p)
            removed.append(str(p.relative_to(root)))
    return removed


def git_commit() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()
        return out
    except Exception:
        return "UNKNOWN"


def git_dirty() -> bool:
    try:
        out = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT).decode().strip()
        return bool(out)
    except Exception:
        return True


def compute_corpus_root_hash(index_obj: Dict[str, Any]) -> str:
    docs = index_obj["docs"]
    rows = [(d["doc_id"], d["sha256"], int(d["bytes"]), d["path"]) for d in docs]
    payload = stable_json_dumps(rows).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def seal_corpus_index() -> Dict[str, Any]:
    idx = json.loads(CORPUS_INDEX.read_text(encoding="utf-8"))
    docs = idx.get("docs", [])
    for d in docs:
        p = REPO_ROOT / d["path"]
        if not p.exists():
            raise SystemExit(f"Missing corpus file: {d['path']}")
        d["bytes"] = p.stat().st_size
        d["sha256"] = sha256_file(p)

    docs.sort(key=lambda x: x["doc_id"])
    idx["docs"] = docs
    idx["root_sha256"] = compute_corpus_root_hash(idx)

    write_stable_json(CORPUS_INDEX, idx)
    return idx


def fail_closed_check_corpus(index_obj: Dict[str, Any]) -> None:
    docs_dir = REPO_ROOT / "audit_corpus_pack" / "docs"
    allowed_paths = set()

    for d in index_obj["docs"]:
        p = REPO_ROOT / d["path"]
        allowed_paths.add(p.resolve())
        if not p.exists():
            raise SystemExit(f"FAIL: missing file {d['path']}")
        if sha256_file(p) != d["sha256"]:
            raise SystemExit(f"FAIL: sha256 mismatch {d['path']}")

    if index_obj.get("rules", {}).get("allow_extra_files_not_listed") is False:
        for p in docs_dir.rglob("*"):
            if p.is_file() and p.resolve() not in allowed_paths:
                raise SystemExit(
                    f"FAIL: extra unindexed file present: {p.relative_to(REPO_ROOT)}"
                )

    root = compute_corpus_root_hash(index_obj)
    if root != index_obj["root_sha256"]:
        raise SystemExit("FAIL: corpus root_sha256 mismatch")


def run_cmd(argv: Iterable[str]) -> None:
    cmd = list(argv)
    print("RUN:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=REPO_ROOT)


def format_command(template: str) -> List[str]:
    formatted = template.format(
        corpus_index=str(CORPUS_INDEX.relative_to(REPO_ROOT)),
        store=str(OUT_STORE.relative_to(REPO_ROOT)),
        capsules=str(OUT_CAPSULES.relative_to(REPO_ROOT)),
        queries=str(AUDIT_QUERIES.relative_to(REPO_ROOT)),
        report=str(OUT_REPORT.relative_to(REPO_ROOT)),
    )
    return shlex.split(formatted)


def export_mcp_tools() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    if not MCP_EXPORT.exists():
        write_stable_json(MCP_EXPORT, {"schema": "mcp.tools.export.v0", "tools": []})


def run_ingest_and_queries(ingest_cmd: str, query_cmd: str) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    for p in [OUT_STORE, OUT_CAPSULES, OUT_REPORT]:
        if p.exists():
            p.unlink()

    run_cmd(format_command(ingest_cmd))
    run_cmd(format_command(query_cmd))

    for p in [OUT_STORE, OUT_CAPSULES, OUT_REPORT]:
        if not p.exists():
            raise SystemExit(f"FAIL: expected artifact not produced: {p}")


def build_run_record(corpus_obj: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest_sha = sha256_file(MANIFEST) if MANIFEST.exists() else "sha256:missing"
    return {
        "schema": "cie.audit_run.v1",
        "run_id": "CIE-V1-AUDIT-RUN-001",
        "created_utc": now,
        "code_seal": {
            "repo": REPO_ROOT.name,
            "git_commit": git_commit(),
            "dirty": git_dirty(),
            "manifest_file": str(MANIFEST.relative_to(REPO_ROOT)) if MANIFEST.exists() else "manifest.json",
            "manifest_sha256": manifest_sha,
            "tool_surface_export_file": str(MCP_EXPORT.relative_to(REPO_ROOT)),
            "tool_surface_export_sha256": sha256_file(MCP_EXPORT),
        },
        "environment": {
            "os": platform.platform(),
            "python": sys.version.split()[0],
            "dependencies_lock": {
                "file": "pyproject.toml",
                "sha256": sha256_file(REPO_ROOT / "pyproject.toml"),
            },
        },
        "inputs": {
            "corpus": {
                "index_file": str(CORPUS_INDEX.relative_to(REPO_ROOT)),
                "index_sha256": sha256_file(CORPUS_INDEX),
                "root_sha256": corpus_obj["root_sha256"],
                "doc_count": len(corpus_obj["docs"]),
            },
            "queries": {
                "file": str(AUDIT_QUERIES.relative_to(REPO_ROOT)),
                "sha256": sha256_file(AUDIT_QUERIES),
                "count": len(json.loads(AUDIT_QUERIES.read_text(encoding="utf-8"))["queries"]),
            },
        },
        "outputs": {
            "store_sqlite": {
                "file": str(OUT_STORE.relative_to(REPO_ROOT)),
                "sha256": sha256_file(OUT_STORE),
            },
            "capsules": {
                "file": str(OUT_CAPSULES.relative_to(REPO_ROOT)),
                "sha256": sha256_file(OUT_CAPSULES),
            },
            "audit_report": {
                "file": str(OUT_REPORT.relative_to(REPO_ROOT)),
                "sha256": sha256_file(OUT_REPORT),
            },
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seal-corpus", action="store_true", help="Compute sha256/bytes/root hash and rewrite corpus index canonically.")
    ap.add_argument("--run", action="store_true", help="Execute audit ingest + queries and write cie.audit_run.001.json.")
    ap.add_argument("--replay-assert", action="store_true", help="Run twice and assert output hashes are identical.")
    ap.add_argument("--ingest-cmd", help="Command template for ingest (use {corpus_index} {store} {capsules}).")
    ap.add_argument("--query-cmd", help="Command template for query (use {store} {queries} {report} {capsules}).")
    args = ap.parse_args()

    removed = remove_pycache(REPO_ROOT)
    if removed:
        print("Removed __pycache__:", removed)

    export_mcp_tools()

    if args.seal_corpus:
        corpus_obj = seal_corpus_index()
        fail_closed_check_corpus(corpus_obj)
        print("Corpus sealed:", corpus_obj["root_sha256"])
        return

    if not args.run:
        print("Nothing to do. Use --seal-corpus or --run.")
        return

    if not args.ingest_cmd or not args.query_cmd:
        raise SystemExit("--ingest-cmd and --query-cmd are required for --run.")

    corpus_obj = json.loads(CORPUS_INDEX.read_text(encoding="utf-8"))
    fail_closed_check_corpus(corpus_obj)

    run_ingest_and_queries(args.ingest_cmd, args.query_cmd)
    run_record_1 = build_run_record(corpus_obj)
    write_stable_json(OUT_RUN, run_record_1)
    h1 = {k: v["sha256"] for k, v in run_record_1["outputs"].items()}

    if not args.replay_assert:
        print("Run complete. Wrote:", OUT_RUN)
        return

    run_ingest_and_queries(args.ingest_cmd, args.query_cmd)
    run_record_2 = build_run_record(corpus_obj)
    h2 = {k: v["sha256"] for k, v in run_record_2["outputs"].items()}

    if h1 != h2:
        raise SystemExit(f"FAIL: replay identity mismatch\nrun1={h1}\nrun2={h2}")

    print("PASS: replay identity check (hash match)")
    write_stable_json(OUT_RUN, run_record_2)
    print("Sealed:", OUT_RUN)


if __name__ == "__main__":
    main()
