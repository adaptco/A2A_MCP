"""Loss hooks for expert utilization and drift prevention."""

from typing import Dict, List


def compute_expert_utilization(routing: List[int], num_experts: int) -> Dict[int, float]:
    """Return utilization ratios for each expert index."""
    counts = {idx: 0 for idx in range(num_experts)}
    for expert_idx in routing:
        counts[expert_idx] = counts.get(expert_idx, 0) + 1
    total = float(len(routing)) or 1.0
    return {idx: count / total for idx, count in counts.items()}
