"""Game engine integrating Three.js rendering with WHAM physics and Judge."""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from frontend.three.scene_manager import SceneManager, Vector3
from frontend.three.world_renderer import WorldRenderer
from frontend.three.avatar_renderer import AvatarRenderer
from orchestrator.judge_orchestrator import get_judge_orchestrator
from schemas.game_model import AgentRuntimeState, GameActionResult, GameModel, ZoneSpec


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
        self.game_model = GameModel(preset=preset)

        # Game state
        self.player_states: Dict[str, PlayerState] = {}
        self.frame_count = 0
        self.running = False

        # Merge renderers into main scene
        self._merge_scenes()

    def _merge_scenes(self) -> None:
        """Merge world and avatar renderer objects into main scene."""
        self._sync_zones_into_game_model()

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
        if isinstance(avatars, dict):
            avatars = avatars.values()
        for avatar in avatars:
            avatar_obj = self.avatar_renderer.create_avatar_representation(
                avatar.profile.avatar_id
            )
            if avatar_obj:
                self.scene.add_object(avatar_obj)

    def _sync_zones_into_game_model(self) -> None:
        """Mirror world renderer zone specs into the typed game model."""
        for zone_id, renderer in self.world_renderer.zone_renderers.items():
            zone_data = renderer.zone_data
            self.game_model.register_zone(
                ZoneSpec(
                    zone_id=zone_id,
                    name=zone_data.get("name", zone_id),
                    layer=zone_data.get("layer", 0),
                    speed_limit_mph=zone_data.get("zone_speed_limit_mph", 55),
                    obstacle_density=self._normalize_obstacle_density(
                        zone_data.get("obstacle_density")
                    ),
                    difficulty_rating=zone_data.get("difficulty_rating", 1),
                    metadata={"grid_pos": zone_data.get("grid_pos")},
                )
            )

    @staticmethod
    def _normalize_obstacle_density(value: Any) -> float:
        """Normalize zone obstacle density from string or numeric values."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            mapping = {
                "none": 0.0,
                "low": 0.25,
                "medium": 0.5,
                "high": 0.75,
                "extreme": 1.0,
            }
            return mapping.get(value.strip().lower(), 0.0)
        return 0.0

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
        self.game_model.upsert_agent_state(
            AgentRuntimeState(
                agent_name=agent_name,
                x=position.x,
                y=position.y,
                z=position.z,
                speed_mph=state.speed_mph,
                heading_deg=state.rotation,
                fuel_gal=state.fuel_gal,
                current_zone=state.current_zone,
                active=state.active,
            )
        )
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
        self.game_model.upsert_agent_state(
            AgentRuntimeState(
                agent_name=state.agent_name,
                x=state.position.x,
                y=state.position.y,
                z=state.position.z,
                speed_mph=state.speed_mph,
                heading_deg=state.rotation,
                fuel_gal=state.fuel_gal,
                current_zone=state.current_zone,
                active=state.active,
            )
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
        result = GameActionResult(
            agent_name=agent_name,
            action=action,
            score=score.overall_score,
            zone=state.current_zone,
            speed_mph=state.speed_mph,
            fuel_gal=state.fuel_gal,
        )
        self.game_model.apply_action_result(result)

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
            "contract": self.game_model.model_dump(mode="json"),
        }

    def run_frame(self) -> Dict[str, Any]:
        """Execute one frame of game loop."""
        self.frame_count += 1
        self.game_model.snapshot(self.frame_count)
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
