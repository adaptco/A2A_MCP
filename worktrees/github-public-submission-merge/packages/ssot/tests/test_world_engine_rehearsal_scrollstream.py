"""Tests for the rehearsal scrollstream capsule lifecycle."""

from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from previz.world_engine import WorldEngine


def build_engine_ready() -> WorldEngine:
    engine = WorldEngine()
    engine.load_capsules(
        [
            {"capsule_id": "lexicon.qube.v1"},
            {"capsule_id": "seed.core.v1"},
            {"capsule_id": "ledger.cadence.v1"},
            {"capsule_id": "lock.attestation.v1"},
        ]
    )
    engine.emit_lora_map()
    engine.rehearse_scene()
    engine.fork_scene()
    engine.render_final()
    engine.finalize_and_bind()
    return engine


def test_stage_rehearsal_scrollstream_requires_capsules() -> None:
    engine = WorldEngine()

    with pytest.raises(ValueError) as excinfo:
        engine.stage_rehearsal_scrollstream()

    assert "capsule.rehearsal.boo.v2" in str(excinfo.value)


def test_stage_rehearsal_scrollstream_emits_three_events() -> None:
    engine = build_engine_ready()

    capsule = engine.stage_rehearsal_scrollstream()

    assert capsule.capsule_id == "capsule.rehearsal.scrollstream.v1"
    ledger = capsule.data["scrollstream_ledger"]
    assert [entry["event"] for entry in ledger] == [
        "audit.summary",
        "audit.proof",
        "audit.execution",
    ]
    assert [entry["sequence"] for entry in ledger] == [1, 2, 3]
    assert capsule.data["hud_shimmer"]["status"] == "confirmed"
    assert capsule.data["replay_glyph"]["pulse_sequence"] == [0.33, 0.66, 0.99]
    # Ensure artifact export occurs for downstream chaining.
    assert "capsule.rehearsal.scrollstream.v1.json" in engine.artifacts
