"""
Telemetry Integration Guide and Utility Functions
===================================================
This module provides utilities for integrating the diagnostic telemetry system
into the existing A2A-MCP orchestrator and decision agent components.
"""

from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime

from orchestrator.telemetry_service import TelemetryService, get_telemetry, init_telemetry
from judge.dmn_decision_engine import DMNDecisionEngine, DecisionOutcome, get_dmn, init_dmn
from schemas.telemetry import DMNToken, ConstraintViolation, DTCSeverity


# ============================================================================
# Integration Points - Hook these into existing agent execution
# ============================================================================


def hook_coder_agent_telemetry(
    telemetry: TelemetryService,
    input_embedding: Optional[List[float]],
    output_embedding: Optional[List[float]],
    artifact_id: str,
    duration_ms: float,
    success: bool = True,
    error: Optional[str] = None,
):
    """
    Hook for CoderAgent to report telemetry

    Called after generate_solution() in agents/coder.py
    """
    telemetry.log_event(
        component="CoderAgent",
        event_type="code_generation_complete",
        input_embedding=input_embedding,
        output_embedding=output_embedding,
        metadata={
            "artifact_type": "code_solution",
            "model": "codestral-latest",
        },
        success=success,
        error_message=error,
        duration_ms=duration_ms,
        artifact_id=artifact_id,
    )


def hook_judge_evaluation_telemetry(
    telemetry: TelemetryService,
    action_type: str,
    judgment_vector: Optional[List[float]],
    scores: Dict[str, float],  # SAFETY, SPEC_ALIGNMENT, PLAYER_INTENT, LATENCY
    final_score: float,
    approved: bool,
):
    """
    Hook for Judge to report evaluation telemetry

    Called after JudgmentModel.evaluate_criteria() in judge/decision.py
    """
    telemetry.log_event(
        component="Judge",
        event_type="action_evaluation",
        output_embedding=judgment_vector,
        metadata={
            "action_type": action_type,
            "scores": scores,
            "final_score": final_score,
            "approved": approved,
        },
        success=approved,
    )


def hook_orchestrator_state_change_telemetry(
    telemetry: TelemetryService,
    state_from: str,
    state_to: str,
    phase: str,
    success: bool = True,
):
    """
    Hook for StateFlow to report state transitions

    Called in orchestrator/stateflow.py state change methods
    """
    telemetry.log_event(
        component="StateFlow",
        event_type="state_transition",
        metadata={
            "from_state": state_from,
            "to_state": state_to,
            "phase": phase,
        },
        success=success,
    )


def hook_transformer_output_telemetry(
    telemetry: TelemetryService,
    prompt_embedding: List[float],
    generated_embedding: List[float],
    expected_embedding: List[float],
    artifact_id: str,
):
    """
    Hook to track transformer (LLM) output differences

    Called after LLMService.call_llm() in orchestrator/llm_util.py
    Track embedding diffs from prompt → generated → expected
    """
    diff = telemetry.track_transformer_diff(
        prompt_embedding=prompt_embedding,
        generated_embedding=generated_embedding,
        expected_embedding=expected_embedding,
        generated_artifact_id=artifact_id,
        prompt_id=str(uuid.uuid4()),
    )
    return diff


def hook_structural_gap_detection(
    telemetry: TelemetryService,
    source_agent: str,
    target_agent: str,
    artifact: Dict[str, Any],
    expected_schema: Dict[str, Any],
    source_embedding: Optional[List[float]] = None,
    target_embedding: Optional[List[float]] = None,
):
    """
    Hook to detect structural gaps between agent interfaces

    Call when artifact is passed from source_agent to target_agent
    """
    gap = telemetry.detect_structural_gap(
        source_component=source_agent,
        target_component=target_agent,
        artifact_type=artifact.get("type", "unknown"),
        expected_schema=expected_schema,
        actual_schema=artifact,
        expected_embedding=target_embedding,
        actual_embedding=source_embedding,
    )
    return gap


