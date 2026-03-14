"""Tests for the ledger module."""
from __future__ import annotations
from pathlib import Path
import sys
import subprocess

try:
    import pytest
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest"])
    import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from previz.ledger import CameraState, MotionFrame, MotionLedger, SubjectPose  # pylint: disable=wrong-import-position

def make_frame(frame_index: int) -> MotionFrame:
    """Create a test frame."""
    return MotionFrame(
        frame=frame_index,
        cars={"alpha": SubjectPose(x=1.0, y=2.0, yaw=3.0)},
        camera=CameraState(pan=0.0, tilt=0.0, zoom=1.0),
    )


def test_duration_seconds_handles_non_zero_start_frame() -> None:
    """Test duration logic."""
    ledger = MotionLedger(
        capsule_id="capsule",
        scene="scene",
        fps=30,
        frames=[make_frame(10), make_frame(40)],
        style_capsules=[],
    )
    assert ledger.duration_seconds() == pytest.approx((40 - 10) / 30)


def test_duration_seconds_empty_ledger_returns_zero() -> None:
    """Test duration logic for an empty ledger."""
    ledger = MotionLedger(
        capsule_id="capsule",
        scene="scene",
        fps=30,
        frames=[],
        style_capsules=[],
    )
    assert ledger.duration_seconds() == 0.0


def test_track_for_returns_only_requested_subject() -> None:
    """Test tracking for specific subject."""
    ledger = MotionLedger(
        capsule_id="capsule",
        scene="scene",
        fps=12,
        frames=[make_frame(1), make_frame(2)],
        style_capsules=[],
    )
    track = ledger.track_for("alpha")
    assert len(track) == 2


def test_ensure_sorted_frames() -> None:
    """Test that frames are sorted upon initialization."""
    frames = [make_frame(10), make_frame(5)]
    ledger = MotionLedger(
        capsule_id="capsule",
        scene="scene",
        fps=30,
        frames=frames,
        style_capsules=[],
    )
    assert ledger.frames[0].frame == 5
    assert ledger.frames[1].frame == 10


def test_track_for_returns_empty_list_if_subject_not_found() -> None:
    """Test tracking for a subject that does not exist."""
    ledger = MotionLedger(
        capsule_id="capsule",
        scene="scene",
        fps=12,
        frames=[make_frame(1), make_frame(2)],
        style_capsules=[],
    )
    track = ledger.track_for("beta")
    assert len(track) == 0


def test_summary_returns_correct_data() -> None:
    """Test the summary method."""
    ledger = MotionLedger(
        capsule_id="capsule",
        scene="scene",
        fps=30,
        frames=[make_frame(10), make_frame(40)],
        style_capsules=["style1"],
    )
    summary = ledger.summary()
    assert summary["scene"] == "scene"
    assert summary["fps"] == 30
    assert summary["capsule_id"] == "capsule"
    assert summary["style_capsules"] == ["style1"]
    assert summary["frames"] == 2
    assert summary["duration_seconds"] == pytest.approx((40 - 10) / 30)


def test_duration_seconds_single_frame() -> None:
    """Test duration logic for a single frame."""
    ledger = MotionLedger(
        capsule_id="capsule",
        scene="scene",
        fps=30,
        frames=[make_frame(10)],
        style_capsules=[],
    )
    assert ledger.duration_seconds() == 0.0
