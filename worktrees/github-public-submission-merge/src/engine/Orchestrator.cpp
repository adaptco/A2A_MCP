#include "engine/Orchestrator.hpp"
#include <iostream>
#include <string>

namespace engine {

Orchestrator::Orchestrator()
    : sandbox_(std::make_unique<Sandbox>()), isRunning_(false) {}

void Orchestrator::Run() {
  // Initialize Sandbox
  sandbox_->Initialize();
  isRunning_ = true;

  // Command Loop
  // Expected to run as a subprocess where stdin provides commands
  std::string line;
  while (isRunning_ && std::getline(std::cin, line)) {
    // Simple 'Tick' protocol:
    // Any input results in one simulation step.
    // Check for Genesis Command
    if (line.find("genesis_plane") != std::string::npos) {
      // Hardcoded parsing for the specific structure sent by grounding.js
      // origin: { x: 0, y: 500 }, dimensions: { w: 1000, h: 50 }

      // Pass through to Sandbox -> WorldModel
      // We need a way to access WorldModel.
      // Sandbox::GetWorld is const. We need a non-const method or direct
      // access. For scaffolding, let's cast or add a method. Better: Add
      // sandbox_->SpawnPlane(...)

      sandbox_->TriggerGenesis();

      // Do not tick physics on configuration commands? Or do?
      // Let's continue to tick to stay alive.
    }

    float dt = 0.016f; // Fixed time step 60fps
    sandbox_->Update(dt);

    // Output State
    // For now, we output a simple confirmation/state JSON
    // A real implementation would serialize the World/Avatar state
    std::cout << "{\"type\": \"state_update\", \"frame_processed\": true}"
              << std::endl;
  }
}

} // namespace engine