# ============================================================================
# Diagnostic Report Generation
# ============================================================================


def generate_phase_diagnostic(
    telemetry: TelemetryService,
    phase_name: str,
    trigger_event: str,
    structural_gaps: Optional[List] = None,
):
    """
    Generate diagnostic report for a pipeline phase

    Args:
        telemetry: TelemetryService instance
        phase_name: Pipeline phase (e.g., 'transformer_output', 'judge_evaluation')
        trigger_event: What triggered the diagnostic
        structural_gaps: Optional list of detected gaps

    Returns:
        DiagnosticReport
    """
    report = telemetry.generate_diagnostic_report(
        execution_phase=phase_name,
        trigger_event=trigger_event,
        structural_gaps=structural_gaps,
    )
    return report


def analyze_embedding_trajectory(
    telemetry: TelemetryService,
    min_divergence_threshold: float = 0.3,
) -> Dict[str, Any]:
    """
    Analyze embedding progression through pipeline

    Returns analysis of how embeddings evolved, where they diverged significantly
    """
    trajectory = telemetry.embedding_trajectory

    analysis = {
        "total_hops": len(trajectory),
        "components_traversed": [comp for comp, _ in trajectory],
        "divergence_points": [],
    }

    if len(trajectory) > 1:
        from scipy.spatial.distance import cosine

        for i in range(len(trajectory) - 1):
            comp1, vec1 = trajectory[i]
            comp2, vec2 = trajectory[i + 1]

            dist = cosine(vec1, vec2)
            if dist > min_divergence_threshold:
                analysis["divergence_points"].append(
                    {
                        "from": comp1,
                        "to": comp2,
                        "distance": dist,
                        "severity": "critical"
                        if dist > 0.6
                        else "high" if dist > 0.4 else "medium",
                    }
                )

    return analysis


# ============================================================================
# DMN Integration - Converting Loose Threads to DMN Tokens
# ============================================================================


def convert_diagnostic_to_dmn_token(
    report,  # DiagnosticReport
    dmn_engine: DMNDecisionEngine,
) -> DMNToken:
    """
    Convert diagnostic report findings into DMN token for decision engine

    Args:
        report: DiagnosticReport from telemetry
        dmn_engine: DMNDecisionEngine instance

    Returns:
        DMNToken ready for DMN evaluation
    """
    # Build problem statement from DTCs
    dtc_descriptions = []
    for dtc_code in report.detected_dtcs:
        from schemas.telemetry import DTC_CATALOG

        if dtc_code in DTC_CATALOG:
            dtc = DTC_CATALOG[dtc_code]
            dtc_descriptions.append(f"{dtc.code}: {dtc.name} - {dtc.description}")

    problem_statement = (
        f"Diagnostic report for {report.execution_phase}\n"
        f"Detected DTCs ({len(report.detected_dtcs)}):\n"
        + "\n".join(dtc_descriptions)
        + f"\nStructural gaps: {len(report.structural_gaps)}\n"
        + f"Vector divergence points: {len(report.vector_divergence_points)}"
    )

    # Extract constraint violations from DTCs
    constraints = []
    for gap in report.structural_gaps:
        constraints.append(
            {
                "name": f"Schema gap {gap.source_component}→{gap.target_component}",
                "dtc": gap.related_dtc or "I01-03",
                "severity": gap.severity.value,
            }
        )

    # Use latest embedding from trajectory
    embedding = None
    if report.embedding_trajectory:
        _, embedding = report.embedding_trajectory[-1]

    token = DMNToken(
        token_id=str(uuid.uuid4()),
        loose_thread_id=report.report_id,
        vector=embedding or [0.0] * 768,  # Default to zero vector if unavailable
        problem_statement=problem_statement,
        context_artifacts=[],
        constraints=constraints,
        decision_criteria_input={
            "SAFETY": 1.0 if "safety" in problem_statement.lower() else 0.5,
            "SPEC_ALIGNMENT": 0.5,
            "PLAYER_INTENT": 0.5,
            "LATENCY": 0.3,
        },
    )

    return token


