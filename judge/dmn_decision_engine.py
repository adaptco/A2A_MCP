"""
DMN Decision Model Engine - Codified Loose Thread Resolution
=============================================================
Decision Model and Notation (DMN) implementation for consuming telemetry tokens,
constraint violations, and loose threads. Integrated with Decision Agent for
formal decision-making and remediation.
"""

from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import uuid
from datetime import datetime

from schemas.telemetry import DMNToken, DTCSeverity, ConstraintViolation


class DecisionOutcome(str, Enum):
    """DMN Decision outcomes"""
    PROCEED = "PROCEED"              # System can continue
    HEALING_REQUIRED = "HEALING_REQUIRED"  # Trigger self-healing
    ESCALATE_TO_MANUAL = "ESCALATE_TO_MANUAL"  # Requires human intervention
    TERMINATE = "TERMINATE"          # System must halt


class ConstraintViolationMode(str, Enum):
    """How constraints are evaluated"""
    STRICT = "strict"                # All constraints must pass (AND)
    LENIENT = "lenient"              # At least one constraint must pass (OR)
    WEIGHTED = "weighted"            # Weighted evaluation


class DMNDecisionRule:
    """A single DMN decision rule"""

    def __init__(
        self,
        rule_id: str,
        name: str,
        condition: str,
        outcome: DecisionOutcome,
        priority: int = 0,
    ):
        self.rule_id = rule_id
        self.name = name
        self.condition = condition  # Semantic description of condition
        self.outcome = outcome
        self.priority = priority  # Higher priority rules evaluated first

    def __repr__(self):
        return f"<DMNRule {self.name} → {self.outcome.value}>"


class DMNTable:
    """DMN Decision Table - Maps constraints to outcomes"""

    def __init__(self, table_id: str, name: str):
        self.table_id = table_id
        self.name = name
        self.rules: List[DMNDecisionRule] = []
        self.hit_policy = "first"  # 'first', 'unique', 'any', 'priority'

    def add_rule(self, rule: DMNDecisionRule):
        """Add a decision rule"""
        self.rules.append(rule)
        # Sort by priority (descending)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def evaluate(
        self,
        context: Dict[str, Any],
    ) -> Tuple[DecisionOutcome, Optional[str]]:
        """
        Evaluate decision rules against context

        Returns:
            (DecisionOutcome, explanation)
        """
        for rule in self.rules:
            # Evaluate rule condition against context
            # (Simplified semantic evaluation)
            if self._matches_condition(rule, context):
                return rule.outcome, rule.name

        # Default outcome if no rules match
        return DecisionOutcome.PROCEED, "No specific rules matched, proceeding"

    @staticmethod
    def _matches_condition(rule: DMNDecisionRule, context: Dict[str, Any]) -> bool:
        """Evaluate whether rule condition matches context"""
        # This is a simplified implementation
        # In production, would use expression evaluator

        # Check severity-based conditions
        if "critical_dtc" in context and context["critical_dtc"]:
            if "critical" in rule.condition.lower():
                return True
        if "healing_loop_exhausted" in context and context["healing_loop_exhausted"]:
            if "exhausted" in rule.condition.lower():
                return True
        if "structural_gap_count" in context:
            gap_count = context["structural_gap_count"]
            if gap_count > 3 and "gaps" in rule.condition.lower():
                return True

        return False


