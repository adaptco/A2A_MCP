import numpy as np

from drift_suite.gate import gate_drift


def test_gate_passes_for_similar_distributions():
    baseline = np.linspace(0.0, 1.0, 200)
    candidate = baseline + 1e-6  # tiny shift
    result = gate_drift(baseline, candidate, pvalue_threshold=0.10)
    assert result.passed, result.reason


def test_gate_fails_for_shifted_distributions():
    baseline = np.linspace(0.0, 1.0, 200)
    candidate = np.linspace(1.0, 2.0, 200)  # clearly shifted
    result = gate_drift(baseline, candidate, pvalue_threshold=0.10)
    assert not result.passed, "Expected drift gate to fail for shifted distributions."


def test_gate_rejects_empty_inputs():
    baseline = np.array([])
    candidate = np.array([1.0, 2.0, 3.0])
    try:
        gate_drift(baseline, candidate)
        assert False, "Expected ValueError for empty baseline"
    except ValueError:
        pass


def test_gate_uses_loader_when_baseline_missing():
    baseline = np.linspace(0.0, 1.0, 100)
    candidate = baseline + 1e-6

    def loader() -> np.ndarray:
        return baseline

    result = gate_drift(None, candidate, baseline_loader=loader)
    assert result.passed, result.reason