def consume_loose_threads_with_dmn(
    dmn_engine: DMNDecisionEngine,
    loose_thread_tokens: List[DMNToken],
    judge_score: float,
) -> Dict[str, Any]:
    """
    Process loose threads through DMN decision engine

    Args:
        dmn_engine: DMNDecisionEngine instance
        loose_thread_tokens: List of DMN tokens representing issues
        judge_score: Overall judge evaluation score (0-1)

    Returns:
        Formal decision with remediation recommendations
    """
    decision = dmn_engine.make_formal_decision(
        loose_threads=loose_thread_tokens,
        judge_score=judge_score,
    )

    return decision


# ============================================================================
# Quickstart Integration Example
# ============================================================================


def quickstart_telemetry_integration(db_session=None):
    """
    Quick setup for integrating telemetry into system execution

    Example usage in main orchestrator loop:

    ```python
    from orchestrator.telemetry_integration import quickstart_telemetry_integration

    # Initialize telemetry early
    telemetry, dmn = quickstart_telemetry_integration(db_session)

    # During execution:
    telemetry.log_event(
        component="CoderAgent",
        event_type="generation_complete",
        success=True,
        artifact_id=artifact.id
    )

    # At phase boundaries:
    from orchestrator.telemetry_integration import generate_phase_diagnostic
    report = generate_phase_diagnostic(telemetry, "transformer_output", "phase_complete")

    # Before making decisions:
    from orchestrator.telemetry_integration import convert_diagnostic_to_dmn_token
    token = convert_diagnostic_to_dmn_token(report, dmn)

    outcome, findings = dmn.evaluate_token(token)
    # Use outcome to determine next action
    ```
    """
    telemetry = init_telemetry(db_session)
    dmn = init_dmn()

    return telemetry, dmn


# ============================================================================
# Telemetry Report Export Utilities
# ============================================================================


def export_diagnostic_report_markdown(report) -> str:
    """Export diagnostic report as markdown for human review"""
    from datetime import datetime

    md = f"""
# Diagnostic Report - {report.report_id}

**Generated:** {report.timestamp}
**Phase:** {report.execution_phase}
**Trigger:** {report.trigger_event}

## Summary
{report.summary}

## Detected DTCs
"""
    from schemas.telemetry import DTC_CATALOG

    for dtc_code in report.detected_dtcs:
        if dtc_code in DTC_CATALOG:
            dtc = DTC_CATALOG[dtc_code]
            md += f"""
### {dtc.code}: {dtc.name}
- **Severity:** {dtc.severity.value}
- **Description:** {dtc.description}
- **Remediation:** {dtc.remediation}
"""

    md += f"""
## Structural Gaps: {len(report.structural_gaps)}
"""
    for gap in report.structural_gaps:
        md += f"""
### {gap.source_component} → {gap.target_component}
- **Missing Fields:** {', '.join(gap.missing_fields) or 'None'}
- **Extra Fields:** {', '.join(gap.extra_fields) or 'None'}
- **Semantic Distance:** {gap.semantic_distance or 'N/A'}
- **Related DTC:** {gap.related_dtc or 'N/A'}
"""

    md += f"""
## Recommendations
"""
    for rec in report.recommendations:
        md += f"- {rec}\n"

    if report.critical_actions:
        md += f"""
## CRITICAL ACTIONS REQUIRED
"""
        for action in report.critical_actions:
            md += f"- ⚠️ {action}\n"

    return md


def export_dmn_decision_table_csv(dmn_engine: DMNDecisionEngine) -> str:
    """Export DMN decision rules as CSV for audit trail"""
    csv = "table_name,rule_id,rule_name,condition,outcome,priority\n"

    for table_name, table in dmn_engine.tables.items():
        for rule in table.rules:
            csv += (
                f'"{table_name}","{rule.rule_id}","{rule.name}",'
                f'"{rule.condition}","{rule.outcome.value}",{rule.priority}\n'
            )

    return csv
