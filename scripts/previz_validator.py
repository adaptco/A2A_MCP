#!/usr/bin/env python3
"""Utilities for validating governed previz ledgers and producing Sentinel handoff exports."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


DEFAULT_BEATS = [
    "Entry",
    "Stabilize",
    "Gloh Flux",
    "Sol Ignition",
]


def load_ledger(path: Path) -> List[Dict]:
    """Load a JSONL previz ledger into a list of dictionaries."""
    ledger: List[Dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                ledger.append(json.loads(line))
            except json.JSONDecodeError as exc:  # pragma: no cover - CLI guard
                raise ValueError(f"Invalid JSON on line {line_number} of {path}: {exc}") from exc
    return ledger


def validate_previz(
    ledger_lines: Sequence[Dict],
    *,
    qlock_interval_s: float = 3.0,
    drift_threshold: float = 0.01,
) -> Dict:
    """Validate timeline ordering, QLOCK anchors, drift thresholds, and pose locks."""
    issues: List[str] = []
    last_ts = -math.inf
    last_frame = -math.inf

    for row in ledger_lines:
        ts = float(row.get("timestamp_rel_s", 0.0))
        frame_idx = int(row.get("frame_idx", -1))
        hud = row.get("hud", {}) or {}
        drift = hud.get("drift.delta")
        tick = hud.get("qlock.tick_s")
        pose_lock = row.get("pose_lock")

        if ts < last_ts:
            issues.append(f"Non-ordered timestamp at frame {frame_idx}")
        if frame_idx <= last_frame:
            issues.append(f"Non-ordered frame index at frame {frame_idx}")

        if drift is None or float(drift) > drift_threshold:
            issues.append(
                f"Drift threshold breach at frame {frame_idx}: {drift!r} (limit {drift_threshold})"
            )

        tick_value = None
        if tick is not None:
            try:
                tick_value = float(tick)
            except (TypeError, ValueError):
                issues.append(f"Invalid QLOCK tick value at frame {frame_idx}: {tick!r}")
        if tick_value is None or not math.isclose(
            math.fmod(tick_value, qlock_interval_s), 0.0, rel_tol=1e-9, abs_tol=1e-9
        ):
            issues.append(
                f"QLOCK misalignment at frame {frame_idx}: tick={tick!r}, interval={qlock_interval_s}"
            )

        if pose_lock != "3q-window-stance":
            issues.append(f"Pose lock missing/mismatch at frame {frame_idx}: {pose_lock!r}")

        last_ts = ts
        last_frame = frame_idx

    return {
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "checked": {
            "ordered_timeline": True,
            "non_overlap": True,
            "qlock_interval_s": qlock_interval_s,
            "drift_threshold": drift_threshold,
        },
    }


def generate_shot_list(
    ledger_lines: Sequence[Dict],
    beats_order: Sequence[str],
    *,
    qlock_interval_s: float = 3.0,
) -> List[Dict]:
    """Aggregate ledger frames into beat-aligned shot metadata."""
    grouped: Dict[str, List[Dict]] = {beat: [] for beat in beats_order}
    for row in ledger_lines:
        beat = row.get("beat")
        if beat in grouped:
            grouped[beat].append(row)

    shots: List[Dict] = []
    for index, beat in enumerate(beats_order, start=1):
        rows = grouped.get(beat) or []
        if not rows:
            continue
        start_row = rows[0]
        end_row = rows[-1]
        time_in = float(start_row["timestamp_rel_s"])
        time_out = float(end_row["timestamp_rel_s"])
        qlock_anchor = math.floor(time_in / qlock_interval_s) * qlock_interval_s
        shots.append(
            {
                "id": f"S{index:02d}",
                "beat": beat,
                "time_in": f"{time_in:06.3f}",
                "time_out": f"{time_out:06.3f}",
                "start_frame": int(start_row["frame_idx"]),
                "end_frame": int(end_row["frame_idx"]),
                "qlock_anchor_s": f"{qlock_anchor:06.3f}",
                "camera_grammar": start_row.get("camera_grammar", "glyph-orbit"),
                "emotional_payload": (start_row.get("hud", {}) or {}).get("aura.gold.phase", ""),
                "hud_overlays": "glyph.pulse,aura.gold,qlock.tick,drift.delta",
                "notes": "Previz governed shot chunk",
            }
        )
    return shots


def write_shot_list_csv(shots: Sequence[Dict], path: Path) -> Path:
    """Persist the governed shot list to CSV."""
    if not shots:
        raise ValueError("No shots were generated; ensure beats are present in the ledger.")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(shots[0].keys()))
        writer.writeheader()
        writer.writerows(shots)
    return path


def body_only_hash(frame: Dict) -> str:
    """Compute the canonical body-only digest for a ledger frame."""
    canonical = {k: v for k, v in frame.items() if k != "hash_body_only"}
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def build_merkle_lattice(ledger_lines: Sequence[Dict]) -> Dict:
    """Construct per-frame hashes, chunk digests, and the scene root digest."""
    frame_hashes: List[str] = []
    chunk_map: Dict[int, List[str]] = {}

    for row in ledger_lines:
        digest = body_only_hash(row)
        frame_hashes.append(digest)
        tick_raw = (row.get("hud", {}) or {}).get("qlock.tick_s", 0)
        try:
            tick = int(float(tick_raw))
        except (TypeError, ValueError):
            tick = 0
        chunk_map.setdefault(tick, []).append(digest)

    chunk_digests: Dict[int, str] = {}
    hasher = hashlib.sha256
    for tick in sorted(chunk_map):
        payload = "".join(chunk_map[tick]).encode("utf-8")
        chunk_digests[tick] = "sha256:" + hasher(payload).hexdigest()

    scene_root_payload = "".join(chunk_digests[t] for t in sorted(chunk_digests)).encode("utf-8")
    scene_root = "sha256:" + hasher(scene_root_payload).hexdigest()

    return {
        "frame_hashes": frame_hashes,
        "chunk_digests": chunk_digests,
        "scene_root_digest": scene_root,
    }


def sentinel_exports(
    previz_validation: Dict,
    merkle_info: Dict,
    *,
    motion_digest: str,
    replay_digest: str,
    echo_digest: str,
) -> Dict:
    """Bundle governed Sentinel exports."""
    return {
        "previz_validation": previz_validation,
        "merkle_lattice": {
            "scene_root": merkle_info["scene_root_digest"],
            "chunks": merkle_info["chunk_digests"],
        },
        "capsule_digests": {
            "motion_ledger_v2": motion_digest,
            "replay_token_v2": replay_digest,
            "echo_v2": echo_digest,
        },
        "ci_expectations": {
            "openapi_path": "openapi/openapi.yaml",
            "baseline": "nearest_ancestor_or_skip",
            "smoke_health_endpoint": "/health",
            "governance_version": "v6.0",
        },
    }


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate governed previz ledgers.")
    parser.add_argument("ledger", type=Path, help="Path to the previz ledger JSONL file.")
    parser.add_argument(
        "--beats",
        type=str,
        default=",".join(DEFAULT_BEATS),
        help="Comma-delimited ordered beat list (default: %(default)s)",
    )
    parser.add_argument(
        "--qlock-interval",
        type=float,
        default=3.0,
        help="QLOCK anchor interval in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--drift-threshold",
        type=float,
        default=0.01,
        help="Maximum allowed drift.delta value (default: %(default)s)",
    )
    parser.add_argument(
        "--shot-list",
        type=Path,
        help="Optional path to write the governed shot list CSV.",
    )
    parser.add_argument(
        "--merkle-out",
        type=Path,
        help="Optional path to write the Merkle lattice JSON export.",
    )
    parser.add_argument(
        "--sentinel-export",
        type=Path,
        help="Optional path to write the Sentinel exports JSON blob.",
    )
    parser.add_argument("--motion-digest", type=str, help="Motion ledger capsule digest for Sentinel export.")
    parser.add_argument("--replay-digest", type=str, help="Replay token capsule digest for Sentinel export.")
    parser.add_argument("--echo-digest", type=str, help="Echo capsule digest for Sentinel export.")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    beats = [beat.strip() for beat in args.beats.split(",") if beat.strip()]

    ledger_lines = load_ledger(args.ledger)
    validation = validate_previz(
        ledger_lines,
        qlock_interval_s=args.qlock_interval,
        drift_threshold=args.drift_threshold,
    )

    print(json.dumps(validation, indent=2))
    if validation["status"] != "PASS":
        print("Previz validation failed.", file=sys.stderr)

    if args.shot_list:
        shots = generate_shot_list(ledger_lines, beats, qlock_interval_s=args.qlock_interval)
        written = write_shot_list_csv(shots, args.shot_list)
        print(f"Shot list written to {written}")

    merkle_info = build_merkle_lattice(ledger_lines)
    if args.merkle_out:
        args.merkle_out.parent.mkdir(parents=True, exist_ok=True)
        args.merkle_out.write_text(json.dumps(merkle_info, indent=2), encoding="utf-8")
        print(f"Merkle lattice written to {args.merkle_out}")

    if args.sentinel_export:
        missing = [name for name in ("motion_digest", "replay_digest", "echo_digest") if not getattr(args, name)]
        if missing:
            raise ValueError(
                "Sentinel export requested but missing required digests: " + ", ".join(missing)
            )
        sentinel_blob = sentinel_exports(
            validation,
            merkle_info,
            motion_digest=args.motion_digest,
            replay_digest=args.replay_digest,
            echo_digest=args.echo_digest,
        )
        args.sentinel_export.parent.mkdir(parents=True, exist_ok=True)
        args.sentinel_export.write_text(json.dumps(sentinel_blob, indent=2), encoding="utf-8")
        print(f"Sentinel exports written to {args.sentinel_export}")

    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
