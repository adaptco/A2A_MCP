#include "safety/SafetyLayer.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>


namespace safety {

ClipResult SafetyLayer::clip(const Action &proposed, const State &context,
                             const std::vector<SafetyBounds> &bounds) {
  ClipResult result;
  result.is_safe = true;

  // Basic dimension check
  if (proposed.values.size() != bounds.size()) {
    // If dimensions mismatch, we can't safely clip per joint.
    // This is a structural invariant breach.
    result.is_safe = false;
    // Neutralize everything
    result.clamped_action.values.resize(bounds.size(), 0.0);

    ClipStats stat;
    stat.violation = ViolationType::InvariantBreach;
    stat.message = "Dimension mismatch between action and bounds";
    stat.was_modified = true;
    result.stats.push_back(stat);
    return result;
  }

  result.clamped_action.values.resize(proposed.values.size());

  for (size_t i = 0; i < proposed.values.size(); ++i) {
    double val = proposed.values[i];
    const auto &bound = bounds[i];
    ClipStats stat;
    stat.original_value = val;
    stat.violation = ViolationType::None;
    stat.was_modified = false;

    // Check for NaN/Inf
    if (!std::isfinite(val)) {
      stat.violation = ViolationType::InvariantBreach;
      stat.message = "Non-finite value";
      stat.clipped_value = 0.0; // Fail-safe to zero
      stat.was_modified = true;
      result.is_safe = false;
    } else {
      // Hard limits
      if (val > bound.upper_hard) {
        stat.violation = ViolationType::HardLimit;
        stat.clipped_value = bound.upper_hard;
        stat.was_modified = true;
        stat.message = "Exceeded Upper Hard Limit";
      } else if (val < bound.lower_hard) {
        stat.violation = ViolationType::HardLimit;
        stat.clipped_value = bound.lower_hard;
        stat.was_modified = true;
        stat.message = "Exceeded Lower Hard Limit";
      } else {
        // Soft limits (only checked if hard limits passed)
        if (val > bound.upper_soft) {
          stat.violation = ViolationType::SoftLimit;
          stat.clipped_value = val; // Soft limit does not clamp, just warns
          stat.was_modified = false;
          stat.message = "Exceeded Upper Soft Limit";
        } else if (val < bound.lower_soft) {
          stat.violation = ViolationType::SoftLimit;
          stat.clipped_value = val;
          stat.was_modified = false;
          stat.message = "Exceeded Lower Soft Limit";
        } else {
          stat.clipped_value = val;
        }
      }
    }

    result.clamped_action.values[i] = stat.clipped_value;
    result.stats.push_back(stat);
  }

  return result;
}

} // namespace safety
