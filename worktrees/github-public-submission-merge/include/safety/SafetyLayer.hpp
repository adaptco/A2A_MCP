#pragma once

#include <vector>
#include <string>
#include <limits>
#include <cstdint>

namespace safety {

    /**
     * @brief Class of violation that occurred during clipping.
     * 
     * - None: Signal passed unchanged.
     * - SoftLimit: Signal exceeded warning threshold but was within hard limits (or hard limit not enforcing).
     * - HardLimit: Signal exceeded hard limit and was clamped.
     * - InvariantBreach: Fundamental safety invariant violated (e.g. NaN, impossible state).
     */
    enum class ViolationType {
        None,
        SoftLimit,
        HardLimit,
        InvariantBreach
    };

    /**
     * @brief Defines the operating bounds for a single dimension of action.
     */
    struct SafetyBounds {
        double lower_hard;
        double upper_hard;
        double lower_soft;
        double upper_soft;

        SafetyBounds()
            : lower_hard(-std::numeric_limits<double>::infinity()),
              upper_hard(std::numeric_limits<double>::infinity()),
              lower_soft(-std::numeric_limits<double>::infinity()),
              upper_soft(std::numeric_limits<double>::infinity()) {}
        
        SafetyBounds(double lh, double uh, double ls, double us)
            : lower_hard(lh), upper_hard(uh), lower_soft(ls), upper_soft(us) {}
    };

    /**
     * @brief Generic representation of a control signal/action.
     */
    struct Action {
        std::vector<double> values;
        // potentially add timestamp or other metadata
    };

    /**
     * @brief Context state required for safety checks (e.g. joint positions, velocities).
     */
    struct State {
        // Placeholder for state information needed to calculate dynamic limits
        std::vector<double> values;
    };

    /**
     * @brief Telemetry definitions for what happened during the clip cycle.
     */
    struct ClipStats {
        ViolationType violation;
        double original_value;
        double clipped_value;
        bool was_modified;
        std::string message; 
    };

    /**
     * @brief Result of the clip operation.
     */
    struct ClipResult {
        Action clamped_action;
        std::vector<ClipStats> stats;
        bool is_safe; // True if no InvariantBreach
    };

    /**
     * @brief The SafetyLayer acts as a hard envelope around the control signal.
     * It enforces strict torque/action limits to keep the system in the safe manifold.
     */
    class SafetyLayer {
    public:
        /**
         * @brief Clips the proposed action to lie within the safe manifold.
         * 
         * @invariant The returned action MUST strictly lie within [lower_hard, upper_hard].
         * @invariant If proposed action is InvariantBreach (e.g. NaN), the result effectively neutralizes the action (zeroes it) or clamps to nearest safe.
         * @invariant Clipping is deterministic and stateless within the scope of a single call (though limits may depend on State).
         * 
         * @param proposed The control action proposed by the policy/controller.
         * @param context The current system state, effectively determining the shape of the manifold at this instance.
         * @param bounds The static or dynamic bounds to apply.
         * @return ClipResult containing the safe action and telemetry.
         */
        static ClipResult clip(const Action& proposed, const State& context, const std::vector<SafetyBounds>& bounds);
    };

} // namespace safety
