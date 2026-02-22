from .wasd_agent import WASDAgent
from .physics_config import DEFAULT_PHYSICS

def from_prompt(description: str) -> WASDAgent:
    """
    Heuristic prompt → physics mapping.
    Later: replace with Gemma model that predicts config.
    """
    desc = description.lower()
    cfg = DEFAULT_PHYSICS

    mass = cfg.base_mass
    friction = cfg.base_friction
    max_speed = cfg.max_speed

    if "heavy" in desc or "tank" in desc:
        mass *= 2.5
        max_speed *= 0.6
    if "sluggish" in desc or "high inertia" in desc:
        friction *= 0.5
        max_speed *= 0.7
    if "nimble" in desc or "light" in desc:
        mass *= 0.7
        friction *= 1.2
        max_speed *= 1.4

    return WASDAgent(
        position=WASDAgent.default().position,
        velocity=WASDAgent.default().velocity,
        mass=mass,
        friction=friction,
        max_speed=max_speed,
    )
