"""WHAM WebGL-capable game engine with decoupled physics."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import asyncio
import time


class EngineState(str, Enum):
    """Engine execution state."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    SHUTDOWN = "shutdown"


@dataclass
class EngineConfig:
    """Engine configuration."""
    target_fps: int = 60
    max_entities: int = 1000
    enable_physics: bool = True
    enable_audio: bool = True
    render_backend: str = "webgl"  # "webgl", "headless", "debug"
    debug_mode: bool = False


@dataclass
class Transform:
    """Entity position, rotation, scale."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rx: float = 0.0  # rotation x
    ry: float = 0.0  # rotation y
    rz: float = 0.0  # rotation z
    sx: float = 1.0  # scale
    sy: float = 1.0
    sz: float = 1.0


@dataclass
class Entity:
    """Game entity (player, NPC, object, etc.)."""
    entity_id: str
    entity_type: str  # "player", "npc", "vehicle", "prop"
    mesh_ref: Optional[str] = None  # Reference to 3D model
    transform: Transform = field(default_factory=Transform)
    velocity: tuple = field(default=(0.0, 0.0, 0.0))  # vx, vy, vz
    properties: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<Entity id={self.entity_id} type={self.entity_type} pos=({self.transform.x:.1f},{self.transform.y:.1f},{self.transform.z:.1f})>"


class WHAMEngine:
    """
    WHAM game engine with decoupled physics and render backend.
    Supports WebGL (browser) and headless execution.
    """

    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()
        self.state = EngineState.IDLE
        self._entities: Dict[str, Entity] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._frame_count = 0
        self._last_frame_time = 0.0
        self._loop_task: Optional[asyncio.Task] = None

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register a callback for an event type."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to all registered handlers."""
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(data)
            except Exception as e:
                if self.config.debug_mode:
                    print(f"Event handler error: {e}")

    def spawn_entity(self, entity: Entity) -> None:
        """Spawn an entity in the world."""
        if len(self._entities) >= self.config.max_entities:
            raise RuntimeError("Max entity limit reached")
        self._entities[entity.entity_id] = entity

        self.emit_event("entity_spawned", {
            "entity_id": entity.entity_id,
            "entity_type": entity.entity_type,
            "position": (entity.transform.x, entity.transform.y, entity.transform.z)
        })

    def despawn_entity(self, entity_id: str) -> bool:
        """Remove an entity from the world."""
        if entity_id in self._entities:
            del self._entities[entity_id]
            self.emit_event("entity_despawned", {"entity_id": entity_id})
            return True
        return False

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve an entity."""
        return self._entities.get(entity_id)

    def list_entities(self, entity_type: Optional[str] = None) -> List[Entity]:
        """List all entities, optionally filtered by type."""
        entities = list(self._entities.values())
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]
        return entities

    async def _game_loop(self) -> None:
        """Main game loop (runs at target FPS)."""
        frame_time = 1.0 / self.config.target_fps

        while self.state == EngineState.RUNNING:
            loop_start = time.perf_counter()

            # Update
            self._update_frame(frame_time)

            # Render (WebGL backend handles this separately)
            self._render_frame()

            # Frame timing
            elapsed = time.perf_counter() - loop_start
            if elapsed < frame_time:
                await asyncio.sleep(frame_time - elapsed)

            self._frame_count += 1

    def _update_frame(self, dt: float) -> None:
        """Physics and entity update step."""
        # Physics simulation (decoupled from render)
        if self.config.enable_physics:
            for entity in self._entities.values():
                # Simple Euler integration
                entity.transform.x += entity.velocity[0] * dt
                entity.transform.y += entity.velocity[1] * dt
                entity.transform.z += entity.velocity[2] * dt

        self.emit_event("frame_update", {
            "frame": self._frame_count,
            "dt": dt,
            "entity_count": len(self._entities)
        })

    def _render_frame(self) -> None:
        """Render step (WebGL sends to browser)."""
        # In WebGL mode, this serializes entity state for transmission to client
        # In headless mode, this is a no-op
        self.emit_event("frame_render", {
            "frame": self._frame_count,
            "entities": [
                {
                    "id": e.entity_id,
                    "mesh": e.mesh_ref,
                    "pos": (e.transform.x, e.transform.y, e.transform.z),
                    "rot": (e.transform.rx, e.transform.ry, e.transform.rz)
                }
                for e in self._entities.values()
            ]
        })

    async def run(self) -> None:
        """Start the engine."""
        if self.state != EngineState.IDLE:
            raise RuntimeError(f"Engine is {self.state.value}, cannot start")

        self.state = EngineState.RUNNING
        self.emit_event("engine_started", {"config": self.config})

        try:
            await self._game_loop()
        finally:
            self.state = EngineState.SHUTDOWN
            self.emit_event("engine_stopped", {"frame_count": self._frame_count})

    async def stop(self) -> None:
        """Stop the engine."""
        self.state = EngineState.SHUTDOWN

    def get_state(self) -> Dict[str, Any]:
        """Return engine state snapshot for serialization."""
        return {
            "state": self.state.value,
            "frame_count": self._frame_count,
            "entity_count": len(self._entities),
            "entities": [
                {
                    "id": e.entity_id,
                    "type": e.entity_type,
                    "pos": (e.transform.x, e.transform.y, e.transform.z),
                    "vel": e.velocity
                }
                for e in self._entities.values()
            ]
        }

    def __repr__(self) -> str:
        return f"<WHAMEngine state={self.state.value} fps={self.config.target_fps} entities={len(self._entities)}>"
