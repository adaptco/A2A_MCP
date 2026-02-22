from __future__ import annotations

from dataclasses import dataclass
<<<<<<< HEAD
from typing import Callable

import numpy as np

from .drift_metrics import KSTestResult, ks_2samp_numpy
=======
from typing import Optional

import numpy as np

from .drift_metrics import ks_2samp_numpy, KSTestResult
>>>>>>> core-orchestrator/ci-migration-gh-actions-3099626751256413922


@dataclass(frozen=True)
class DriftGateResult:
    passed: bool
    threshold: float
    metric: str
    ks: KSTestResult
    reason: str


def gate_drift(
<<<<<<< HEAD
    baseline: np.ndarray | None,
    candidate: np.ndarray,
    *,
    baseline_loader: Callable[[], np.ndarray] | None = None,
    pvalue_threshold: float = 0.10,
    metric_name: str = "ks_2samp",
) -> DriftGateResult:
    """Run a deterministic KS-based drift gate.

    Callers can pass baseline explicitly or provide baseline_loader.
=======
    baseline: np.ndarray,
    candidate: np.ndarray,
    *,
    pvalue_threshold: float = 0.10,
    metric_name: str = "ks_2samp",
) -> DriftGateResult:
    """
    CI-style drift gate:
      - Compute KS two-sample test between baseline and candidate
      - PASS if pvalue > pvalue_threshold
      - FAIL otherwise

    Deterministic: no randomness, fixed inputs => fixed output.
>>>>>>> core-orchestrator/ci-migration-gh-actions-3099626751256413922
    """
    if not (0.0 < pvalue_threshold < 1.0):
        raise ValueError("pvalue_threshold must be between 0 and 1.")

<<<<<<< HEAD
    if baseline is None:
        if baseline_loader is None:
            raise ValueError("Provide baseline or baseline_loader.")
        baseline = baseline_loader()

    ks = ks_2samp_numpy(baseline, candidate)
    passed = ks.pvalue > pvalue_threshold

    reason = (
        f"PASS: pvalue {ks.pvalue:.6f} > threshold {pvalue_threshold:.6f}"
        if passed
        else f"FAIL: pvalue {ks.pvalue:.6f} <= threshold {pvalue_threshold:.6f}"
    )
=======
    ks = ks_2samp_numpy(baseline, candidate)
    passed = ks.pvalue > pvalue_threshold

    if passed:
        reason = f"PASS: pvalue {ks.pvalue:.6f} > threshold {pvalue_threshold:.6f}"
    else:
        reason = f"FAIL: pvalue {ks.pvalue:.6f} <= threshold {pvalue_threshold:.6f}"
>>>>>>> core-orchestrator/ci-migration-gh-actions-3099626751256413922

    return DriftGateResult(
        passed=passed,
        threshold=pvalue_threshold,
        metric=metric_name,
        ks=ks,
        reason=reason,
    )
