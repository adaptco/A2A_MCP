"""LLM policy composition utilities.

Provides deterministic merge order for prompt composition:
1) platform/system constraints
2) workflow constraints
3) user/task payload
"""

from __future__ import annotations

from typing import Iterable, List

from schemas.prompt_inputs import PromptIntent


PLATFORM_SYSTEM_CONSTRAINTS: tuple[str, ...] = (
    "You are a helpful coding assistant.",
    "Follow repository contracts and return clear, actionable outputs.",
)


class PolicyComposer:
    """Compose system and user messages from structured prompt intent."""

    @staticmethod
    def _normalize_constraints(values: Iterable[str]) -> List[str]:
        return [item.strip() for item in values if item and item.strip()]

    @classmethod
    def compose_system_prompt(cls, intent: PromptIntent) -> str:
        """Deterministically merge constraints into a system prompt."""
        ordered_constraints: List[str] = []
        ordered_constraints.extend(cls._normalize_constraints(PLATFORM_SYSTEM_CONSTRAINTS))
        ordered_constraints.extend(cls._normalize_constraints(intent.system_constraints))
        ordered_constraints.extend(cls._normalize_constraints(intent.workflow_constraints))

        lines = ["System constraints (ordered):"]
        lines.extend(f"{idx}. {constraint}" for idx, constraint in enumerate(ordered_constraints, start=1))
        return "\n".join(lines)

    @staticmethod
    def compose_user_payload(intent: PromptIntent) -> str:
        """Build user payload after constraints are applied."""
        segments: List[str] = []
        if intent.task_context:
            segments.append(f"Task context:\n{intent.task_context}")
        segments.append(f"User input:\n{intent.user_input}")
        return "\n\n".join(segments)
