from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass(frozen=True)
class KSTestResult:
    statistic: float
    pvalue: float
    n1: int
    n2: int


def ks_statistic(x: np.ndarray, y: np.ndarray) -> float:
    """
    Two-sample Kolmogorov–Smirnov statistic D = sup |F1 - F2|
    Deterministic, NumPy-only.

    Requirements:
      - x, y are 1D arrays of finite floats
    """
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()

    if x.size == 0 or y.size == 0:
        raise ValueError("KS test requires non-empty samples.")

    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("KS test requires all-finite samples.")

    x_sorted = np.sort(x)
    y_sorted = np.sort(y)

    # Evaluate ECDF differences at all unique points in combined sample.
    data_all = np.sort(np.concatenate([x_sorted, y_sorted]))

    # For each value v, count how many x <= v and y <= v.
    cdf_x = np.searchsorted(x_sorted, data_all, side="right") / x_sorted.size
    cdf_y = np.searchsorted(y_sorted, data_all, side="right") / y_sorted.size

    d = np.max(np.abs(cdf_x - cdf_y))
    return float(d)


def ks_pvalue_asymptotic(d: float, n1: int, n2: int) -> float:
    """
    Asymptotic two-sample KS p-value approximation.

    This approximation is commonly used:
      en = sqrt(n1*n2/(n1+n2))
      p ~= Q_KS((en + 0.12 + 0.11/en) * d)
      Q_KS(lambda) = 2 * sum_{j=1..inf} (-1)^{j-1} exp(-2 j^2 lambda^2)

    We truncate the series safely.
    """
    if not (0.0 <= d <= 1.0):
        raise ValueError("KS statistic d must be in [0,1].")
    if n1 <= 0 or n2 <= 0:
        raise ValueError("Sample sizes must be positive.")

    en = math.sqrt(n1 * n2 / (n1 + n2))
    if en == 0:
        return 1.0

    lam = (en + 0.12 + 0.11 / en) * d
    if lam <= 0:
        return 1.0

    # Compute Q_KS(lam) via alternating series
    # Stop when term is tiny or after a cap.
    s = 0.0
    for j in range(1, 200):
        term = (-1.0) ** (j - 1) * math.exp(-2.0 * (j * j) * (lam * lam))
        s += term
        if abs(term) < 1e-12:
            break

    p = max(0.0, min(1.0, 2.0 * s))
    return p


def ks_2samp_numpy(x: np.ndarray, y: np.ndarray) -> KSTestResult:
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    d = ks_statistic(x, y)
    p = ks_pvalue_asymptotic(d, x.size, y.size)
    return KSTestResult(statistic=d, pvalue=p, n1=int(x.size), n2=int(y.size))
