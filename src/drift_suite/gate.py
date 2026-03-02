from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .drift_metrics import ks_2samp_numpy, KSTestResult


@dataclass(frozen=True)
class DriftGateResult:
    passed: bool
    threshold: float
    metric: str
    ks: KSTestResult
    reason: str


def gate_drift(
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
    """
    if not (0.0 < pvalue_threshold < 1.0):
        raise ValueError("pvalue_threshold must be between 0 and 1.")

    ks = ks_2samp_numpy(baseline, candidate)
    passed = ks.pvalue > pvalue_threshold

    if passed:
        reason = f"PASS: pvalue {ks.pvalue:.6f} > threshold {pvalue_threshold:.6f}"
    else:
        reason = f"FAIL: pvalue {ks.pvalue:.6f} <= threshold {pvalue_threshold:.6f}"

    return DriftGateResult(
        passed=passed,
        threshold=pvalue_threshold,
        metric=metric_name,
        ks=ks,
        reason=reason,
    )
