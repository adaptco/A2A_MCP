#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGET_PATHS = [
    "src/prime_directive/api/app.py",
    "src/prime_directive/pipeline/engine.py",
    "src/prime_directive/validators/preflight.py",
    "src/prime_directive/sovereignty/chain.py",
    "docs/architecture/ws_protocol.md",
    "docs/architecture/sovereignty_log.md",
    "scripts/smoke_ws.sh",
]

FORBIDDEN_COMMITTED = ["exports", "staging", ".env", "*.db", "*.sqlite"]


def check_target_structure() -> list[str]:
    findings: list[str] = []
    for rel in TARGET_PATHS:
        path = ROOT / rel
        if not path.exists():
            findings.append(f"MISSING: {rel}")
    return findings


def flag_forbidden_artifacts() -> list[str]:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        rel = path.relative_to(ROOT)
        if rel.parts and rel.parts[0] in {"exports", "staging"}:
            findings.append(f"FORBIDDEN_ARTIFACT_DIR: {rel}")
        if rel.name == ".env" or rel.suffix in {".db", ".sqlite"}:
            findings.append(f"FORBIDDEN_ARTIFACT_FILE: {rel}")
    return findings


def flag_gate_logic_in_ws() -> list[str]:
    findings: list[str] = []
    for path in ROOT.rglob("*.py"):
        if ".git" in path.parts:
            continue
        if "ws" not in path.stem and "websocket" not in path.stem and "webhook" not in path.stem:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "preflight" in text or "c5" in text or "rsm" in text:
            findings.append(f"POTENTIAL_WS_GATE_COUPLING: {path.relative_to(ROOT)}")
    return findings


def suggest_moves() -> list[str]:
    suggestions = []
    mapping = {
        "orchestrator/stateflow.py": "src/prime_directive/pipeline/state_machine.py",
        "orchestrator/settlement.py": "src/prime_directive/sovereignty/chain.py",
        "orchestrator/webhook.py": "src/prime_directive/api/app.py (adapter first)",
    }
    for src, dst in mapping.items():
        if (ROOT / src).exists():
            suggestions.append(f"MOVE_CANDIDATE: {src} -> {dst}")
    return suggestions


def main() -> int:
    findings = []
    findings.extend(check_target_structure())
    findings.extend(flag_gate_logic_in_ws())
    findings.extend(flag_forbidden_artifacts())
    findings.extend(suggest_moves())

    if not findings:
        print("Audit OK: no findings")
        return 0

    print("Audit findings:")
    for item in findings:
        print(f" - {item}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
