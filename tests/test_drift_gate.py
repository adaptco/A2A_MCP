import numpy as np
import pytest

from drift_suite.gate import gate_drift

GOLDEN_BASELINE = np.array(
    [-2.0, -1.5, -1.2, -1.0, -0.8, -0.5, -0.3, -0.1, 0.0, 0.1, 0.3, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0]
)
GOLDEN_CURRENT = GOLDEN_BASELINE + 1.5
GOLDEN_PVALUE = 0.01004124869627724


def test_gate_passes_for_similar_distributions():
    baseline = np.linspace(0.0, 1.0, 200)
    candidate = baseline + 1e-6
    result = gate_drift(baseline, candidate, pvalue_threshold=0.10)
    assert result.passed, result.reason


def test_gate_fails_for_shifted_distributions():
    baseline = np.linspace(0.0, 1.0, 200)
    candidate = np.linspace(1.0, 2.0, 200)
    result = gate_drift(baseline, candidate, pvalue_threshold=0.10)
    assert not result.passed, "Expected drift gate to fail for shifted distributions."


def test_gate_rejects_empty_inputs():
    baseline = np.array([])
    candidate = np.array([1.0, 2.0, 3.0])

    with pytest.raises(ValueError, match="non-empty"):
        gate_drift(baseline, candidate)


def test_gate_uses_loader_when_baseline_missing():
    baseline = np.linspace(0.0, 1.0, 100)
    candidate = baseline + 1e-6

    def loader() -> np.ndarray:
        return baseline

    result = gate_drift(None, candidate, baseline_loader=loader)
    assert result.passed, result.reason


def test_golden_replay():
    """Ensures stable KS gate math for a fixed pair of arrays."""
    result = gate_drift(GOLDEN_BASELINE, GOLDEN_CURRENT, pvalue_threshold=0.10)
    assert not result.passed
    assert abs(result.ks.pvalue - GOLDEN_PVALUE) < 1e-12
