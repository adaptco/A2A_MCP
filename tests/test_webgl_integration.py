"""Test Three.js WebGL frontend integration (Part D)."""

import sys
sys.path.insert(0, ".")

from frontend.three.scene_manager import SceneManager, ThreeJSObject, Vector3
from frontend.three.world_renderer import WorldRenderer
from frontend.three.avatar_renderer import AvatarRenderer
from frontend.three.game_engine import GameEngine, PlayerState
from specs.loader import get_loader


def test_scene_manager():
    """Test Three.js scene management."""
    print("\n=== Test 1: Scene Manager ===")
    
    scene = SceneManager(scene_id="test_scene")
    assert scene.scene_id == "test_scene"
    assert len(scene.objects) == 0
    assert len(scene.lights) == 2  # ambient + directional
    assert len(scene.cameras) == 1
    print("[OK] Scene manager created")
    
    # Add object
    obj = ThreeJSObject(
        id="obj1",
        name="Test Object",
        position=Vector3(x=10, y=20, z=30),
        rotation=Vector3(),
        scale=Vector3(x=1, y=1, z=1),
    )
    scene.add_object(obj)
    assert len(scene.objects) == 1
    print("[OK] Object added to scene")
    
    # Update position
    new_pos = Vector3(x=50, y=50, z=50)
    scene.update_object_position("obj1", new_pos)
    updated = scene.get_object("obj1")
    assert updated.position.x == 50
    print("[OK] Object position updated")
    
    # Export JSON
    json_str = scene.export_scene_json()
    assert "test_scene" in json_str
    assert "objects" in json_str
    print("[OK] Scene exported to JSON")


def test_world_renderer():
    """Test Base44 world rendering."""
    print("\n=== Test 2: World Renderer ===")
    
    renderer = WorldRenderer()
    assert len(renderer.zone_renderers) == 44
    print("[OK] World renderer created with 44 zones")
    
    # Test zone at position
    zone_id = renderer.get_zone_at_position(x=50, z=50, layer=0)
    assert zone_id is not None
    print(f"[OK] Zone at (50, 50, 0): {zone_id}")
    
    # Test speed limit
    speed = renderer.get_speed_limit_at_position(x=50, z=50, layer=0)
    assert 25 <= speed <= 70
    print(f"[OK] Speed limit at zone: {speed} mph")
    
    # Test scene export
    scene_dict = renderer.get_scene_dict()
    assert scene_dict["object_count"] == 44
    print(f"[OK] World scene exported with {scene_dict['object_count']} zones")


def test_avatar_renderer():
    """Test avatar rendering."""
    print("\n=== Test 3: Avatar Renderer ===")
    
    renderer = AvatarRenderer()
    assert len(renderer.avatar_panels) == 7
    print("[OK] Avatar renderer created with 7 panels")
    
    # Update avatar score
    first_avatar_id = list(renderer.avatar_panels.keys())[0]
    success = renderer.update_avatar_score(first_avatar_id, 0.85)
    assert success
    panel = renderer.avatar_panels[first_avatar_id]
    assert panel.judge_score == 0.85
    print(f"[OK] Avatar score updated to 0.85")
    
    # Get UI panels JSON
    ui_json = renderer.get_ui_panels_json()
    assert ui_json["count"] == 7
    print("[OK] Avatar UI panels exported to JSON")
    
    # Create avatar 3D representation
    avatar_obj = renderer.create_avatar_representation(first_avatar_id)
    assert avatar_obj is not None
    assert avatar_obj.id.startswith("avatar_")
    print("[OK] Avatar 3D representation created")


def test_game_engine():
    """Test game engine integration."""
    print("\n=== Test 4: Game Engine ===")
    
    engine = GameEngine(preset="simulation")
    assert engine.preset == "simulation"
    assert len(engine.player_states) == 0
    print("[OK] Game engine initialized")
    
    # Initialize player
    pos = Vector3(x=100, y=0, z=100)
    state = engine.initialize_player("TestAgent", position=pos)
    assert state.agent_name == "TestAgent"
    assert state.speed_mph == 0.0
    assert state.fuel_gal == 13.2
    print("[OK] Player initialized")
    
    # Update player state
    success = engine.update_player_state("TestAgent", speed_mph=50, rotation=0, fuel_gal=12.0)
    assert success
    state = engine.player_states["TestAgent"]
    assert state.speed_mph == 50
    assert state.fuel_gal == 12.0
    print("[OK] Player state updated")
    
    # Judge action
    result = engine.judge_action("TestAgent", "accelerate to 60 mph")
    assert "score" in result
    assert 0.0 <= result["score"] <= 1.0
    print(f"[OK] Action judged with score {result['score']:.3f}")
    
    # Get game state
    game_state = engine.get_game_state()
    assert game_state["frame"] == 0
    assert game_state["preset"] == "simulation"
    assert "TestAgent" in game_state["players"]
    print("[OK] Game state exported")
    
    # Run frame
    frame_state = engine.run_frame()
    assert frame_state["frame"] == 1
    print("[OK] Frame executed")


def test_integration():
    """Test full system integration."""
    print("\n=== Test 5: Full Integration ===")
    
    # Initialize all systems
    engine = GameEngine(preset="arcade")
    
    # Add multiple players
    engine.initialize_player("Agent1", Vector3(x=50, y=0, z=50))
    engine.initialize_player("Agent2", Vector3(x=200, y=50, z=200))
    engine.initialize_player("Agent3", Vector3(x=300, y=100, z=150))
    
    assert len(engine.player_states) == 3
    print("[OK] Multiple agents initialized")
    
    # Update all agents
    for i, agent_name in enumerate(["Agent1", "Agent2", "Agent3"]):
        engine.update_player_state(agent_name, 40 + i * 10, i * 45, 12.0)
    
    # Judge all actions
    for agent_name in ["Agent1", "Agent2", "Agent3"]:
        result = engine.judge_action(agent_name, "navigate to zone")
        assert "score" in result
    
    print("[OK] All agents judged")
    
    # Run several frames
    for _ in range(10):
        engine.run_frame()
    
    assert engine.frame_count == 10
    print("[OK] Frame loop executed")
    
    # Get final state
    state = engine.get_game_state()
    assert state["frame"] == 10
    assert len(state["players"]) == 3
    assert len(state["avatar_ui"]["panels"]) == 7
    print("[OK] Full game state verified")


def test_module_compilation():
    """Test all modules compile."""
    print("\n=== Test 6: Module Compilation ===")
    
    import py_compile
    
    modules = [
        "frontend/three/scene_manager.py",
        "frontend/three/world_renderer.py",
        "frontend/three/avatar_renderer.py",
        "frontend/three/game_engine.py",
        "frontend/three/__init__.py",
        "frontend/__init__.py",
    ]
    
    for module in modules:
        try:
            py_compile.compile(module, doraise=True)
        except Exception as e:
            print(f"[FAIL] {module}: {e}")
            sys.exit(1)
    
    print(f"[OK] All {len(modules)} modules compile")


if __name__ == "__main__":
    print("=" * 70)
    print("Three.js WebGL Frontend Integration Tests (Part D)")
    print("=" * 70)

    test_scene_manager()
    test_world_renderer()
    test_avatar_renderer()
    test_game_engine()
    test_integration()
    test_module_compilation()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED - Part D Complete")
    print("=" * 70)
