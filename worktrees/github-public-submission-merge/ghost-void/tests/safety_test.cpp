#include "../include/safety/SafetyLayer.hpp"
#include <cassert>
#include <cmath>
#include <iostream>
#include <vector>

using namespace safety;

void print_stats(const ClipStats &stat, int index) {
  std::cout << "Joint " << index << ": ";
  switch (stat.violation) {
  case ViolationType::None:
    std::cout << "OK";
    break;
  case ViolationType::SoftLimit:
    std::cout << "SOFT WARNING";
    break;
  case ViolationType::HardLimit:
    std::cout << "HARD CLAMP";
    break;
  case ViolationType::InvariantBreach:
    std::cout << "INVARIANT BREACH";
    break;
  }
  std::cout << " | Orig: " << stat.original_value
            << " | Clipped: " << stat.clipped_value
            << " | Msg: " << stat.message << std::endl;
}

int main() {
  std::cout << "Running SafetyLayer verification..." << std::endl;

  // Define bounds:
  // Joint 0: Hard [-10, 10], Soft [-5, 5]
  // Joint 1: Hard [-1, 1], Soft [-0.5, 0.5]
  std::vector<SafetyBounds> bounds;
  bounds.push_back(SafetyBounds(-10, 10, -5, 5));
  bounds.push_back(SafetyBounds(-1, 1, -0.5, 0.5));

  State context; // Unused for now

  // Test Case 1: All safe
  {
    std::cout << "\nTest 1: Normal Operation" << std::endl;
    Action act;
    act.values = {0.0, 0.0};
    auto res = SafetyLayer::clip(act, context, bounds);
    assert(res.is_safe);
    assert(res.clamped_action.values[0] == 0.0);
    assert(res.stats[0].violation == ViolationType::None);
    print_stats(res.stats[0], 0);
  }

  // Test Case 2: Soft Limit Violation
  {
    std::cout << "\nTest 2: Soft Limit Warning" << std::endl;
    Action act;
    act.values = {6.0, 0.0}; // 6.0 > 5.0 (soft) but < 10.0 (hard)
    auto res = SafetyLayer::clip(act, context, bounds);
    assert(res.is_safe);
    assert(res.clamped_action.values[0] == 6.0); // Should NOT be clamped
    assert(res.stats[0].violation == ViolationType::SoftLimit);
    print_stats(res.stats[0], 0);
  }

  // Test Case 3: Hard Limit Violation
  {
    std::cout << "\nTest 3: Hard Limit Clamping" << std::endl;
    Action act;
    act.values = {12.0, -2.0}; // 12 > 10, -2 < -1
    auto res = SafetyLayer::clip(act, context, bounds);
    assert(res.is_safe);
    assert(res.clamped_action.values[0] == 10.0); // Clamped to max
    assert(res.clamped_action.values[1] == -1.0); // Clamped to min
    assert(res.stats[0].violation == ViolationType::HardLimit);
    assert(res.stats[1].violation == ViolationType::HardLimit);
    print_stats(res.stats[0], 0);
    print_stats(res.stats[1], 1);
  }

  // Test Case 4: NaN Injection
  {
    std::cout << "\nTest 4: NaN Injection" << std::endl;
    Action act;
    act.values = {NAN, 0.0};
    auto res = SafetyLayer::clip(act, context, bounds);
    assert(!res.is_safe);
    assert(res.stats[0].violation == ViolationType::InvariantBreach);
    assert(res.clamped_action.values[0] == 0.0); // Fail-safe
    print_stats(res.stats[0], 0);
  }

  std::cout << "\nAll tests passed!" << std::endl;
  return 0;
}
