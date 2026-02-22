import math
from typing import Literal

# --- Controller for Temporal Flux Governance ---
class TemporalStabilizer:
    """
    Manages the 'Deviation_Metric' under 'Temporal_Flux' conditions.
    It enforces a 'Boundary_Limit' and performs an 'Integrity_Check'
    to maintain system stability. The mechanism uses 'Predictive_Adjustment'
    to address potential instability before it fully manifests.

    Attributes:
        MAX_DEVIATION_TOLERANCE (float): The maximum allowed deviation before triggering intervention.
        GOVERNANCE_PROTOCOL (str): Describes the type of governance logic being applied.
        StabilityStatus (Literal): Defines the possible states of the controller's operation.
        stable_reference_point (float): The baseline value representing a stable state.
        stability_status (StabilityStatus): The current operational status of the controller.
    """
    # Defines the immutable threshold for system integrity
    MAX_DEVIATION_TOLERANCE: float = 0.001

    # Specifies the type of governance protocol being applied
    GOVERNANCE_PROTOCOL: str = "PROTOCOL::PREDICTIVE_GOVERNANCE_CAP"

    # Status report enumeration indicating the state of the stability and flux tolerance
    StabilityStatus = Literal[
        "STABILIZER_INITIALIZED",        # Initial state upon creation
        "FLUX_TOLERATED::STABLE_GREEN",  # Deviation within acceptable limits
        "DEVIATION_VIOLATION::CAP_ARMED", # Deviation exceeds tolerance, intervention system armed
        "GOVERNANCE_TRUNCATED::CAP_ENFORCED" # Deviation truncated to the maximum allowed tolerance
    ]

    def __init__(self, stable_reference_point: float = 0.0):
        """
        Initializes the stabilizer with a stable reference point.
        Args:
            stable_reference_point: The baseline value representing a stable state, defaults to 0.0.
        """
        self.stable_reference_point: float = stable_reference_point
        self.stability_status: self.StabilityStatus = "STABILIZER_INITIALIZED" # Set initial status

    def _check_tolerance_boundary(self, deviation_value: float) -> bool:
        """
        Performs an integrity check against the maximum deviation tolerance.
        Compares the absolute value of the input 'deviation_value' against the
        immutable 'MAX_DEVIATION_TOLERANCE'.

        Args:
            deviation_value: The value to check against the tolerance.
        Returns:
            True if the absolute deviation is within the tolerance, False otherwise.
        """
        # Check if the absolute deviation exceeds the immutable tolerance
        if abs(deviation_value) > self.MAX_DEVIATION_TOLERANCE:
            self.stability_status = "DEVIATION_VIOLATION::CAP_ARMED" # Update status to indicate violation
            return False
        self.stability_status = "FLUX_TOLERATED::STABLE_GREEN" # Update status to indicate tolerance
        return True

    def calculate_predictive_adjustment(self, future_metric_projection: float) -> float:
        """
        Calculates the adjustment vector based on a future projection.
        This vector represents the adjustment needed to pull the 'future_metric_projection'
        back towards the 'stable_reference_point'.

        Args:
            future_metric_projection: The projected metric value at a future point in time.
        Returns:
            The calculated adjustment vector.
        """
        # Calculate the deviation of the future projection from the baseline
        deviation_from_future = future_metric_projection - self.stable_reference_point
        # Apply a damping factor (0.5) to the deviation to get the adjustment vector
        adjustment_vector = 0.5 * deviation_from_future
        return adjustment_vector

    def govern_deviation_metric(self, current_metric: float, future_metric_projection: float) -> float:
        """
        Applies the governance logic to the Deviation_Metric.
        This method integrates predictive adjustment and tolerance enforcement.

        Args:
            current_metric: The currently observed Deviation_Metric.
            future_metric_projection: The projected metric value at a future point in time.
        Returns:
            The governed (adjusted and capped) Deviation_Metric.
        """
        # Step 1: Calculate Predictive Adjustment
        adjustment_vector = self.calculate_predictive_adjustment(future_metric_projection)

        # Step 2: Apply Pre-Correction (Stabilizing the current metric)
        adjusted_metric = current_metric - adjustment_vector

        # Step 3: Enforce MAX_DEVIATION_TOLERANCE (Sovereign Cap)
        # Check if the adjusted metric violates the integrity check
        if not self._check_tolerance_boundary(adjusted_metric):
            # If the adjusted value still violates the tolerance, it is truncated
            # to the absolute MAX_DEVIATION_TOLERANCE to prevent failure.
            correction_sign = math.copysign(1, adjusted_metric) # Determine the sign
            governed_metric = correction_sign * self.MAX_DEVIATION_TOLERANCE # Truncate to max tolerance
            self.stability_status = "GOVERNANCE_TRUNCATED::CAP_ENFORCED" # Update status
        else:
            # If within tolerance, the adjusted metric is the final governed metric
            governed_metric = adjusted_metric

        return governed_metric

    def get_status(self) -> str:
        """
        Returns the current canonical status of the stabilizer.
        Returns:
            The current stability status as a string.
        """
        return self.stability_status
