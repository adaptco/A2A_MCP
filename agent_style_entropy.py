"""Deterministic style-temperature and template routing model for coding agents."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Sequence


DEFAULT_API_SKILLS: tuple[str, ...] = (
    "orchestrate-api",
    "airtable-routing",
    "slack-thread-reply",
    "github-pr-merge",
    "runtime-bridge",
)


@dataclass(frozen=True)
class StyleConfig:
    """Control knobs for enthalpy/entropy style tuning."""

    base_temperature: float = 0.35
    min_temperature: float = 0.15
    max_temperature: float = 0.85
    enthalpy_gain: float = 0.30
    entropy_gain: float = 0.20


def deterministic_embedding(text: str, dimensions: int = 32) -> list[float]:
    """Map text into a deterministic embedding without external model calls."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    for idx in range(dimensions):
        value = digest[idx % len(digest)]
        values.append((value / 255.0) * 2.0 - 1.0)
    return values


def _normalize(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return [0.0 for _ in vector]
    return [value / norm for value in vector]


def uniform_dotproduct(left: Sequence[float], right: Sequence[float]) -> float:
    """Compute normalized dot product for vectors with matching dimensions."""
    if len(left) != len(right):
        raise ValueError("left and right vectors must have matching dimensions")
    left_norm = _normalize(left)
    right_norm = _normalize(right)
    return float(sum(a * b for a, b in zip(left_norm, right_norm)))


def _shannon_entropy(probabilities: Sequence[float]) -> float:
    clamped = [max(1e-12, value) for value in probabilities]
    entropy = -sum(value * math.log(value) for value in clamped)
    return float(entropy / math.log(len(clamped)))


def _risk_scalar(risk_profile: str) -> float:
    normalized = risk_profile.strip().lower()
    if normalized == "high":
        return 1.0
    if normalized == "medium":
        return 0.6
    return 0.3


def build_style_temperature_plan(
    *,
    prompt: str,
    risk_profile: str,
    changed_path_count: int,
    api_skills: Sequence[str] = DEFAULT_API_SKILLS,
    config: StyleConfig = StyleConfig(),
) -> dict[str, Any]:
    """
    Build deterministic style controls:
    - API skill token list for avatar/runtime shell routing.
    - Enthalpy/entropy based style temperature.
    - Uniform dotproduct route to front/back-end templates.
    """
    prompt_vec = deterministic_embedding(prompt)
    template_vectors = {
        "frontend": deterministic_embedding(
            "frontend ui css client component template action rendering"
        ),
        "backend": deterministic_embedding(
            "backend api database queue worker service template action reliability"
        ),
        "fullstack": deterministic_embedding(
            "fullstack frontend backend api ui service template action integration"
        ),
    }

    template_scores = {
        template: uniform_dotproduct(prompt_vec, vector)
        for template, vector in template_vectors.items()
    }
    chosen_template = max(template_scores.items(), key=lambda item: item[1])[0]

    weights = [abs(score) + 1e-4 for score in template_scores.values()]
    weight_total = sum(weights)
    probabilities = [weight / weight_total for weight in weights]
    entropy = _shannon_entropy(probabilities)

    pressure = min(1.0, max(0.1, changed_path_count / 20.0))
    enthalpy = min(1.0, 0.55 * _risk_scalar(risk_profile) + 0.45 * pressure)
    temperature = config.base_temperature + (enthalpy * config.enthalpy_gain) - (
        entropy * config.entropy_gain
    )
    temperature = max(config.min_temperature, min(config.max_temperature, temperature))

    skill_tokens = [
        {
            "skill": skill_name,
            "token": f"api::{skill_name.replace('_', '-').replace(' ', '-').lower()}",
        }
        for skill_name in api_skills
    ]

    template_actions = {
        "frontend": [
            "apply-ui-template",
            "bind-api-contracts",
            "run-client-smoke",
        ],
        "backend": [
            "apply-service-template",
            "validate-schema-contracts",
            "run-api-smoke",
        ],
        "fullstack": [
            "apply-fullstack-template",
            "verify-end-to-end-contracts",
            "run-system-smoke",
        ],
    }

    return {
        "enthalpy": round(enthalpy, 6),
        "entropy": round(entropy, 6),
        "temperature": round(float(temperature), 6),
        "template_scores": {key: round(value, 6) for key, value in template_scores.items()},
        "selected_template": chosen_template,
        "selected_actions": template_actions[chosen_template],
        "api_skill_tokens": skill_tokens,
        "model_style_preferences": {
            "planner": "precise-low-variance",
            "architect": "constraint-aware-balanced",
            "coder": "implementation-focused",
            "tester": "adversarial-strict",
            "reviewer": "risk-prioritized",
        },
    }


__all__ = [
    "DEFAULT_API_SKILLS",
    "StyleConfig",
    "deterministic_embedding",
    "uniform_dotproduct",
    "build_style_temperature_plan",
]
