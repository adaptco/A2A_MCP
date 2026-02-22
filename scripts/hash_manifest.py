#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INCLUDE = ["model", "scripts", "eval", "docs", "runtime"]
manifest = {}
for d in INCLUDE:
    p = ROOT / d
    if not p.exists():
        continue
    for path in p.rglob("*"):
        if path.is_file():
            rel = path.relative_to(ROOT)
            if rel.as_posix() in {"runtime/freeze_manifest.json", "runtime/sandbox_log.jsonl"}:
                continue
            with path.open("rb") as f:
                digest = hashlib.sha256(f.read()).hexdigest()
            manifest[rel.as_posix()] = digest

out = ROOT / "runtime" / "freeze_manifest.json"
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w") as f:
    json.dump(manifest, f, indent=2, sort_keys=True)
print(f"wrote {out}")
