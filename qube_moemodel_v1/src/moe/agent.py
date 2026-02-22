"""MoE Agent implementation using TransformerBlock."""
from typing import Callable, List, Dict, Any
from .transformer_block import TransformerBlock

class MoEAgent:
    """
    An agent that uses a Mixture-of-Experts (MoE) TransformerBlock to process tasks.
    It manages a set of experts and routes inputs to them.
    """
    def __init__(self, experts: List[Callable[[float], float]], expert_names: List[str] = None):
        """
        Initialize the MoE Agent.

        Args:
            experts: A list of callable expert functions.
            expert_names: Optional names for the experts for logging/debugging.
        """
        if not experts:
            raise ValueError("At least one expert is required.")

        self.block = TransformerBlock(experts)
        self.expert_names = expert_names or [f"Expert_{i}" for i in range(len(experts))]

        if len(self.expert_names) != len(experts):
             raise ValueError("Number of expert names must match number of experts.")

    def decide_routing(self, input_value: float) -> List[int]:
        """
        Determine which experts to route the input to.
        This is a simple routing logic:
        - If input is negative, use first half of experts.
        - If input is positive, use second half.
        - If zero, use all.

        Args:
            input_value: The input float value.

        Returns:
            A list of expert indices.
        """
        num_experts = len(self.block.experts)
        if input_value < 0:
            # Route to first half
            return list(range(num_experts // 2 + (1 if num_experts == 1 else 0)))
        elif input_value > 0:
             # Route to second half
            start_idx = num_experts // 2
            return list(range(start_idx, num_experts))
        else:
            # Route to all
            return list(range(num_experts))

    def process(self, input_value: float) -> Dict[str, Any]:
        """
        Process an input value through the MoE block.

        Args:
            input_value: The value to process.

        Returns:
            A dictionary containing the result, routing info, and active experts.
        """
        routing_indices = self.decide_routing(input_value)

        # If no experts selected (edge case with empty list logic), default to all
        if not routing_indices:
             routing_indices = list(range(len(self.block.experts)))

        result = self.block.forward(input_value, routing_indices)

        active_experts = [self.expert_names[i] for i in routing_indices]

        return {
            "input": input_value,
            "output": result,
            "routing_indices": routing_indices,
            "active_experts": active_experts
        }
