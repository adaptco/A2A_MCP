"""Pull request template registry resolver."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping


class UnknownPRTemplateError(ValueError):
    """Raised when a ``pr_template_id`` is not present in the registry."""


@dataclass(slots=True)
class PRTemplateResolver:
    """Resolve pull request templates from a JSON registry file."""

    registry_path: Path = Path("policy/pr_templates.json")

    def resolve(self, template_id: str) -> str:
        """Return the markdown template mapped to ``template_id``.

        Raises
        ------
        UnknownPRTemplateError
            If ``template_id`` is not in the registry.
        """

        registry = self._load_registry()
        template = registry.get(template_id)
        if template is None:
            raise UnknownPRTemplateError(f"Unknown pr_template_id: {template_id}")
        return template

    def is_known(self, template_id: str) -> bool:
        """Return ``True`` when ``template_id`` exists in the registry."""

        return template_id in self._load_registry()

    def _load_registry(self) -> Mapping[str, str]:
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("PR template registry must be a JSON object")
        return payload


__all__ = ["PRTemplateResolver", "UnknownPRTemplateError"]
