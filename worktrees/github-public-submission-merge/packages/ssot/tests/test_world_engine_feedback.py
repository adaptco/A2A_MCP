"""Tests for the contributor feedback loop pipeline."""

from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from previz.world_engine import WorldEngine


def build_engine_with_manifest() -> WorldEngine:
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
    engine.stage_preview_hud()
    engine.emit_summary_manifest()
    return engine


def test_stage_feedback_loop_default_window_open() -> None:
    engine = build_engine_with_manifest()

    capsule = engine.stage_feedback_loop()

    assert capsule.capsule_id == "capsule.selfie.dualroot.q.cici.v1.feedback.v1"
    assert capsule.data["window_status"] == "Open"
    assert capsule.data["ledger_freeze_job"]["status"] == "on_hold"


def test_stage_feedback_loop_with_freeze_schedule() -> None:
    engine = build_engine_with_manifest()

    capsule = engine.stage_feedback_loop(freeze_after_feedback=True)

    assert capsule.data["ledger_freeze_job"]["scheduled"] is True
    assert capsule.data["ledger_freeze_job"]["status"] == "queued"


def test_stage_adjudication_capsule_requires_feedback() -> None:
    engine = build_engine_with_manifest()

    with pytest.raises(ValueError) as excinfo:
        engine.stage_adjudication_capsule()

    assert "capsule.selfie.dualroot.q.cici.v1" in str(excinfo.value)


def test_stage_adjudication_capsule_defaults() -> None:
    engine = build_engine_with_manifest()
    engine.stage_feedback_loop()

    capsule = engine.stage_adjudication_capsule()

    assert capsule.capsule_id == "capsule.adjudication.merge_conflict.v1"
    assert capsule.data["status"] == "PENDING_ADJUDICATION"
    files = {item["file"] for item in capsule.data["conflicts"]}
    assert files == {"main.py", "previz/world_engine.py"}
    assert capsule.data["overlay_logic"]["status"] == "aligned"
