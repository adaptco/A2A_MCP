#pragma once

#include "TokenPixel.hpp"
#include <string>
#include <vector>

namespace qube {

class QubeRuntime {
public:
  QubeRuntime();
  ~QubeRuntime();

  // Initialize the runtime with a specific configuration/hash
  void Initialize(const std::string &configHash);

  // Feed a TokenPixel into the runtime (Deterministic Step)
  bool Execute(const TokenPixel &pixel);

  // Get the current state hash of the runtime
  std::string GetStateHash() const;

  // HUB Model: Dock data (patterns) into the kernel
  void DockPattern(const std::string &patternId,
                   const std::vector<uint8_t> &data);

  // Recursion: Generate synthetic structures from reorganized patterns
  struct SyntheticStructure {
    float x, y, w, h;
    std::string type;
  };
  std::vector<SyntheticStructure> ReorganizeAndSynthesize();

  // Shutdown and cleanup
  void Shutdown();

private:
  std::string currentStateHash_;
  bool isInitialized_;
  uint64_t operationsCount_;

  // Internal audit log
  std::vector<std::string> auditLog_;

  void UpdateHash(const TokenPixel &pixel);
};

} // namespace qube
