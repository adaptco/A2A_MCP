import unittest
from unittest.mock import MagicMock, patch
import time
import math
from frontend.three.game_engine import GameEngine, PlayerState
from frontend.three.scene_manager import Vector3
from schemas.game_model import ZoneSpec

class TestGameEnginePhysics(unittest.TestCase):
    @patch('frontend.three.game_engine.SceneManager')
    @patch('frontend.three.game_engine.WorldRenderer')
    @patch('frontend.three.game_engine.AvatarRenderer')
    @patch('frontend.three.game_engine.get_judge_orchestrator')
    def test_physics_calculations(self, mock_judge_getter, mock_avatar_renderer, mock_world_renderer_cls, mock_scene_manager):
        # Setup mocks
        mock_judge = MagicMock()
        mock_judge_getter.return_value = mock_judge

        # Setup world renderer mock
        mock_world_renderer = mock_world_renderer_cls.return_value
        mock_world_renderer.get_scene_dict.return_value = {"objects": []}
        mock_world_renderer.zone_renderers = {}
        mock_world_renderer.get_zone_at_position.return_value = "test_zone" # Default zone

        # Instantiate engine
        engine = GameEngine()

        # Manually register a zone in the game model
        engine.game_model.register_zone(ZoneSpec(
            zone_id="test_zone",
            name="Test Zone",
            obstacle_density=0.5, # Medium density -> 50m distance
            zone_speed_limit_mph=60
        ))

        # Initialize player
        state = engine.initialize_player("agent1")
        state.current_zone = "test_zone"

        # --- TEST 1: Verify values are dynamic ---
        mock_judge.judge_action.return_value = MagicMock(overall_score=0.8)

        engine.judge_action("agent1", "move")
        call_args = mock_judge.judge_action.call_args
        context = call_args[0][1]

        # Verify initial values
        self.assertEqual(context['nearest_obstacle_distance_m'], 50.0) # 100 * (1 - 0.5)
        self.assertEqual(context['lateral_g_force'], 0.0)
        self.assertEqual(context['max_speed_mph'], 155.0)

        # --- TEST 2: Simulate Physics ---

        with patch('time.time') as mock_time:
            mock_time.return_value = 1000.0
            engine.update_player_state("agent1", speed_mph=60, rotation=0, fuel_gal=10)

            mock_time.return_value = 1001.0 # 1 second later
            engine.update_player_state("agent1", speed_mph=60, rotation=10, fuel_gal=9.9)

            engine.judge_action("agent1", "turn")
            call_args = mock_judge.judge_action.call_args
            context = call_args[0][1]

            # Speed = 60 mph = 26.8224 m/s
            # Omega = 10 deg/s = 0.174533 rad/s
            # a_lat = 26.8224 * 0.174533 = 4.6814 m/s^2
            # g_lat = 4.6814 / 9.81 = 0.4772 g

            expected_g = (60 * 0.44704) * math.radians(10) / 9.81
            self.assertAlmostEqual(context['lateral_g_force'], expected_g, places=4)
            self.assertEqual(context['nearest_obstacle_distance_m'], 50.0)

if __name__ == '__main__':
    unittest.main()
