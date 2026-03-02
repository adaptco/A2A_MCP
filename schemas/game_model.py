"""Typed game model and cross-system integration contract."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OwnerSystem(str, Enum):
    """Source-of-truth system ownership."""

    CORE_ORCHESTRATOR = "core-orchestrator"
    SSOT = "SSOT"
    GROUND = "ground"


class OwnershipBoundary(BaseModel):
    """Declares who owns a contract domain and who can consume it."""

    domain: str
    owner: OwnerSystem
    consumers: List[OwnerSystem] = Field(default_factory=list)


class SpawnConfig(BaseModel):
    """Agent spawn position and defaults."""

    x: float
    y: float = 0.0
    z: float
    heading_deg: float = 0.0
    initial_fuel_gal: float = 13.2


class ZoneSpec(BaseModel):
    """Typed map-zone contract."""

    zone_id: str
    name: str
    layer: int = 0
    speed_limit_mph: int = 55
    obstacle_density: float = 0.0
    difficulty_rating: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentRuntimeState(BaseModel):
    """Canonical runtime state shared across game/orchestrator layers."""

    agent_name: str
    x: float
    y: float
    z: float
    speed_mph: float = 0.0
    heading_deg: float = 0.0
    fuel_gal: float = 13.2
    current_zone: Optional[str] = None
    last_action: Optional[str] = None
    last_judge_score: Optional[float] = None
    active: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GameActionResult(BaseModel):
    """Judge-evaluated action result contract."""

    agent_name: str
    action: str
    score: float
    zone: Optional[str] = None
    speed_mph: float
    fuel_gal: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GameTick(BaseModel):
    """Snapshot entry for deterministic replay and CI assertions."""

    frame: int
    states: Dict[str, AgentRuntimeState] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GameModel(BaseModel):
    """Single source of truth for game runtime + integration boundaries."""

    model_id: str = "a2a-game-model"
    preset: str = "simulation"
    zones: Dict[str, ZoneSpec] = Field(default_factory=dict)
    agent_states: Dict[str, AgentRuntimeState] = Field(default_factory=dict)
    history: List[GameTick] = Field(default_factory=list)
    ownership: List[OwnershipBoundary] = Field(
        default_factory=lambda: [
            OwnershipBoundary(
                domain="agent_runtime_state",
                owner=OwnerSystem.CORE_ORCHESTRATOR,
                consumers=[OwnerSystem.SSOT, OwnerSystem.GROUND],
            ),
            OwnershipBoundary(
                domain="world_specifications",
                owner=OwnerSystem.SSOT,
                consumers=[OwnerSystem.CORE_ORCHESTRATOR, OwnerSystem.GROUND],
            ),
            OwnershipBoundary(
                domain="physics_ground_truth",
                owner=OwnerSystem.GROUND,
                consumers=[OwnerSystem.CORE_ORCHESTRATOR, OwnerSystem.SSOT],
            ),
        ]
    )

    def register_zone(self, zone: ZoneSpec) -> None:
        self.zones[zone.zone_id] = zone

    def upsert_agent_state(self, state: AgentRuntimeState) -> None:
        self.agent_states[state.agent_name] = state

    def apply_action_result(self, result: GameActionResult) -> None:
        state = self.agent_states.get(result.agent_name)
        if state is None:
            state = AgentRuntimeState(
                agent_name=result.agent_name,
                x=0.0,
                y=0.0,
                z=0.0,
            )
        state.last_action = result.action
        state.last_judge_score = result.score
        state.current_zone = result.zone
        state.speed_mph = result.speed_mph
        state.fuel_gal = result.fuel_gal
        state.timestamp = result.timestamp
        self.agent_states[result.agent_name] = state

    def snapshot(self, frame: int) -> GameTick:
        snap = GameTick(
            frame=frame,
            states={
                name: AgentRuntimeState.model_validate(state.model_dump())
                for name, state in self.agent_states.items()
            },
        )
        self.history.append(snap)
        return snap
