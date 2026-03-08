#include "engine/WorldModel.hpp"
#include "qube/QubeRuntime.hpp"
#include <cassert>
#include <iostream>
#include <vector>


void test_jurassic_pixels() {
  std::cout << "Starting Jurassic Pixels Unit Verification..." << std::endl;

  // 1. Home World Initialization
  engine::WorldModel world;
  world.LoadLevel(0); // HUB Level
  assert(world.GetCurrentLevel() == 0);
  assert(!world.GetTiles().empty());
  std::cout << " - Home World (Level 0) loaded successfully." << std::endl;

  // 2. Qube Runtime HUB Setup
  qube::QubeRuntime runtime;
  runtime.Initialize("JURASSIC_GENESIS_HUB");

  // 3. Data Docking (Soaking in Embeddings)
  // Simulating the intake of high-fidelity embeddings as "pattern clusters"
  std::vector<uint8_t> embedding_mock = {0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE};
  runtime.DockPattern("PATTERN_CLUST_SOAK_01", embedding_mock);

  std::string hash1 = runtime.GetStateHash();
  std::cout << " - Data Docked. Hub State Hash: " << hash1 << std::endl;

  // 4. Pattern Rehash & Synthesis
  // Reorganizing the clusters into "Synthetic Structures" for recursion
  auto structures = runtime.ReorganizeAndSynthesize();
  assert(!structures.empty());
  std::cout << " - Synthetic Structures synthesized: " << structures.size()
            << std::endl;

  // 5. Recursion Loop: Materialize structures back into the World Model
  for (const auto &s : structures) {
    std::cout << "   -> Component: " << s.type << " at [" << s.x << "," << s.y
              << "] Size: " << s.w << "x" << s.h << std::endl;
    world.SpawnPlane({s.x, s.y}, s.w, s.h);
  }

  // 6. Verify Stabilization
  // The world should now contain the synthetic structures
  assert(world.GetTiles().size() > 3); // Level 0 has 3 platforms initially

  std::cout << " - Recursion loop stabilized. Hub reorganizer verified."
            << std::endl;
  std::cout << "Jurassic Pixels Unit Verification: SUCCESS" << std::endl;
}

int main() {
  try {
    test_jurassic_pixels();
  } catch (const std::exception &e) {
    std::cerr << "Verification FAILED: " << e.what() << std::endl;
    return 1;
  }
  return 0;
}
