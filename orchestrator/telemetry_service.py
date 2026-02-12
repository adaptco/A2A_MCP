"""
Telemetry Service - Diagnostic Subsystem
==========================================
Core service for capturing, analyzing, and reporting on system health via DTCs,
embeddings, and formal diagnostic reports for the A2A-MCP system.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from scipy.spatial.distance import cosine
import numpy as np

from schemas.telemetry import (
    DTC_CATALOG,
    TelemetryEvent,
    DiagnosticReport,
    StructuralGap,
    TransformerDiff,
    DMNToken,
    DTCSeverity,
)
from schemas.database import (
    TelemetryEventModel,
    DiagnosticReportModel,
    StructuralGapModel,
    TransformerDiffModel,
    DMNTokenModel,
)


class TelemetryService:
    """Core telemetry and diagnostic service for system monitoring"""

    def __init__(self, db_session=None):
        """Initialize telemetry service with optional database connection"""
        self.db_session = db_session
        self.event_buffer: List[TelemetryEvent] = []
        self.embedding_trajectory: List[Tuple[str, List[float]]] = []

    def log_event(
        self,
        component: str,
        event_type: str,
        input_embedding: Optional[List[float]] = None,
        output_embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
        artifact_id: Optional[str] = None,
    ) -> TelemetryEvent:
        """
        Log a telemetry event with optional embedding tracking

        Args:
            component: Source component (e.g., 'CoderAgent', 'Judge')
            event_type: Event type (e.g., 'inference_complete')
            input_embedding: Input vector to component
            output_embedding: Output vector from component
            metadata: Additional context
            success: Whether operation succeeded
            error_message: Error details if failed
            duration_ms: Execution time
            artifact_id: Related artifact ID

        Returns:
            TelemetryEvent object
        """
        event_id = str(uuid.uuid4())
        embedding_distance = None

        # Calculate embedding distance if both vectors provided
        if input_embedding and output_embedding:
            embedding_distance = cosine(input_embedding, output_embedding)

            # Track embedding trajectory through pipeline
            self.embedding_trajectory.append((component, output_embedding))

        event = TelemetryEvent(
            event_id=event_id,
            component=component,
            event_type=event_type,
            input_embedding=input_embedding,
            output_embedding=output_embedding,
            embedding_distance=embedding_distance,
            metadata=metadata or {},
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
        )

        self.event_buffer.append(event)

        # Persist to database if available
        if self.db_session:
            self._persist_event(event, artifact_id)

        return event

    def _persist_event(self, event: TelemetryEvent, artifact_id: Optional[str] = None):
        """Persist telemetry event to database"""
        try:
            db_event = TelemetryEventModel(
                event_id=event.event_id,
                timestamp=event.timestamp,
                component=event.component,
                event_type=event.event_type,
                input_embedding=event.input_embedding,
                output_embedding=event.output_embedding,
                embedding_distance=event.embedding_distance,
                metadata=event.metadata,
                duration_ms=event.duration_ms,
                success=event.success,
                error_message=event.error_message,
                artifact_id=artifact_id,
            )
            self.db_session.add(db_event)
            self.db_session.commit()
        except Exception as e:
            print(f"Failed to persist telemetry event: {e}")

    def detect_structural_gap(
        self,
        source_component: str,
        target_component: str,
        artifact_type: str,
        expected_schema: Dict[str, Any],
        actual_schema: Dict[str, Any],
        expected_embedding: Optional[List[float]] = None,
        actual_embedding: Optional[List[float]] = None,
    ) -> Optional[StructuralGap]:
        """
        Detect and record a structural gap between components

        Returns:
            StructuralGap object if gap detected, None if schemas match
        """
        # Check schema compatibility
        missing_fields = set(expected_schema.keys()) - set(actual_schema.keys())
        extra_fields = set(actual_schema.keys()) - set(expected_schema.keys())

        # Calculate semantic distance if embeddings provided
        semantic_distance = None
        if expected_embedding and actual_embedding:
            semantic_distance = cosine(expected_embedding, actual_embedding)

        if not missing_fields and not extra_fields and not semantic_distance:
            # No gap detected
            return None

        # Determine severity based on gap type
        if missing_fields:
            severity = DTCSeverity.HIGH
        elif extra_fields and semantic_distance and semantic_distance > 0.5:
            severity = DTCSeverity.MEDIUM
        else:
            severity = DTCSeverity.LOW

        # Find related DTC if applicable
        related_dtc = None
        if "I01-03" in DTC_CATALOG:  # STRUCTURAL_GAP_DETECTED
            if missing_fields:
                related_dtc = "I01-03"

        gap = StructuralGap(
            gap_id=str(uuid.uuid4()),
            source_component=source_component,
            target_component=target_component,
            artifact_type=artifact_type,
            expected_schema=expected_schema,
            actual_schema=actual_schema,
            missing_fields=list(missing_fields),
            extra_fields=list(extra_fields),
            expected_embedding=expected_embedding,
            actual_embedding=actual_embedding,
            semantic_distance=semantic_distance,
            related_dtc=related_dtc,
            severity=severity,
        )

        # Persist to database
        if self.db_session:
            self._persist_structural_gap(gap)

        return gap

    def _persist_structural_gap(self, gap: StructuralGap):
        """Persist structural gap to database"""
        try:
            db_gap = StructuralGapModel(
                gap_id=gap.gap_id,
                timestamp=gap.timestamp,
                source_component=gap.source_component,
                target_component=gap.target_component,
                artifact_type=gap.artifact_type,
                expected_schema=gap.expected_schema,
                actual_schema=gap.actual_schema,
                missing_fields=gap.missing_fields,
                extra_fields=gap.extra_fields,
                expected_embedding=gap.expected_embedding,
                actual_embedding=gap.actual_embedding,
                semantic_distance=gap.semantic_distance,
                related_dtc=gap.related_dtc,
                severity=gap.severity.value,
            )
            self.db_session.add(db_gap)
            self.db_session.commit()
        except Exception as e:
            print(f"Failed to persist structural gap: {e}")

    def track_transformer_diff(
        self,
        prompt_embedding: List[float],
        generated_embedding: List[float],
        expected_embedding: List[float],
        generated_artifact_id: str,
        prompt_id: Optional[str] = None,
        generation_id: Optional[str] = None,
    ) -> TransformerDiff:
        """
        Track differences in transformer output against expected

        Args:
            prompt_embedding: Embedding of input prompt
            generated_embedding: Embedding of LLM output
            expected_embedding: Embedding of expected/reference
            generated_artifact_id: ID of generated artifact
            prompt_id: Reference prompt ID
            generation_id: LLM generation ID

        Returns:
            TransformerDiff record
        """
        prompt_to_gen_dist = cosine(prompt_embedding, generated_embedding)
        gen_to_expected_dist = cosine(generated_embedding, expected_embedding)

        # Determine alignment status
        if gen_to_expected_dist < 0.2:
            status = "ALIGNED"
        elif gen_to_expected_dist < 0.4:
            status = "DRIFTED"
        else:
            status = "CRITICAL_MISS"

        diff = TransformerDiff(
            diff_id=str(uuid.uuid4()),
            prompt_id=prompt_id or str(uuid.uuid4()),
            generation_id=generation_id or str(uuid.uuid4()),
            prompt_embedding=prompt_embedding,
            generated_embedding=generated_embedding,
            expected_embedding=expected_embedding,
            prompt_to_generated_distance=prompt_to_gen_dist,
            generated_to_expected_distance=gen_to_expected_dist,
            generated_artifact_id=generated_artifact_id,
            status=status,
        )

        # Persist to database
        if self.db_session:
            self._persist_transformer_diff(diff)

        return diff

    def _persist_transformer_diff(self, diff: TransformerDiff):
        """Persist transformer diff to database"""
        try:
            db_diff = TransformerDiffModel(
                diff_id=diff.diff_id,
                timestamp=diff.timestamp,
                prompt_id=diff.prompt_id,
                generation_id=diff.generation_id,
                prompt_embedding=diff.prompt_embedding,
                generated_embedding=diff.generated_embedding,
                expected_embedding=diff.expected_embedding,
                prompt_to_generated_distance=diff.prompt_to_generated_distance,
                generated_to_expected_distance=diff.generated_to_expected_distance,
                generated_artifact_id=diff.generated_artifact_id,
                status=diff.status,
            )
            self.db_session.add(db_diff)
            self.db_session.commit()
        except Exception as e:
            print(f"Failed to persist transformer diff: {e}")

    def generate_diagnostic_report(
        self,
        execution_phase: str,
        trigger_event: str,
        structural_gaps: Optional[List[StructuralGap]] = None,
    ) -> DiagnosticReport:
        """
        Generate formal diagnostic report with DTC findings

        Args:
            execution_phase: Pipeline phase (e.g., 'transformer_output')
            trigger_event: What triggered diagnosis
            structural_gaps: Detected gaps to include

        Returns:
            DiagnosticReport object
        """
        detected_dtcs = []
        dtc_details = {}
        critical_actions = []
        max_severity = DTCSeverity.LOW

        # Scan event buffer for error conditions
        for event in self.event_buffer:
            if not event.success and event.error_message:
                # Map error to potential DTCs
                if "inference" in event.error_message.lower():
                    dtc_code = "T01-01"  # LLM_INFERENCE_FAILURE
                elif "parse" in event.error_message.lower():
                    dtc_code = "I01-01"  # INTENT_PARSING_FAILURE
                elif "persist" in event.error_message.lower():
                    dtc_code = "O01-01"  # ARTIFACT_PERSISTENCE_FAILURE
                else:
                    continue

                if dtc_code not in detected_dtcs:
                    detected_dtcs.append(dtc_code)
                    dtc_info = DTC_CATALOG.get(dtc_code)
                    if dtc_info:
                        dtc_details[dtc_code] = {
                            "name": dtc_info.name,
                            "severity": dtc_info.severity.value,
                            "remediation": dtc_info.remediation,
                        }
                        if dtc_info.severity.value == DTCSeverity.CRITICAL.value:
                            critical_actions.append(dtc_info.remediation)

        # Include structural gaps
        gaps = structural_gaps or []
        for gap in gaps:
            if gap.related_dtc and gap.related_dtc not in detected_dtcs:
                detected_dtcs.append(gap.related_dtc)

        # Calculate divergence points in embedding trajectory
        vector_divergence_points = []
        if len(self.embedding_trajectory) > 1:
            for i in range(len(self.embedding_trajectory) - 1):
                comp1, vec1 = self.embedding_trajectory[i]
                comp2, vec2 = self.embedding_trajectory[i + 1]
                dist = cosine(vec1, vec2)
                if dist > 0.3:  # Significant divergence threshold
                    vector_divergence_points.append(
                        {
                            "from": comp1,
                            "to": comp2,
                            "distance": dist,
                        }
                    )

        # Determine max severity
        for dtc_code in detected_dtcs:
            if dtc_code in DTC_CATALOG:
                dtc = DTC_CATALOG[dtc_code]
                if dtc.severity == DTCSeverity.CRITICAL:
                    max_severity = DTCSeverity.CRITICAL
                elif dtc.severity == DTCSeverity.HIGH and max_severity != DTCSeverity.CRITICAL:
                    max_severity = DTCSeverity.HIGH
                elif dtc.severity == DTCSeverity.MEDIUM and max_severity == DTCSeverity.LOW:
                    max_severity = DTCSeverity.MEDIUM

        # Build recommendations
        recommendations = []
        for dtc_code in detected_dtcs:
            if dtc_code in DTC_CATALOG:
                recommendations.append(DTC_CATALOG[dtc_code].remediation)

        # Create summary
        summary = (
            f"Diagnostic report for {execution_phase}: {len(detected_dtcs)} DTCs detected, "
            f"{len(gaps)} structural gaps, {len(vector_divergence_points)} divergence points"
        )

        report = DiagnosticReport(
            report_id=str(uuid.uuid4()),
            execution_phase=execution_phase,
            trigger_event=trigger_event,
            detected_dtcs=detected_dtcs,
            dtc_details=dtc_details,
            structural_gaps=gaps,
            embedding_trajectory=self.embedding_trajectory,
            vector_divergence_points=vector_divergence_points,
            recommendations=recommendations,
            critical_actions=critical_actions,
            max_severity=max_severity,
            summary=summary,
        )

        # Persist to database
        if self.db_session:
            self._persist_diagnostic_report(report)

        return report

    def _persist_diagnostic_report(self, report: DiagnosticReport):
        """Persist diagnostic report to database"""
        try:
            db_report = DiagnosticReportModel(
                report_id=report.report_id,
                timestamp=report.timestamp,
                execution_phase=report.execution_phase,
                trigger_event=report.trigger_event,
                detected_dtcs=report.detected_dtcs,
                dtc_details=report.dtc_details,
                embedding_trajectory=report.embedding_trajectory,
                vector_divergence_points=report.vector_divergence_points,
                recommendations=report.recommendations,
                critical_actions=report.critical_actions,
                max_severity=report.max_severity.value,
                summary=report.summary,
                structural_gaps_count=len(report.structural_gaps),
            )
            self.db_session.add(db_report)
            self.db_session.commit()
        except Exception as e:
            print(f"Failed to persist diagnostic report: {e}")

    def create_dmn_token(
        self,
        loose_thread_id: str,
        vector: List[float],
        problem_statement: str,
        context_artifacts: List[str],
        constraints: List[Dict[str, Any]],
        decision_criteria_input: Optional[Dict[str, float]] = None,
    ) -> DMNToken:
        """
        Create a DMN token for decision model consumption

        Args:
            loose_thread_id: Reference to unresolved issue
            vector: 768-dim embedding
            problem_statement: Description of the problem
            context_artifacts: Related artifact IDs
            constraints: List of constraint violations
            decision_criteria_input: Judge criteria values

        Returns:
            DMNToken object
        """
        token = DMNToken(
            token_id=str(uuid.uuid4()),
            loose_thread_id=loose_thread_id,
            vector=vector,
            problem_statement=problem_statement,
            context_artifacts=context_artifacts,
            constraints=[
                {
                    "constraint_id": str(uuid.uuid4()),
                    "name": c.get("name", ""),
                    "violated_by_dtc": c.get("dtc", ""),
                    "severity": c.get("severity", "medium"),
                }
                for c in constraints
            ],
            decision_criteria_input=decision_criteria_input
            or {
                "SAFETY": 0.0,
                "SPEC_ALIGNMENT": 0.0,
                "PLAYER_INTENT": 0.0,
                "LATENCY": 0.0,
            },
        )

        # Persist to database
        if self.db_session:
            self._persist_dmn_token(token)

        return token

    def _persist_dmn_token(self, token: DMNToken):
        """Persist DMN token to database"""
        try:
            db_token = DMNTokenModel(
                token_id=token.token_id,
                loose_thread_id=token.loose_thread_id,
                vector=token.vector,
                problem_statement=token.problem_statement,
                context_artifacts=token.context_artifacts,
                constraints_json=[c.dict() if hasattr(c, 'dict') else c for c in token.constraints],
                decision_criteria_input=token.decision_criteria_input,
                expected_decision_score=token.expected_decision_score,
            )
            self.db_session.add(db_token)
            self.db_session.commit()
        except Exception as e:
            print(f"Failed to persist DMN token: {e}")

    def clear_buffer(self):
        """Clear event buffer and embedding trajectory"""
        self.event_buffer.clear()
        self.embedding_trajectory.clear()


# Global telemetry instance
_telemetry_service: Optional[TelemetryService] = None


def init_telemetry(db_session=None) -> TelemetryService:
    """Initialize global telemetry service"""
    global _telemetry_service
    _telemetry_service = TelemetryService(db_session)
    return _telemetry_service


def get_telemetry() -> TelemetryService:
    """Get global telemetry service instance"""
    if _telemetry_service is None:
        raise RuntimeError("Telemetry service not initialized. Call init_telemetry() first.")
    return _telemetry_service
