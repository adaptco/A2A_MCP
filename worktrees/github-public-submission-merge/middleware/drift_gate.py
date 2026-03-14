"""
Drift Gate — Statistical deployment validation using the Kolmogorov-Smirnov test.
Ported from: sovereign-mcp/src/utils/drift_gate.py + revenue_policy.py
"""
from typing import List, Tuple
import numpy as np


# ------------------------------------------------------------------
# KS-Test drift detection
# ------------------------------------------------------------------

def gate_drift(
    baseline_embeddings: List[List[float]],
    new_embeddings: List[List[float]]
) -> Tuple[float, float]:
    """
    Perform a two-sample KS-test to detect distribution drift between
    baseline and new embeddings.

    Returns:
        (ks_statistic, p_value) — lower p-value means more drift.
    """
    try:
        from scipy import stats
        v1 = np.array(baseline_embeddings).flatten()
        v2 = np.array(new_embeddings).flatten()
        ks_stat, p_value = stats.ks_2samp(v1, v2)
        return float(ks_stat), float(p_value)
    except ImportError:
        # Fallback: simple mean-distance if scipy not available
        v1 = np.array(baseline_embeddings).flatten()
        v2 = np.array(new_embeddings).flatten()
        ks_stat = float(np.abs(np.mean(v1) - np.mean(v2)))
        p_value = 1.0 if ks_stat < 0.05 else 0.01
        return ks_stat, p_value


# ------------------------------------------------------------------
# Revenue / deployment policy
# ------------------------------------------------------------------

class RevenuePolicy:
    """
    Enforces deployment gates on statistical and financial grounds.
    """

    DRIFT_P_VALUE_THRESHOLD = 0.10  # Do not deploy if p < threshold

    @staticmethod
    def check_drift_gate(p_value: float) -> bool:
        """Returns True if safe to deploy (no significant drift detected)."""
        return p_value >= RevenuePolicy.DRIFT_P_VALUE_THRESHOLD

    @staticmethod
    def validate_transaction(transaction: dict) -> bool:
        """
        Validate a financial transaction for policy compliance.
        Rules: must have amount > 0 and a non-empty recipient.
        """
        if "amount" not in transaction or transaction["amount"] <= 0:
            return False
        if "recipient" not in transaction or not transaction["recipient"]:
            return False
        return True
