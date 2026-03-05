"""
Celine — Planning Agent (agents/Celine/planner.py)

Decomposes high-level user prompts into structured task lists
and generates implementation plans via LLM.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Import the universal runner
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import call_llm  # noqa: E402


SYSTEM_PROMPT = """You are Celine, the Planning Agent in the Sovereign Orchestrator framework.

Your role:
- Decompose high-level prompts into structured, actionable sub-tasks
- Generate implementation plans with clear dependencies
- Map each sub-task to the appropriate agent (Dot, Spryte, Echo, Gloh, Luma)
- Output JSON task lists that conform to the A2A protocol schema

Output format:
{
  "plan_id": "plan-<uuid>",
  "tasks": [
    {
      "task_id": "T-XXX",
      "name": "Task name",
      "description": "What to do",
      "agent": "AgentName",
      "llm_target": "claude|openai|gemini|ollama",
      "depends_on": ["T-YYY"],
      "priority": 1
    }
  ]
}
"""


def decompose_prompt(prompt: str) -> str:
    """Decompose a high-level prompt into a structured task list."""
    llm_target = os.environ.get("LLM_TARGET", "gemini")
    print(f"[Celine] Decomposing prompt via {llm_target}...")

    result = call_llm(SYSTEM_PROMPT, prompt)
    return result


def save_plan(plan_text: str, task_id: str = "T-001") -> Path:
    """Save the generated plan to the artifacts directory."""
    output_dir = Path("artifacts") / task_id
    output_dir.mkdir(parents=True, exist_ok=True)

    plan_file = output_dir / "plan.json"
    plan_file.write_text(plan_text, encoding="utf-8")

    print(f"[Celine] ✅ Plan saved to {plan_file}")
    return plan_file


if __name__ == "__main__":
    user_prompt = os.environ.get("USER_PROMPT", "")
    if not user_prompt and len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:])
    if not user_prompt:
        user_prompt = "Create a default implementation plan for the project."

    plan = decompose_prompt(user_prompt)
    save_plan(plan)
