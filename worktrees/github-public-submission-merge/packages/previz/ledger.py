"""PreViz motion ledger capsule utilities and discovery."""
from __future__ import annotations
from datetime import datetime, timezone

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field, validator


class SubjectPose(BaseModel):
    """Pose vector for a subject (car/avatar) in a frame."""

    x: float
    y: float
    yaw: float


class CameraState(BaseModel):
    """Camera transform metadata for a frame."""

    pan: float
    tilt: float
    zoom: float


class MotionFrame(BaseModel):
    """One frame in the motion ledger."""

    frame: int
    cars: Dict[str, SubjectPose] = Field(default_factory=dict)
    camera: CameraState


class MotionLedger(BaseModel):
    """Full ledger for a scene."""

    capsule_id: str
    scene: str
    fps: int
    frames: List[MotionFrame]
    style_capsules: List[str] = Field(default_factory=list)

    @validator("frames")
    def ensure_sorted_frames(cls, value: List[MotionFrame]) -> List[MotionFrame]:
        return sorted(value, key=lambda frame: frame.frame)

    def duration_seconds(self) -> float:
        if not self.frames:
            return 0.0
        first_frame = self.frames[0].frame
        last_frame = self.frames[-1].frame
        if last_frame < first_frame:
            return 0.0
        return (last_frame - first_frame) / max(self.fps, 1)

    def track_for(self, car_id: str) -> List[SubjectPose]:
        return [frame.cars[car_id] for frame in self.frames if car_id in frame.cars]

    def summary(self) -> Dict[str, object]:
        return {
            "scene": self.scene,
            "fps": self.fps,
            "capsule_id": self.capsule_id,
            "style_capsules": self.style_capsules,
            "frames": len(self.frames),
            "duration_seconds": self.duration_seconds(),
        }


@dataclass
class LedgerSummary:
    scene: str
    path: Path
    metadata: Dict[str, object]


class PrevizLibrary:
    """Helper that discovers and caches ledger capsules from disk."""

    def __init__(self, root: Path):
        self._root = root
        self._cache: Dict[str, MotionLedger] = {}
        self._index: Dict[str, Path] = {}
        self._load_index()

    def _load_index(self) -> None:
        if not self._root.exists():
            return
        for path in sorted(self._root.glob("*.json")):
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            ledger = MotionLedger.parse_obj(payload)
            self._cache[ledger.scene] = ledger
            self._index[ledger.scene] = path

    def list_summaries(self) -> List[LedgerSummary]:
        summaries: List[LedgerSummary] = []
        for scene, path in self._index.items():
            summaries.append(
                LedgerSummary(scene=scene, path=path, metadata=self._cache[scene].summary())
            )
        return summaries

    def get_ledger(self, scene: str) -> MotionLedger:
        if scene not in self._cache:
            raise KeyError(f"scene '{scene}' not found in PreViz library")
        return self._cache[scene]


@lru_cache()
def load_library() -> PrevizLibrary:
    root = Path(__file__).resolve().parents[0] / "data"
    return PrevizLibrary(root)


LIBRARY = load_library()

__all__ = [
    "CameraState",
    "MotionFrame",
    "MotionLedger",
    "PrevizLibrary",
    "SubjectPose",
    "LIBRARY",
    "load_library",
]

class ScrollstreamRehearsalRequest(BaseModel):
    mode: str = "standard"
    include_hud: bool = False

class ScrollstreamRehearsalEvent(BaseModel):
    phase: str
    agent: str
    role: str
    output: str
    emotional_payload: str

def _deterministic_timestamp() -> str:
    return "2025-01-01T00:00:00Z"

def _iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _data_root() -> Path:
    return Path(__file__).resolve().parents[0] / "data"

_ledger_path = _data_root().parent / "ledger.jsonl"
