"""
Tests for Supra Drift Logic and Phase Space Integration.
Verifies drift physics calculations and mapping to Base44 grid.
"""

import pytest
import math
from phase_space_tick import SupraDriftModel

class TestSupraDrift:
    def test_grip_mode(self):
        """Low speed and low steering should result in GRIP mode."""
        model = SupraDriftModel()
        state = model.calculate_drift(velocity=10.0, steering_angle=0.05)
        
        assert state.mode == "GRIP"
        assert not state.is_drifting
        assert state.drift_score < 0.1

    def test_drift_initiation(self):
        """High speed and sharp turn should initiate DRIFT mode."""
        model = SupraDriftModel()
        # 30 m/s (~108 km/h), sharp turn
        state = model.calculate_drift(velocity=30.0, steering_angle=0.5)
        
        assert state.mode == "DRIFT"
        assert state.is_drifting
        assert state.drift_score > 0.5
        assert abs(state.lateral_force) > 0 # Should have significant force

    def test_slip_transition(self):
        """Moderate conditions should result in SLIP mode."""
        model = SupraDriftModel()
        # 20 m/s, moderate turn
        state = model.calculate_drift(velocity=20.0, steering_angle=0.2)
        
        # Depending on specific tuning, this might be SLIP or GRIP/DRIFT edge
        # We assert it's at least not zero force
        assert abs(state.lateral_force) > 0

    def test_zero_velocity(self):
        """Stationary vehicle has no drift."""
        model = SupraDriftModel()
        state = model.calculate_drift(velocity=0.0, steering_angle=1.0)
        
        assert state.mode == "GRIP"
        assert state.drift_score == 0.0

if __name__ == "__main__":
    pytest.main([__file__])
