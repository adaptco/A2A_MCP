"""Multi-criteria decision model for agent judgment."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class CriteriaType(str, Enum):
    """Types of decision criteria."""
    SAFETY = "safety"           # Safety constraints
    SPEC_ALIGNMENT = "spec"     # Specification adherence
    PLAYER_INTENT = "intent"    # Player/user goal alignment
    LATENCY = "latency"          # Execution speed


@dataclass
class DecisionCriteria:
    """Evaluation criteria for decision scoring."""
    criteria_type: CriteriaType
    weight: float = 1.0  # Relative importance (0.0-1.0)
    scorer: Callable[[Any], float] = None  # Function: context -> score [0, 1]
    description: str = ""

    def score(self, context: Any) -> float:
        """Score this criterion given context."""
        if not self.scorer:
            return 0.5  # Neutral default
        try:
            return min(1.0, max(0.0, self.scorer(context)))
        except Exception:
            return 0.0


@dataclass
class ActionScore:
    """Scored action with criteria breakdown."""
    action: str
    overall_score: float
    criterion_scores: Dict[CriteriaType, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<ActionScore action={self.action} score={self.overall_score:.3f}>"


class JudgmentModel:
    """
    Multi-criteria decision analysis for agent judgment.
    Synchronous per-frame evaluation; no RL (extensible for future MARL).
    Loads criteria weights from specs/judge_criteria.yaml.
    """

    def __init__(self, preset: str = "simulation"):
        self._criteria: Dict[CriteriaType, DecisionCriteria] = {}
        self._preset = preset
        self._load_criteria_from_specs()

    def _load_criteria_from_specs(self) -> None:
        """Load criteria weights from specs/judge_criteria.yaml."""
        try:
            from specs.loader import get_loader
            loader = get_loader()
            weights = loader.get_judge_preset(self._preset)

            # Update weights from loaded specs
            self._load_default_criteria()
            for crit_type in self._criteria:
                key = crit_type.value
                if key in weights:
                    self._criteria[crit_type].weight = weights[key]
        except Exception as e:
            # Fallback to defaults if specs loading fails
            if not self._criteria:
                self._load_default_criteria()

    def _load_default_criteria(self) -> None:
        """Initialize default criteria."""
        defaults = [
            DecisionCriteria(
                criteria_type=CriteriaType.SAFETY,
                weight=1.0,
                description="Vehicle and environment safety constraints",
                scorer=lambda ctx: 1.0 if ctx.get("nearest_obstacle_distance_m", 0) > 5 else 0.6
                    if ctx.get("nearest_obstacle_distance_m", 0) > 2 else 0.0,
            ),
            DecisionCriteria(
                criteria_type=CriteriaType.SPEC_ALIGNMENT,
                weight=0.8,
                description="Adherence to Supra physics and performance specs",
                scorer=lambda ctx: 1.0,  # Placeholder
            ),
            DecisionCriteria(
                criteria_type=CriteriaType.PLAYER_INTENT,
                weight=0.7,
                description="Alignment with user/player goal",
                scorer=lambda ctx: 0.85,  # Placeholder
            ),
            DecisionCriteria(
                criteria_type=CriteriaType.LATENCY,
                weight=0.5,
                description="Execution within time budget",
                scorer=lambda ctx: 1.0,  # Placeholder
            ),
        ]

        for criterion in defaults:
            self._criteria[criterion.criteria_type] = criterion

    def judge_actions(
        self,
        actions: List[str],
        context: Dict[str, Any]
    ) -> List[ActionScore]:
        """
        Evaluate multiple actions using MCDA framework.
        Returns sorted list by overall_score (highest first).
        """
        scores: List[ActionScore] = []

        for action in actions:
            # Calculate per-criterion scores
            criterion_scores: Dict[CriteriaType, float] = {}
            weighted_sum = 0.0
            weight_sum = 0.0

            for crit_type, criterion in self._criteria.items():
                crit_score = criterion.score(context)
                criterion_scores[crit_type] = crit_score
                weighted_sum += criterion.weight * crit_score
                weight_sum += criterion.weight

            # Weighted average
            overall_score = weighted_sum / weight_sum if weight_sum > 0 else 0.5

            score = ActionScore(
                action=action,
                overall_score=overall_score,
                criterion_scores=criterion_scores,
                metadata={"preset": self._preset},
            )
            scores.append(score)

        # Sort by score (highest first)
        scores.sort(key=lambda s: s.overall_score, reverse=True)
        return scores

    def best_action(
        self,
        actions: List[str],
        context: Dict[str, Any]
    ) -> Optional[ActionScore]:
        """Get highest-scoring action."""
        scores = self.judge_actions(actions, context)
        return scores[0] if scores else None

    def __repr__(self) -> str:
        criteria_info = ", ".join(
            f"{ct.value}={c.weight:.1f}" for ct, c in self._criteria.items()
        )
        return f"<JudgmentModel preset={self._preset} criteria=[{criteria_info}]>"
