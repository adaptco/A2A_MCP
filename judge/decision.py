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
<<<<<<< HEAD
    scorer: Callable[[Any], float] = None  # Function: context -> score [0, 1]
=======
    scorer: Callable[[Any], float] = None  # Function: context → score [0, 1]
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
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
<<<<<<< HEAD
                description="Vehicle and environment safety constraints",
                scorer=lambda ctx: 1.0 if ctx.get("nearest_obstacle_distance_m", 0) > 5 else 0.6
                    if ctx.get("nearest_obstacle_distance_m", 0) > 2 else 0.0,
=======
                scorer=self._scorer_safety,
                description="No out-of-bounds, collision-free, token cap respected"
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
            ),
            DecisionCriteria(
                criteria_type=CriteriaType.SPEC_ALIGNMENT,
                weight=0.8,
<<<<<<< HEAD
                description="Adherence to Supra physics and performance specs",
                scorer=lambda ctx: 1.0,  # Placeholder
=======
                scorer=self._scorer_spec,
                description="Adherence to Supra/game specs"
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
            ),
            DecisionCriteria(
                criteria_type=CriteriaType.PLAYER_INTENT,
                weight=0.7,
<<<<<<< HEAD
                description="Alignment with user/player goal",
                scorer=lambda ctx: 0.85,  # Placeholder
=======
                scorer=self._scorer_intent,
                description="Alignment with player intent"
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
            ),
            DecisionCriteria(
                criteria_type=CriteriaType.LATENCY,
                weight=0.5,
<<<<<<< HEAD
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
=======
                scorer=self._scorer_latency,
                description="Execution within time budget"
            ),
        ]

        for criteria in defaults:
            self._criteria[criteria.criteria_type] = criteria

    def register_criterion(self, criteria: DecisionCriteria) -> None:
        """Register a custom decision criterion."""
        self._criteria[criteria.criteria_type] = criteria

    def judge_actions(self, actions: List[str], context: Dict[str, Any]) -> List[ActionScore]:
        """
        Score a list of candidate actions given context.

        Args:
            actions: List of action strings to evaluate
            context: Game state, player intent, constraints, etc.

        Returns:
            Sorted list of ActionScore (best first)
        """
        scores = []

        for action in actions:
            criterion_scores = {}
            weighted_sum = 0.0
            weight_sum = 0.0

            # Evaluate each criterion
            for crit_type, criteria in self._criteria.items():
                score = criteria.score(context)
                criterion_scores[crit_type] = score
                weighted_sum += score * criteria.weight
                weight_sum += criteria.weight

            # Normalize by total weight
            overall_score = weighted_sum / weight_sum if weight_sum > 0 else 0.0

            action_score = ActionScore(
                action=action,
                overall_score=overall_score,
                criterion_scores=criterion_scores,
                metadata={"context_keys": list(context.keys())}
            )
            scores.append(action_score)

        # Sort by overall score, descending
        scores.sort(key=lambda x: x.overall_score, reverse=True)
        return scores

    def best_action(self, actions: List[str], context: Dict[str, Any]) -> Optional[ActionScore]:
        """Return the highest-scoring action."""
        scores = self.judge_actions(actions, context)
        return scores[0] if scores else None

    # Default criterion scorers (override / extend as needed)

    @staticmethod
    def _scorer_safety(context: Dict[str, Any]) -> float:
        """Safety criterion: check bounds, collisions, tokens."""
        # Placeholder: context should include bot_in_bounds, no_collision, token_budget_ok
        safe = context.get("safe", True)
        return 1.0 if safe else 0.0

    @staticmethod
    def _scorer_spec(context: Dict[str, Any]) -> float:
        """Spec alignment: adherence to vehicle/game specs."""
        spec_compliant = context.get("spec_compliant", True)
        return 1.0 if spec_compliant else 0.0

    @staticmethod
    def _scorer_intent(context: Dict[str, Any]) -> float:
        """Player intent: alignment with user goal."""
        intent_match = context.get("intent_match", 0.5)
        return max(0.0, min(1.0, intent_match))

    @staticmethod
    def _scorer_latency(context: Dict[str, Any]) -> float:
        """Latency: execution within time budget."""
        elapsed_ms = context.get("elapsed_ms", 0)
        budget_ms = context.get("budget_ms", 100)
        return max(0.0, 1.0 - (elapsed_ms / budget_ms))

    def __repr__(self) -> str:
        return f"<JudgmentModel criteria={list(self._criteria.keys())}>"
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
