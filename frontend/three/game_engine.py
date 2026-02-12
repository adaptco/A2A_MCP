"""Game engine integrating Three.js rendering with WHAM physics and Judge."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from frontend.three.scene_manager import SceneManager, Vector3
from frontend.three.world_renderer import WorldRenderer
from frontend.three.avatar_renderer import AvatarRenderer
from judge.decision import JudgmentModel
from orchestrator.judge_orchestrator import get_judge_orchestrator


@dataclass
class PlayerState:
    """Current player/agent state."""
    agent_name: str
    position: Vector3
    velocity: Vector3
    rotation: float  # Yaw in degrees
    speed_mph: float
    fuel_gal: float
    current_zone: Optional[str] = None
    active: bool = True


class GameEngine:
    """Main game engine combining rendering and physics."""

    def __init__(self, preset: str = "simulation"):
        self.preset = preset
        self.scene = SceneManager(scene_id="A2A_Game")
        self.world_renderer = WorldRenderer()
        self.avatar_renderer = AvatarRenderer()
        self.judge_orchestrator = get_judge_orchestrator(preset=preset)

        # Game state
        self.player_states: Dict[str, PlayerState] = {}
        self.frame_count = 0
        self.running = False

        # Merge renderers into main scene
        self._merge_scenes()

    def _merge_scenes(self) -> None:
        """Merge world and avatar renderer objects into main scene."""
        # Add world zones
        world_scene_dict = self.world_renderer.get_scene_dict()
        for obj_dict in world_scene_dict.get("objects", []):
            # Recreate object from dict
            try:
                obj = self.world_renderer.scene.get_object(obj_dict["id"])
                if obj:
                    self.scene.add_object(obj)
            except:
                pass

        # Add avatar representations
        avatars = self.avatar_renderer.registry.list_avatars()
        for avatar in avatars:
            avatar_obj = self.avatar_renderer.create_avatar_representation(
                avatar.profile.avatar_id
            )
            if avatar_obj:
                self.scene.add_object(avatar_obj)

    def initialize_player(
        self, agent_name: str, position: Optional[Vector3] = None
    ) -> PlayerState:
        """Initialize a player/agent."""
        if position is None:
            position = Vector3(x=50, y=0, z=50)

        state = PlayerState(
            agent_name=agent_name,
            position=position,
            velocity=Vector3(),
            rotation=0.0,
            speed_mph=0.0,
            fuel_gal=13.2,
        )

        self.player_states[agent_name] = state
        return state

    def update_player_state(
        self, agent_name: str, speed_mph: float, rotation: float, fuel_gal: float
    ) -> bool:
        """Update player state."""
        if agent_name not in self.player_states:
            return False

        state = self.player_states[agent_name]
        state.speed_mph = speed_mph
        state.rotation = rotation
        state.fuel_gal = fuel_gal

        # Update current zone
        state.current_zone = self.world_renderer.get_zone_at_position(
            state.position.x, state.position.z, int(state.position.y / 50)
        )

        return True

    def judge_action(
        self,
        agent_name: str,
        action: str,
    ) -> Dict[str, Any]:
        """Judge an agent action based on current state."""
        if agent_name not in self.player_states:
            return {"error": f"Agent {agent_name} not found"}

        state = self.player_states[agent_name]

        # Build context from player state
        context = {
            "speed_mph": state.speed_mph,
            "max_speed_mph": 155,
            "fuel_remaining_gal": state.fuel_gal,
            "nearest_obstacle_distance_m": 100,  # Placeholder
            "lateral_g_force": 0.3,
        }

        # Judge the action
        score = self.judge_orchestrator.judge_action(action, context, agent_name)

        # Update avatar renderer with score
        avatar = self.judge_orchestrator.get_avatar_for_agent(agent_name)
        if avatar:
            self.avatar_renderer.update_avatar_score(
                avatar.profile.avatar_id, score.overall_score
            )

        return {
            "agent_name": agent_name,
            "action": action,
            "score": score.overall_score,
            "zone": state.current_zone,
            "speed_mph": state.speed_mph,
            "fuel_gal": state.fuel_gal,
        }

    def get_game_state(self) -> Dict[str, Any]:
        """Get complete game state for rendering."""
        return {
            "frame": self.frame_count,
            "preset": self.preset,
            "running": self.running,
            "scene": self.scene.get_scene_dict(),
            "players": {
                name: {
                    "position": state.position.to_dict(),
                    "speed_mph": state.speed_mph,
                    "fuel_gal": state.fuel_gal,
                    "zone": state.current_zone,
                }
                for name, state in self.player_states.items()
            },
            "avatar_ui": self.avatar_renderer.get_ui_panels_json(),
        }

    def run_frame(self) -> Dict[str, Any]:
        """Execute one frame of game loop."""
        self.frame_count += 1
        return self.get_game_state()

    def start(self) -> None:
        """Start game engine."""
        self.running = True

    def stop(self) -> None:
        """Stop game engine."""
        self.running = False

    def __repr__(self) -> str:
        return (
            f"<GameEngine preset={self.preset} "
            f"players={len(self.player_states)} frame={self.frame_count}>"
        )
