"""Physics engine (decoupled from rendering)."""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


@dataclass
class RigidBody:
    """Physics representation of an entity."""
    entity_id: str
    mass: float = 1.0
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    acceleration: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    use_gravity: bool = True
    is_kinematic: bool = False  # True = non-physics-driven (e.g., player input)


class PhysicsEngine:
    """
    Decoupled physics simulation.
    Can run at different frequency than render; for now, synchronized.
    """

    def __init__(self, gravity: float = -9.81):
        self.gravity = gravity
        self._bodies: Dict[str, RigidBody] = {}

    def add_body(self, body: RigidBody) -> None:
        """Register a physics body."""
        self._bodies[body.entity_id] = body

    def remove_body(self, entity_id: str) -> bool:
        """Unregister a physics body."""
        if entity_id in self._bodies:
            del self._bodies[entity_id]
            return True
        return False

    def set_velocity(self, entity_id: str, velocity: Tuple[float, float, float]) -> None:
        """Set velocity of a body."""
        if entity_id in self._bodies:
            self._bodies[entity_id].velocity = velocity

    def apply_force(self, entity_id: str, force: Tuple[float, float, float]) -> None:
        """Apply force to a body (updates acceleration)."""
        if entity_id not in self._bodies:
            return

        body = self._bodies[entity_id]
        if body.is_kinematic:
            return  # Kinematic bodies ignore forces

        # F = ma
        ax = force[0] / body.mass
        ay = force[1] / body.mass
        az = force[2] / body.mass

        # Apply gravity
        if body.use_gravity:
            az += self.gravity

        body.acceleration = (ax, ay, az)

    def step(self, dt: float) -> None:
        """Advance physics by dt seconds."""
        for body in self._bodies.values():
            if body.is_kinematic:
                continue

            # Euler integration: v += a * dt; x += v * dt
            vx, vy, vz = body.velocity
            ax, ay, az = body.acceleration

            body.velocity = (
                vx + ax * dt,
                vy + ay * dt,
                vz + az * dt
            )

    def __repr__(self) -> str:
        return f"<PhysicsEngine bodies={len(self._bodies)} gravity={self.gravity}>"
