import pytest
from previz.ledger import MotionLedger, MotionFrame, SubjectPose, CameraState

def make_pose() -> SubjectPose:
    return SubjectPose(x=0.0, y=0.0, yaw=0.0)

def make_camera() -> CameraState:
    return CameraState(pan=0.0, tilt=0.0, zoom=1.0)

def test_ledger_frames_sorted_validator():
    """Verify that MotionLedger validators enforce sorted frames."""
    frames = [
        MotionFrame(frame=20, cars={"car": make_pose()}, camera=make_camera()),
        MotionFrame(frame=10, cars={"car": make_pose()}, camera=make_camera()),
    ]

    # When creating the ledger, the validator should sort the frames automatically
    ledger = MotionLedger(
        capsule_id="capsule",
        scene="scene",
        fps=30,
        frames=frames,
        style_capsules=[],
    )

    # Check if frames were sorted
    assert ledger.frames[0].frame == 10
    assert ledger.frames[1].frame == 20

def test_ledger_style_capsules_validator():
    """Verify that style_capsules defaults to list."""
    ledger = MotionLedger(
        capsule_id="capsule",
        scene="scene",
        fps=30,
        frames=[],
        # style_capsules omitted
    )
    assert isinstance(ledger.style_capsules, list)
    assert len(ledger.style_capsules) == 0
