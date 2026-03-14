"""
Supra Drift Physics Model (Pacejka Magic Formula Simplified)
Maps steering/velocity to lateral slip and drift state.
"""

from dataclasses import dataclass
import math

@dataclass
class DriftState:
    is_drifting: bool
    drift_score: float  # 0.0 to 1.0 energy intensity
    slip_angle: float   # radians
    lateral_force: float
    mode: str           # "GRIP", "SLIP", "DRIFT"

class SupraDriftModel:
    def __init__(self, mass=1500.0, friction_coeff=1.2):
        self.mass = mass
        self.mu = friction_coeff
        self.g = 9.81
        
    def calculate_drift(self, velocity: float, steering_angle: float) -> DriftState:
        """
        Calculate drift dynamics based on current kinematics.
        
        Args:
            velocity: Forward speed in m/s
            steering_angle: Wheel angle in radians
            
        Returns:
            DriftState object
        """
        if velocity < 5.0:
            return DriftState(False, 0.0, 0.0, 0.0, "GRIP")
            
        # Simplified slip angle approximation
        # Adjusted to be less aggressive at lower speeds
        # slip_angle = steering - (0.5 * steering * (velocity / 40.0))
        slip_angle = steering_angle * (1.0 - (velocity / 60.0))
        
        # Pacejka Magic Formula simplified: F_lat = D * sin(C * atan(B * alpha))
        # B=8, C=1.5, D=mu*N (Tuned for stability)
        normal_force = self.mass * self.g
        peak_force = self.mu * normal_force
        
        stiffness = 8.0
        shape = 1.5
        
        lat_force = peak_force * math.sin(shape * math.atan(stiffness * slip_angle))
        
        # Determine drift threshold (break traction > 0.85 peak force)
        load_ratio = abs(lat_force) / peak_force
        is_drifting = load_ratio > 0.85
        
        drift_score = 0.0
        mode = "GRIP"
        
        if is_drifting:
            mode = "DRIFT"
            # Score based on angle and sustained velocity
            # Tuned for more aggressive scoring
            drift_score = min(1.0, (abs(slip_angle) * velocity) / 10.0)
        elif load_ratio > 0.6:
            mode = "SLIP"
            drift_score = load_ratio * 0.5
            
        return DriftState(
            is_drifting=is_drifting,
            drift_score=drift_score,
            slip_angle=slip_angle,
            lateral_force=lat_force,
            mode=mode
        )
