from dataclasses import dataclass

@dataclass(frozen=True)
class PhysicsConfig:
    max_speed: float = 5.0
    base_mass: float = 1.0
    base_friction: float = 0.2
    acceleration: float = 20.0   # units/s^2

DEFAULT_PHYSICS = PhysicsConfig()
