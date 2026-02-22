from .wasd_agent import WASDAgent
from .vec2 import Vec2
from .physics_config import DEFAULT_PHYSICS

INPUT_TO_ACCEL = {
    "W_pressed": Vec2(0.0, 1.0),
    "S_pressed": Vec2(0.0, -1.0),
    "A_pressed": Vec2(-1.0, 0.0),
    "D_pressed": Vec2(1.0, 0.0),
}

def tick(agent: WASDAgent, input_event: str, delta_time: float = 0.016):
    """
    One physics step. Pure function returning (new_agent, event_payload).
    """
    accel_dir = INPUT_TO_ACCEL.get(input_event, Vec2(0.0, 0.0))
    acceleration = DEFAULT_PHYSICS.acceleration / max(agent.mass, 1e-4)
    accel = accel_dir * acceleration

    # Semi-implicit Euler
    new_velocity = agent.velocity + accel * delta_time

    # Simple friction (proportional damping)
    new_velocity = new_velocity * (1.0 - agent.friction * delta_time)

    # Clamp velocity
    new_velocity = new_velocity.clamp(agent.max_speed)

    new_position = agent.position + new_velocity * delta_time

    new_agent = WASDAgent(
        position=new_position,
        velocity=new_velocity,
        mass=agent.mass,
        friction=agent.friction,
        max_speed=agent.max_speed,
    )

    event_payload = {
        "input": input_event,
        "delta_time": delta_time,
        "prev_state": agent.to_dict(),
        "new_state": new_agent.to_dict(),
    }

    return new_agent, event_payload
