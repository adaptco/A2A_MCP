#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$ROOT_DIR/fixtures"

python3 - <<'PY' "$ROOT_DIR" "$OUT_DIR"
import json
import pathlib
import collections

root = pathlib.Path(__import__('sys').argv[1])
out = pathlib.Path(__import__('sys').argv[2])
registry_path = root / "runtime" / "frozen" / "capsule.registry.runtime.v1.json"
metaagent_path = root / "capsules" / "capsule.metaagent.solf1.oneshot.v1.json"

registry = json.loads(registry_path.read_text(encoding="utf-8"))
metaagent = json.loads(metaagent_path.read_text(encoding="utf-8"))

capsules = registry.get("capsules", {})
state_counts = collections.Counter(entry.get("state", "UNKNOWN") for entry in capsules.values())

def sorted_capsules(predicate):
    return sorted([
        capsule_id
        for capsule_id, entry in capsules.items()
        if predicate(entry)
    ])

frozen_capsules = sorted_capsules(lambda entry: entry.get("state") == "FROZEN")

link_summary = {}
for link in registry.get("links", []):
    bucket = link_summary.setdefault(link["type"], [])
    bucket.append({"from": link["from"], "to": link["to"]})

for link_type in list(link_summary.keys()):
    link_summary[link_type] = sorted(link_summary[link_type], key=lambda item: (item["from"], item["to"]))

snapshot = {
    "snapshot_id": "registry-runtime-v1",
    "captured_at": registry.get("issued_at"),
    "source": registry_path.as_posix(),
    "bundles": registry.get("bundles", []),
    "capsule_summary": {
        "total": len(capsules),
        "states": dict(state_counts),
        "frozen_capsules": frozen_capsules,
    },
    "link_summary": dict(sorted(link_summary.items())),
    "health": registry.get("health", {}),
    "metaagent_overrides": {
        "capsule.metaagent.solf1.oneshot.v1": {
            "status": metaagent.get("status"),
            "schema": metaagent.get("schema"),
            "anchors": metaagent.get("anchors", {}),
            "inputs": metaagent.get("inputs", {}),
            "outputs": metaagent.get("outputs", {}),
        }
    },
}

out.mkdir(parents=True, exist_ok=True)
(snapshot_path := out / "snapshot.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")

print(f"wrote {snapshot_path.relative_to(root)}")
PY
