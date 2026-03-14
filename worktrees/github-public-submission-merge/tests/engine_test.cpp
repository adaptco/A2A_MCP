#include "engine/Orchestrator.hpp"
#include "engine/Sandbox.hpp"
#include <cassert>
#include <iostream>

int main() {
  std::cout << "Running Engine Verification..." << std::endl;

  engine::Orchestrator orchestrator;
  // We can't easily inspect orchestrator internals without friend classes or
  // getters, but we can verify it runs without crashing.
  orchestrator.Run();

  std::cout << "Orchestrator run complete." << std::endl;

  // Test Physics / World directly
  engine::WorldModel world;
  world.LoadLevel(1);
  assert(world.GetCurrentLevel() == 1);
  
  // Verify Wily Castle (Level 1) specifics
  // We added 3 platform/spike items + 2 initial mocked items (Floor, Boss Room Wall) = 5 total?
  // Wait, LoadLevel clears tiles_ then adds mocked items:
  // 1. Floor {{-100, 10}, {1000, 20}}
  // 2. Boss Room Wall {{500, -100}, {520, 10}}
  // 3. Level 1 Floor
  // 4. Level 1 Spikes
  // 5. Level 1 Boss Gate
  // Total should be 5.
  assert(world.GetTiles().size() == 5);

  // Verify Spawn Point is not reset to {0,0}
  engine::Vector2 spawn = world.GetSpawnPoint();
  assert(spawn.x == -50 && spawn.y == 40);

  // Verify Collision with Spikes (should be solid now)
  // Spikes are at {{100, 48}, {200, 50}}
  assert(world.IsSolid({150, 49}) == true);
  
  // Verify Empty space is not solid
  assert(world.IsSolid({150, 40}) == false);

  std::cout << "Engine Verification Passed!" << std::endl;
  return 0;
}
