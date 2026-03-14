"""Utilities for emitting deterministic rehearsal scrollstream events.

This module stages a rehearsal loop that simulates the
Celine → Luma → Dot audit braid.  It provides a helper
function that writes canonicalised events to the
``scrollstream_ledger`` so they can be replayed in docs,
HUDs, and smoke tests.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LEDGER = BASE_DIR / "data" / "scrollstream" / "scrollstream_ledger.ndjson"


@dataclass
class ScrollstreamEvent:
    """Represents a single rehearsal emission."""

    timestamp: str
    capsule_id: str
    ledger: str
    stage: str
    agent: str
    output: str
    hud_feedback: str
    training_mode: bool
    emotional_payload: str
    sabrina_spark_test: str

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


DETERMINISTIC_EVENTS: List[ScrollstreamEvent] = [
    ScrollstreamEvent(
        timestamp="2025-02-17T17:00:00Z",
        capsule_id="capsule.rehearsal.scrollstream.v1",
        ledger="scrollstream_ledger",
        stage="audit.summary",
        agent="celine",
        output="Celine weaves the rehearsal summary into the scrollstream braid.",
        hud_feedback="shimmer",
        training_mode=True,
        emotional_payload="anticipation",
        sabrina_spark_test="pass",
    ),
    ScrollstreamEvent(
        timestamp="2025-02-17T17:00:05Z",
        capsule_id="capsule.rehearsal.scrollstream.v1",
        ledger="scrollstream_ledger",
        stage="audit.proof",
        agent="luma",
        output="Luma verifies the audit proof and anchors it for replay.",
        hud_feedback="glyph_pulse",
        training_mode=True,
        emotional_payload="focus",
        sabrina_spark_test="pass",
    ),
    ScrollstreamEvent(
        timestamp="2025-02-17T17:00:10Z",
        capsule_id="capsule.rehearsal.scrollstream.v1",
        ledger="scrollstream_ledger",
        stage="audit.execution",
        agent="dot",
        output="Dot executes the rehearsal playback and records the final state.",
        hud_feedback="trail_glow",
        training_mode=True,
        emotional_payload="confidence",
        sabrina_spark_test="pass",
    ),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def emit_rehearsal_scrollstream(
    ledger_path: Path | str = DEFAULT_LEDGER,
    *,
    deterministic: bool = True,
    events: Iterable[ScrollstreamEvent] | None = None,
) -> List[ScrollstreamEvent]:
    """Write a rehearsal cycle to the ledger.

    Parameters
    ----------
    ledger_path:
        Destination NDJSON file for the scrollstream ledger.
    deterministic:
        When ``True`` (default) the canonical rehearsal payloads are
        written verbatim.  When ``False`` the provided events (or the
        deterministic defaults) are rewritten with fresh timestamps so
        operators can capture ad-hoc practice runs without losing
        repeatability for CI.
    events:
        Optional iterable of :class:`ScrollstreamEvent` objects to write.
        When ``None`` the deterministic canon is used.
    """

    ledger_path = Path(ledger_path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    payloads = list(events or DETERMINISTIC_EVENTS)

    if not deterministic:
        rewritten: List[ScrollstreamEvent] = []
        for event in payloads:
            rewritten.append(
                ScrollstreamEvent(
                    timestamp=_now_iso(),
                    capsule_id=event.capsule_id,
                    ledger=event.ledger,
                    stage=event.stage,
                    agent=event.agent,
                    output=event.output,
                    hud_feedback=event.hud_feedback,
                    training_mode=event.training_mode,
                    emotional_payload=event.emotional_payload,
                    sabrina_spark_test=event.sabrina_spark_test,
                )
            )
        payloads = rewritten

    with ledger_path.open("w", encoding="utf-8") as handle:
        for event in payloads:
            handle.write(event.to_json_line())
            handle.write("\n")

    return payloads


if __name__ == "__main__":
    emitted = emit_rehearsal_scrollstream()
    print("Emitted rehearsal scrollstream events:")
    for item in emitted:
        print(f" - {item.stage} :: {item.agent} :: {item.timestamp}")
