#!/usr/bin/env python3
"""Emit the capsule.rehearsal.scrollstream.v1 cycle and ledger artifacts.

This utility simulates the rehearsal emission cycle so contributors can replay
and audit the deterministic transcript before the capsule is sealed. It writes
append-only ledger entries plus auxiliary HUD shimmer and replay glyph
artifacts that front-end clients can reference.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional

CAPSULE_ID = "capsule.rehearsal.scrollstream.v1"
REPLAY_TOKEN_DEFAULT = "HUD.loop.selfie.dualroot.q.cici.v1.token.002"
SPARK_TEST_NAME = "Sabrina Spark Test"


@dataclass(frozen=True)
class Participant:
    name: str
    state: str
    role: Optional[str] = None

    def as_dict(self) -> dict:
        payload = {"name": self.name, "state": self.state}
        if self.role:
            payload["role"] = self.role
        return payload


@dataclass(frozen=True)
class Agent:
    call_sign: str
    role: str
    channel: str


@dataclass(frozen=True)
class CycleEvent:
    event: str
    agent: Agent
    output: str
    emotional_tone: str
    visual_asset: Optional[dict] = None


@dataclass(frozen=True)
class TemplateConfig:
    events: List[CycleEvent]
    participants: List[Participant]
    hud_shimmer: Optional[dict]
    replay_glyph: Optional[dict]
    training_mode: Optional[dict]
    spark_test_name: str
    replay_token: Optional[str]


@dataclass(frozen=True)
class TemplateOverrides:
    events: Optional[List[CycleEvent]] = None
    participants: Optional[List[Participant]] = None
    hud_shimmer: Optional[dict] = None
    replay_glyph: Optional[dict] = None
    training_mode: Optional[dict] = None
    spark_test_name: Optional[str] = None
    replay_token: Optional[str] = None


DEFAULT_PARTICIPANTS: List[Participant] = [
    Participant(name="CiCi", role="Conductor", state="overlay_active"),
    Participant(name="Q", role="Observer", state="trace_live"),
    Participant(name="Council Quorum", role="Validator", state="watching"),
]


CYCLE_TEMPLATE: List[CycleEvent] = [
    CycleEvent(
        event="audit.summary",
        agent=Agent(call_sign="Celine", role="Architect", channel="audit"),
        output=(
            "Celine threads the dual-root scaffold, confirming shimmer alignment, "
            "scene balance, and contributor posture before the ledger opens."
        ),
        emotional_tone="assured",
    ),
    CycleEvent(
        event="audit.proof",
        agent=Agent(call_sign="Luma", role="Sentinel", channel="observability"),
        output=(
            "Luma validates trail integrity and delta overlays, confirming no drift "
            "between root braids while shimmer breach monitors stay dormant."
        ),
        emotional_tone="focused",
    ),
    CycleEvent(
        event="audit.execution",
        agent=Agent(call_sign="Dot", role="Guardian", channel="execution"),
        output=(
            "Dot replays the capsule, pulses the glyph rail, and stamps the "
            "execution braid so contributors witness the full lifecycle in one click."
        ),
        emotional_tone="galvanized",
    ),
]


DEFAULT_TEMPLATE = TemplateConfig(
    events=CYCLE_TEMPLATE,
    participants=DEFAULT_PARTICIPANTS,
    hud_shimmer=None,
    replay_glyph=None,
    training_mode=None,
    spark_test_name=SPARK_TEST_NAME,
    replay_token=REPLAY_TOKEN_DEFAULT,
)


def parse_base_timestamp(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "--base-timestamp must be in ISO format YYYY-MM-DDTHH:MM:SSZ"
        ) from exc


def isoformat(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cycle_events(
    base_ts: datetime,
    replay_token: str,
    events: List[CycleEvent],
    spark_test_name: str,
) -> Iterable[dict]:
    offset = timedelta(seconds=4)
    current = base_ts
    for index, template in enumerate(events, start=1):
        event_ts = current
        current = current + offset
        payload = {
            "t": isoformat(event_ts),
            "sequence": index,
            "capsule": CAPSULE_ID,
            "event": template.event,
            "agent": template.agent.call_sign,
            "role": template.agent.role,
            "channel": template.agent.channel,
            "output": template.output,
            "emotional_tone": template.emotional_tone,
            "replay_token": replay_token,
            "spark_test": {
                "name": spark_test_name,
                "status": "pass",
                "overlay_grade": 0.97,
            },
            "hooks": [
                "capsule.comment.trace.v1",
                "shimmer.breach.monitor.v1",
                "refusal.flare.script.v1",
                "delta.overlay.audit.v1",
            ],
        }
        if template.visual_asset:
            payload["visual_asset"] = template.visual_asset
        yield payload


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_ledger(path: Path, events: Iterable[dict]) -> List[dict]:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_events = list(events)
    with path.open("a", encoding="utf-8") as ledger:
        for item in existing_events:
            ledger.write(json.dumps(item, sort_keys=True) + "\n")
    return existing_events


def build_visuals(
    events: List[dict],
    hud_override: Optional[dict] = None,
    glyph_override: Optional[dict] = None,
) -> dict:
    hud_payload = {
        "status": "emitted",
        "intensity": 0.82,
        "tone": "aurora",
        "timestamp": events[-1]["t"],
        "confirmation": "HUD shimmer confirms rehearsal emission",
    }
    if hud_override:
        hud_payload = {**hud_payload, **hud_override}
        hud_payload.setdefault("timestamp", events[-1]["t"])

    glyph_payload = {
        "state": "pulsing",
        "rail": "scrollstream",
        "sequence": [
            {
                "step": event["sequence"],
                "event": event["event"],
                "agent": event["agent"],
                "ts": event["t"],
                "spark_status": event["spark_test"]["status"],
                **({"visual_asset": event["visual_asset"]} if "visual_asset" in event else {}),
            }
            for event in events
        ],
    }
    if glyph_override:
        glyph_payload = {**glyph_payload, **glyph_override}
        glyph_payload.setdefault("rail", "scrollstream")
        glyph_payload.setdefault("state", "pulsing")

    return {
        "capsule": CAPSULE_ID,
        "hud_shimmer": hud_payload,
        "replay_glyph": glyph_payload,
    }


def build_capsule_snapshot(
    events: List[dict],
    replay_token: str,
    base_ts: datetime,
    participants: List[Participant],
    training_mode_override: Optional[dict],
    spark_test_name: str,
) -> dict:
    training_mode = {
        "deterministic": True,
        "spark_test": spark_test_name,
        "emotional_payload": "scene-aware",
    }
    if training_mode_override:
        training_mode.update(training_mode_override)

    return {
        "capsule_id": CAPSULE_ID,
        "status": "STAGED",
        "replay_token": replay_token,
        "participants": [participant.as_dict() for participant in participants],
        "window": {"status": "open", "base_timestamp": isoformat(base_ts)},
        "cycle": events,
        "training_mode": training_mode,
    }


def load_template(path: Path) -> TemplateOverrides:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Template {path} does not exist") from exc
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Template {path} contains invalid JSON: {exc}") from exc

    def load_participants(raw: List[dict]) -> List[Participant]:
        participants: List[Participant] = []
        for entry in raw:
            if "name" not in entry or "state" not in entry:
                raise ValueError(
                    "Template participants must include 'name' and 'state' fields"
                )
            participants.append(
                Participant(
                    name=entry["name"],
                    state=entry["state"],
                    role=entry.get("role"),
                )
            )
        return participants

    def load_events(raw: List[dict]) -> List[CycleEvent]:
        events: List[CycleEvent] = []
        for entry in raw:
            if "event" not in entry or "agent" not in entry or "output" not in entry:
                raise ValueError(
                    "Template events must provide 'event', 'agent', and 'output' fields"
                )
            agent_raw = entry["agent"]
            for key in ("call_sign", "role", "channel"):
                if key not in agent_raw:
                    raise ValueError(
                        f"Template event agent is missing required field '{key}'"
                    )
            events.append(
                CycleEvent(
                    event=entry["event"],
                    agent=Agent(
                        call_sign=agent_raw["call_sign"],
                        role=agent_raw["role"],
                        channel=agent_raw["channel"],
                    ),
                    output=entry["output"],
                    emotional_tone=entry.get("emotional_tone", "balanced"),
                    visual_asset=entry.get("visual_asset"),
                )
            )
        return events

    participants = None
    events = None
    hud_shimmer = None
    replay_glyph = None
    training_mode = None
    spark_test_name = None
    replay_token = None

    if "participants" in data:
        participants_raw = data["participants"]
        if not isinstance(participants_raw, list) or not participants_raw:
            raise ValueError("Template participants must be a non-empty list")
        participants = load_participants(participants_raw)

    if "events" in data:
        events_raw = data["events"]
        if not isinstance(events_raw, list) or not events_raw:
            raise ValueError("Template events must be a non-empty list")
        events = load_events(events_raw)

    if "hud_shimmer" in data:
        hud_shimmer = data["hud_shimmer"]

    if "replay_glyph" in data:
        replay_glyph = data["replay_glyph"]

    if "training_mode" in data:
        training_mode = data["training_mode"]

    if "spark_test_name" in data:
        spark_test_name = data["spark_test_name"]

    if "replay_token" in data:
        replay_token = data["replay_token"]

    return TemplateOverrides(
        events=events,
        participants=participants,
        hud_shimmer=hud_shimmer,
        replay_glyph=replay_glyph,
        training_mode=training_mode,
        spark_test_name=spark_test_name,
        replay_token=replay_token,
    )


def apply_overrides(base: TemplateConfig, overrides: TemplateOverrides) -> TemplateConfig:
    return TemplateConfig(
        events=overrides.events or base.events,
        participants=overrides.participants or base.participants,
        hud_shimmer=overrides.hud_shimmer or base.hud_shimmer,
        replay_glyph=overrides.replay_glyph or base.replay_glyph,
        training_mode=overrides.training_mode or base.training_mode,
        spark_test_name=overrides.spark_test_name or base.spark_test_name,
        replay_token=overrides.replay_token or base.replay_token,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the rehearsal scrollstream capsule ledger entries and artifacts."
    )
    parser.add_argument(
        "--out-dir",
        default=".out/rehearsal",
        help="Directory where ledger and artifact files are written (default: .out/rehearsal)",
    )
    parser.add_argument(
        "--base-timestamp",
        default="2025-10-05T18:00:00Z",
        type=parse_base_timestamp,
        help="ISO8601 UTC timestamp used for the first cycle event.",
    )
    parser.add_argument(
        "--replay-token",
        help="Replay token embedded in ledger events (defaults to template or capsule spec).",
    )
    parser.add_argument(
        "--template",
        type=Path,
        help="Optional JSON template describing participants, events, and visuals.",
    )
    args = parser.parse_args()

    template = DEFAULT_TEMPLATE
    if args.template:
        overrides = load_template(args.template)
        template = apply_overrides(template, overrides)

    replay_token = (
        args.replay_token
        or template.replay_token
        or REPLAY_TOKEN_DEFAULT
    )

    out_dir = Path(args.out_dir)
    ledger_path = out_dir / "scrollstream_ledger.jsonl"

    events = list(
        cycle_events(
            args.base_timestamp,
            replay_token,
            template.events,
            template.spark_test_name,
        )
    )
    appended = append_ledger(ledger_path, events)

    write_json(
        out_dir / "capsule.rehearsal.scrollstream.v1.cycle.json",
        build_capsule_snapshot(
            appended,
            replay_token,
            args.base_timestamp,
            template.participants,
            template.training_mode,
            template.spark_test_name,
        ),
    )
    write_json(
        out_dir / "capsule.rehearsal.scrollstream.v1.visuals.json",
        build_visuals(
            appended,
            hud_override=template.hud_shimmer,
            glyph_override=template.replay_glyph,
        ),
    )

    print(f"ledger_appended={ledger_path}")
    print(f"events_written={len(appended)}")
    print(f"replay_token={replay_token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
