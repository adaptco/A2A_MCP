from dataclasses import dataclass
from .vec2 import Vec2
from .physics_config import PhysicsConfig, DEFAULT_PHYSICS

@dataclass
class WASDAgent:
    position: Vec2
    velocity: Vec2
    mass: float
    friction: float
    max_speed: float

    @classmethod
    def default(cls, config: PhysicsConfig = DEFAULT_PHYSICS) -> "WASDAgent":
        return cls(
            position=Vec2(0.0, 0.0),
            velocity=Vec2(0.0, 0.0),
            mass=config.base_mass,
            friction=config.base_friction,
            max_speed=config.max_speed,
        )

    def to_dict(self) -> dict:
        return {
            "position": self.position.to_dict(),
            "velocity": self.velocity.to_dict(),
            "mass": self.mass,
            "friction": self.friction,
            "max_speed": self.max_speed,
        }