class DMNDecisionEngine:
    """
    Main DMN Decision Engine for A2A-MCP
    Consumes telemetry, structural gaps, and constraint violations
    Produces formal decisions for remediation
    """

    def __init__(self):
        self.tables: Dict[str, DMNTable] = {}
        self.decisions_made: List[Dict[str, Any]] = []
        self._initialize_decision_tables()

    def _initialize_decision_tables(self):
        """Initialize standard DMN decision tables"""

        # Table 1: DTC Severity → Initial Response
        dtc_response = DMNTable("dtc_response", "DTC Severity Response")

        dtc_response.add_rule(
            DMNDecisionRule(
                "dtc_critical",
                "Critical DTC detected - terminate immediately",
                "critical_dtc = true",
                DecisionOutcome.TERMINATE,
                priority=100,
            )
        )
        dtc_response.add_rule(
            DMNDecisionRule(
                "dtc_high",
                "High severity DTC - escalate to manual review",
                "high_severity_count > 0",
                DecisionOutcome.ESCALATE_TO_MANUAL,
                priority=90,
            )
        )
        dtc_response.add_rule(
            DMNDecisionRule(
                "dtc_medium",
                "Medium severity with self-healing capability",
                "medium_severity_count > 0 AND healing_capable = true",
                DecisionOutcome.HEALING_REQUIRED,
                priority=80,
            )
        )

        self.tables["dtc_response"] = dtc_response

        # Table 2: Structural Gaps → Compatibility Decision
        gap_compatibility = DMNTable("gap_compatibility", "Structural Gap Compatibility")

        gap_compatibility.add_rule(
            DMNDecisionRule(
                "gaps_severe",
                "Too many structural gaps - incompatible interfaces",
                "gaps > 3",
                DecisionOutcome.ESCALATE_TO_MANUAL,
                priority=95,
            )
        )
        gap_compatibility.add_rule(
            DMNDecisionRule(
                "gaps_recoverable",
                "Gaps detected but recoverable via healing",
                "gaps > 0 AND gaps <= 3",
                DecisionOutcome.HEALING_REQUIRED,
                priority=70,
            )
        )

        self.tables["gap_compatibility"] = gap_compatibility

        # Table 3: Healing Loop Exhaustion → Escalation
        healing_exhaustion = DMNTable("healing_exhaustion", "Healing Loop Status")

        healing_exhaustion.add_rule(
            DMNDecisionRule(
                "healing_exhausted",
                "Self-healing loop reached max retries",
                "healing_loop_exhausted = true",
                DecisionOutcome.ESCALATE_TO_MANUAL,
                priority=100,
            )
        )
        healing_exhaustion.add_rule(
            DMNDecisionRule(
                "healing_retries_available",
                "Retries still available, continue healing",
                "retries_remaining > 0",
                DecisionOutcome.HEALING_REQUIRED,
                priority=60,
            )
        )

        self.tables["healing_exhaustion"] = healing_exhaustion

        # Table 4: Transformer Quality → Continuation Decision
        transformer_quality = DMNTable("transformer_quality", "Transformer Output Quality")

        transformer_quality.add_rule(
            DMNDecisionRule(
                "transformer_critical_miss",
                "Transformer output critically misaligned from expected",
                "transformer_diff_status = CRITICAL_MISS",
                DecisionOutcome.ESCALATE_TO_MANUAL,
                priority=90,
            )
        )
        transformer_quality.add_rule(
            DMNDecisionRule(
                "transformer_drifted",
                "Transformer output drifted from expected - attempt healing",
                "transformer_diff_status = DRIFTED",
                DecisionOutcome.HEALING_REQUIRED,
                priority=70,
            )
        )
        transformer_quality.add_rule(
            DMNDecisionRule(
                "transformer_aligned",
                "Transformer output aligned as expected",
                "transformer_diff_status = ALIGNED",
                DecisionOutcome.PROCEED,
                priority=50,
            )
        )

        self.tables["transformer_quality"] = transformer_quality

    def evaluate_token(
        self,
        token: DMNToken,
    ) -> Tuple[DecisionOutcome, Dict[str, Any]]:
        """
        Evaluate a DMN token through decision tables

        Args:
            token: Telemetry token with problem and constraints

        Returns:
            (DecisionOutcome, detailed_analysis)
        """
        decision_outcome = DecisionOutcome.PROCEED
        findings = {
            "token_id": token.token_id,
            "timestamp": datetime.utcnow().isoformat(),
            "table_evaluations": {},
        }

        # Build evaluation context from token
        context = self._build_evaluation_context(token)

        # Evaluate each decision table
        for table_name, table in self.tables.items():
            outcome, explanation = table.evaluate(context)
            findings["table_evaluations"][table_name] = {
                "outcome": outcome.value,
                "explanation": explanation,
            }

            # Update decision outcome (use most severe)
            if outcome == DecisionOutcome.TERMINATE:
                decision_outcome = DecisionOutcome.TERMINATE
            elif (
                outcome == DecisionOutcome.ESCALATE_TO_MANUAL
                and decision_outcome != DecisionOutcome.TERMINATE
            ):
                decision_outcome = DecisionOutcome.ESCALATE_TO_MANUAL
            elif (
                outcome == DecisionOutcome.HEALING_REQUIRED
                and decision_outcome == DecisionOutcome.PROCEED
            ):
                decision_outcome = DecisionOutcome.HEALING_REQUIRED

        # Record decision
        decision_record = {
            "decision_id": str(uuid.uuid4()),
            "token_id": token.token_id,
            "outcome": decision_outcome,
            "findings": findings,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.decisions_made.append(decision_record)

        return decision_outcome, findings

    def _build_evaluation_context(self, token: DMNToken) -> Dict[str, Any]:
        """Build evaluation context from token for rule matching"""
        context = {
            "token_id": token.token_id,
            "problem": token.problem_statement,
            "constraints_count": len(token.constraints),
        }

        # Extract constraint information
        critical_dtcs = False
        high_severity_count = 0
        medium_severity_count = 0
        structural_gaps = 0

        for constraint in token.constraints:
            if "dtc" in constraint:
                dtc_code = constraint.get("violated_by_dtc", "")
                severity = constraint.get("severity", "")

                if severity == "critical":
                    critical_dtcs = True
                elif severity == "high":
                    high_severity_count += 1
                elif severity == "medium":
                    medium_severity_count += 1

                if "structural_gap" in dtc_code.lower():
                    structural_gaps += 1

        context.update(
            {
                "critical_dtc": critical_dtcs,
                "high_severity_count": high_severity_count,
                "medium_severity_count": medium_severity_count,
                "structural_gap_count": structural_gaps,
                "healing_capable": True,  # Default to true (would be determined dynamically)
                "healing_loop_exhausted": False,
                "retries_remaining": 3,  # Would be tracked in orchestrator
            }
        )

        # Add decision criteria (from Judge)
        context.update(token.decision_criteria_input)

        return context

    def apply_constraint_resolution(
        self,
        constraint: ConstraintViolation,
        decision_outcome: DecisionOutcome,
    ) -> Dict[str, Any]:
        """
        Apply resolution logic for violated constraint

        Args:
            constraint: The violated constraint
            decision_outcome: The DMN decision outcome

        Returns:
            Resolution recommendation
        """
        resolution = {
            "constraint_id": constraint.constraint_id,
            "constraint_name": constraint.constraint_name,
            "violated_dtc": constraint.violated_by_dtc,
            "decision_outcome": decision_outcome.value,
        }

        # Map outcomes to actions
        if decision_outcome == DecisionOutcome.TERMINATE:
            resolution["action"] = "HALT_SYSTEM"
            resolution["reason"] = f"Critical constraint violation in {constraint.constraint_name}"

        elif decision_outcome == DecisionOutcome.ESCALATE_TO_MANUAL:
            resolution["action"] = "ESCALATE_TO_HUMAN"
            resolution["reason"] = f"Unable to auto-resolve {constraint.constraint_name}"
            resolution["artifacts_for_review"] = constraint.affects_objectives

        elif decision_outcome == DecisionOutcome.HEALING_REQUIRED:
            resolution["action"] = "TRIGGER_HEALING_LOOP"
            resolution["healing_target"] = constraint.violated_by_dtc
            resolution["remediation"] = self._get_remediation(constraint.violated_by_dtc)

        else:  # PROCEED
            resolution["action"] = "CONTINUE_EXECUTION"
            resolution["reason"] = "Constraint satisfied or mitigated"

        return resolution

    @staticmethod
    def _get_remediation(dtc_code: str) -> str:
        """Get remediation from DTC catalog"""
        from schemas.telemetry import DTC_CATALOG

        if dtc_code in DTC_CATALOG:
            return DTC_CATALOG[dtc_code].remediation
        return "Review logs and contact support"

    def make_formal_decision(
        self,
        loose_threads: List[DMNToken],
        judge_score: float,
    ) -> Dict[str, Any]:
        """
        Make formal decision based on multiple loose threads and judge score

        Args:
            loose_threads: List of telemetry tokens to evaluate
            judge_score: Overall judge decision score (0-1)

        Returns:
            Formal decision with recommendations
        """
        decision = {
            "decision_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "judge_score": judge_score,
            "loose_thread_count": len(loose_threads),
            "thread_outcomes": [],
        }

        worst_outcome = DecisionOutcome.PROCEED

        for token in loose_threads:
            outcome, findings = self.evaluate_token(token)
            decision["thread_outcomes"].append(
                {
                    "loose_thread_id": token.loose_thread_id,
                    "outcome": outcome.value,
                    "findings": findings,
                }
            )

            # Track worst outcome
            if outcome == DecisionOutcome.TERMINATE:
                worst_outcome = DecisionOutcome.TERMINATE
            elif (
                outcome == DecisionOutcome.ESCALATE_TO_MANUAL
                and worst_outcome != DecisionOutcome.TERMINATE
            ):
                worst_outcome = DecisionOutcome.ESCALATE_TO_MANUAL
            elif (
                outcome == DecisionOutcome.HEALING_REQUIRED
                and worst_outcome == DecisionOutcome.PROCEED
            ):
                worst_outcome = DecisionOutcome.HEALING_REQUIRED

        # Factor in judge score
        if judge_score < 0.3:
            worst_outcome = DecisionOutcome.ESCALATE_TO_MANUAL
        elif judge_score < 0.6 and worst_outcome == DecisionOutcome.PROCEED:
            worst_outcome = DecisionOutcome.HEALING_REQUIRED

        decision["final_outcome"] = worst_outcome.value
        decision["confidence"] = min(judge_score, 0.95)  # Cap at 95%

        return decision


# Global DMN instance
_dmn_engine: Optional[DMNDecisionEngine] = None


def init_dmn() -> DMNDecisionEngine:
    """Initialize global DMN decision engine"""
    global _dmn_engine
    _dmn_engine = DMNDecisionEngine()
    return _dmn_engine


def get_dmn() -> DMNDecisionEngine:
    """Get global DMN decision engine instance"""
    if _dmn_engine is None:
        raise RuntimeError("DMN engine not initialized. Call init_dmn() first.")
    return _dmn_engine
