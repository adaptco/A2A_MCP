#pragma once

#include "Sandbox.hpp"
#include <memory>

namespace engine {

class Orchestrator {
public:
  Orchestrator();
  void Run();

private:
  std::unique_ptr<Sandbox> sandbox_;
  bool isRunning_;
};

} // namespace engine
