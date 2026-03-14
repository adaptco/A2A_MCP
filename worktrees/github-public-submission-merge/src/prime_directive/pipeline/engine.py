from typing import List, Any, Dict

class PipelineEngine:
    def __init__(self, steps: List[Any] = None):
        self.steps = steps or []

    def add_step(self, step: Any):
        self.steps.append(step)

    def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executes pipeline steps sequentially."""
        if context is None:
            context = {}

        print(f"PipelineEngine: Executing {len(self.steps)} steps.")

        for i, step in enumerate(self.steps):
            print(f"Executing step {i+1}: {step}")
            if hasattr(step, 'execute'):
                context = step.execute(context)
            elif callable(step):
                context = step(context)

        return context
