"""Scrollstream-valid MoE transformer block placeholder."""

from typing import Callable, List


class TransformerBlock:
    """A minimal MoE block interface."""

    def __init__(self, experts: List[Callable[[float], float]]) -> None:
        self.experts = experts

    def forward(self, token_value: float, routing: List[int]) -> float:
        """Aggregate expert outputs based on the routing indices."""
        outputs = [self.experts[idx](token_value) for idx in routing]
        return sum(outputs) / max(len(outputs), 1)
