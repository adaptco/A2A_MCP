"""
Diagnostic Telemetry Schema for A2A-MCP
========================================
Defines DTC (Diagnostic Trouble Codes), telemetry events, and diagnostic reports
for tracking structural gaps, embedding diffs, and formal diagnostics across the system.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# DTC (Diagnostic Trouble Code) Definitions
# ============================================================================

class DTCCategory(str, Enum):
    """DTC Categories - Based on automotive DTC structure"""
    TRANSFORMER = "T"          # Transformer/CoderAgent issues
    INTENT_ENGINE = "I"        # IntentEngine structural issues
    JUDGE = "J"                # Judge/Decision Agent issues
    EMBEDDING = "E"            # Embedding/Vector store issues
    ORCHESTRATOR = "O"         # Orchestrator/pipeline issues
    PINN_WORLD = "W"           # PINN/WorldModel issues
    AGENT = "A"                # Agent execution issues


class DTCSeverity(str, Enum):
    """DTC Severity Levels"""
    CRITICAL = "critical"      # System must halt
    HIGH = "high"              # Major path blocked
    MEDIUM = "medium"          # Degraded performance
    LOW = "low"                # Minor issue, operational


class DTC(BaseModel):
    """Diagnostic Trouble Code - A formal fault identifier"""
    code: str = Field(..., description="DTC code format: [Category][Subsystem][Fault] e.g., T01-01")
    name: str = Field(..., description="Human-readable fault name")
    description: str = Field(..., description="Detailed description of the fault")
    severity: DTCSeverity = Field(..., description="Fault severity level")
    remediation: str = Field(..., description="Recommended remediation steps")
    vector_signature: Optional[List[float]] = Field(default=None, description="Embedding vector for semantic matching")
    references: List[str] = Field(default_factory=list, description="Related component references")


# ============================================================================
# DTC Catalog - Formal Fault Library
# ============================================================================

DTC_CATALOG = {
    # Transformer/CoderAgent DTCs
    "T01-01": DTC(
        code="T01-01",
        name="LLM_INFERENCE_FAILURE",
        description="Transformer (LLMService) failed to generate code response",
        severity=DTCSeverity.CRITICAL,
        remediation="Check API endpoint connectivity, verify API key, review prompt context",
        references=["orchestrator/llm_util.py", "agents/coder.py"]
    ),
    "T01-02": DTC(
        code="T01-02",
        name="CODE_GENERATION_SYNTAX_ERROR",
        description="Generated code contains syntax errors not caught by parser",
        severity=DTCSeverity.HIGH,
        remediation="Enhance prompt with syntax constraints, enable pre-validation parsing",
        references=["agents/coder.py:generate_solution()"]
    ),
    "T01-03": DTC(
        code="T01-03",
        name="TRANSFORMER_EMBEDDING_MISMATCH",
        description="Input embedding vector dimension mismatch with transformer expectations",
        severity=DTCSeverity.MEDIUM,
        remediation="Verify embedding dimension (768), check normalization, rebuild vectors",
        references=["pipeline/embed_worker/worker.py"]
    ),

    # IntentEngine DTCs
    "I01-01": DTC(
        code="I01-01",
        name="INTENT_PARSING_FAILURE",
        description="IntentEngine failed to parse user intent into actionable plan",
        severity=DTCSeverity.HIGH,
        remediation="Review intent statement clarity, enhance NLP preprocessing",
        references=["orchestrator/intent_engine.py:parse_intent()"]
    ),
    "I01-02": DTC(
        code="I01-02",
        name="PIPELINE_STATE_CORRUPTION",
        description="State machine detected inconsistent state transitions",
        severity=DTCSeverity.CRITICAL,
        remediation="Reload state from database, verify atomic operations in stateflow",
        references=["orchestrator/stateflow.py"]
    ),
    "I01-03": DTC(
        code="I01-03",
        name="STRUCTURAL_GAP_DETECTED",
        description="Structural gap found between IntentEngine and downstream agent",
        severity=DTCSeverity.MEDIUM,
        remediation="Verify artifact schema compatibility, check interface contracts",
        references=["orchestrator/intent_engine.py"]
    ),

    # Judge/Decision Agent DTCs
    "J01-01": DTC(
        code="J01-01",
        name="JUDGMENT_CRITERIA_WEIGHT_INVALID",
        description="MCDA weights do not sum to valid constraint (0-1 range)",
        severity=DTCSeverity.HIGH,
        remediation="Recalibrate MCDA weights in JudgmentModel, verify normalization",
        references=["judge/decision.py:JudgmentModel"]
    ),
    "J01-02": DTC(
        code="J01-02",
        name="DECISION_TIMEOUT",
        description="Judge decision evaluation exceeded max time threshold",
        severity=DTCSeverity.MEDIUM,
        remediation="Optimize MCDA evaluation, cache criteria weights, parallelize scoring",
        references=["judge/decision.py:evaluate_criteria()"]
    ),
    "J01-03": DTC(
        code="J01-03",
        name="CONFLICTING_OBJECTIVES",
        description="Multiple judge objectives are in conflict (zero-sum trade-off)",
        severity=DTCSeverity.LOW,
        remediation="Adjust priority weighting, introduce objective hierarchies",
        references=["judge/decision.py"]
    ),

    # Embedding/Vector Store DTCs
    "E01-01": DTC(
        code="E01-01",
        name="EMBEDDING_GENERATION_FAILED",
        description="Embed worker failed to generate vector embeddings for chunk",
        severity=DTCSeverity.HIGH,
        remediation="Check CUDA availability, verify model loading, review chunk size",
        references=["pipeline/embed_worker/worker.py"]
    ),
    "E01-02": DTC(
        code="E01-02",
        name="QDRANT_CONNECTION_LOST",
        description="Vector store (Qdrant) connection failure",
        severity=DTCSeverity.CRITICAL,
        remediation="Verify Qdrant service is running, check network connectivity, restart container",
        references=["pipeline/embed_worker/worker.py", "docker-compose.yml"]
    ),
    "E01-03": DTC(
        code="E01-03",
        name="VECTOR_NORMALIZATION_DRIFT",
        description="Vector L2 norm outside expected range, possible dimensionality collapse",
        severity=DTCSeverity.MEDIUM,
        remediation="Re-normalize vectors to unit norm, check embedding model output",
        references=["pipeline/embed_worker/worker.py"]
    ),

    # Orchestrator DTCs
    "O01-01": DTC(
        code="O01-01",
        name="ARTIFACT_PERSISTENCE_FAILURE",
        description="Failed to persist artifact to database",
        severity=DTCSeverity.HIGH,
        remediation="Check PostgreSQL connection, verify schema, review transaction logs",
        references=["orchestrator/storage.py:save_artifact()"]
    ),
    "O01-02": DTC(
        code="O01-02",
        name="AGENT_DISPATCH_DEADLOCK",
        description="Agent pipeline blocked waiting for upstream response",
        severity=DTCSeverity.CRITICAL,
        remediation="Review agent state machines, check for circular dependencies, reset pipeline",
        references=["orchestrator/intent_engine.py:run_full_pipeline()"]
    ),
    "O01-03": DTC(
        code="O01-03",
        name="HEALING_LOOP_EXHAUSTED",
        description="Self-healing retry loop reached max attempts without resolution",
        severity=DTCSeverity.HIGH,
        remediation="Escalate to manual review, collect diagnostics dump, increase retry threshold",
        references=["orchestrator/intent_engine.py:run_healing_loop()"]
    ),

    # PINN/WorldModel DTCs
    "W01-01": DTC(
        code="W01-01",
        name="WORLD_MODEL_KNOWLEDGE_GRAPH_CORRUPTION",
        description="Knowledge graph edges are invalid or malformed",
        severity=DTCSeverity.MEDIUM,
        remediation="Rebuild knowledge graph from artifact trace, verify link operations",
        references=["agents/pinn_agent.py", "schemas/world_model.py"]
    ),
    "W01-02": DTC(
        code="W01-02",
        name="VECTOR_TOKEN_COLLISION",
        description="Multiple artifacts mapping to same semantic token ID",
        severity=DTCSeverity.HIGH,
        remediation="Verify token ID generation (UUID uniqueness), rebuild token index",
        references=["agents/pinn_agent.py:ingest_artifact()"]
    ),

    # Agent Execution DTCs
    "A01-01": DTC(
        code="A01-01",
        name="AGENT_EXCEPTION_UNHANDLED",
        description="Agent raised exception not caught by orchestrator",
        severity=DTCSeverity.CRITICAL,
        remediation="Add exception handler to agent, review error handling strategy",
        references=["agents/"]
    ),
    "A01-02": DTC(
        code="A01-02",
        name="RESOURCE_EXHAUSTION",
        description="Agent exceeded memory or compute resource limits",
        severity=DTCSeverity.HIGH,
        remediation="Optimize agent logic, increase container limits, enable resource throttling",
        references=["docker-compose.yml"]
    ),
}


# ============================================================================
# Telemetry Event Schema
# ============================================================================

class TelemetryEvent(BaseModel):
    """Raw telemetry event from system execution"""
    event_id: str = Field(..., description="Unique event identifier (UUID)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    component: str = Field(..., description="Source component (e.g., 'CoderAgent', 'Judge')")
    event_type: str = Field(..., description="Event category (e.g., 'execution_start', 'inference_complete')")

    # Embedding and vector tracking
    input_embedding: Optional[List[float]] = Field(default=None, description="Input vector to component")
    output_embedding: Optional[List[float]] = Field(default=None, description="Output vector from component")
    embedding_distance: Optional[float] = Field(default=None, description="Cosine distance: ||input - output||")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    duration_ms: Optional[float] = Field(default=None, description="Execution time in milliseconds")
    success: bool = Field(default=True)
    error_message: Optional[str] = Field(default=None)


# ============================================================================
# Structural Gap Detection
# ============================================================================

class StructuralGap(BaseModel):
    """Detected gap between expected and actual artifact structures"""
    gap_id: str = Field(..., description="Unique gap identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Gap location
    source_component: str = Field(..., description="Component that produced artifact")
    target_component: str = Field(..., description="Component expecting artifact")
    artifact_type: str = Field(..., description="Type of artifact with gap")

    # Gap characteristics
    expected_schema: Dict[str, Any] = Field(..., description="Expected schema structure")
    actual_schema: Dict[str, Any] = Field(..., description="Actual schema structure")
    missing_fields: List[str] = Field(default_factory=list, description="Fields in expected but not actual")
    extra_fields: List[str] = Field(default_factory=list, description="Fields in actual but not expected")

    # Semantic gap (embedding-based)
    expected_embedding: Optional[List[float]] = Field(default=None)
    actual_embedding: Optional[List[float]] = Field(default=None)
    semantic_distance: Optional[float] = Field(default=None, description="Cosine distance in embedding space")

    # Associated DTC
    related_dtc: Optional[str] = Field(default=None, description="DTC code if applicable")
    severity: DTCSeverity = Field(default=DTCSeverity.MEDIUM)


# ============================================================================
# Diagnostic Report
# ============================================================================

class DiagnosticReport(BaseModel):
    """Formal diagnostic report with DTC findings"""
    report_id: str = Field(..., description="Unique report identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Report context
    execution_phase: str = Field(..., description="Pipeline phase during diagnosis (e.g., 'transformer_output')")
    trigger_event: str = Field(..., description="What triggered the diagnostic run")

    # DTC findings
    detected_dtcs: List[str] = Field(default_factory=list, description="List of DTC codes identified")
    dtc_details: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Detailed DTC info")

    # Structural gaps
    structural_gaps: List[StructuralGap] = Field(default_factory=list)

    # Vector analysis
    embedding_trajectory: List[tuple[str, List[float]]] = Field(
        default_factory=list,
        description="Sequence of embeddings through pipeline: [(component, vector), ...]"
    )
    vector_divergence_points: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Points where embeddings diverged significantly"
    )

    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    critical_actions: List[str] = Field(default_factory=list, description="Actions required immediately")

    # Severity summary
    max_severity: DTCSeverity = Field(default=DTCSeverity.LOW)
    summary: str = Field(default="")


class ConstraintViolation(BaseModel):
    """Constraint violation for DMN decision model"""
    constraint_id: str = Field(..., description="Constraint identifier")
    constraint_name: str = Field(..., description="Human-readable constraint name")
    violated_by_dtc: str = Field(..., description="DTC code that violates this constraint")

    # Constraint definition
    constraint_expression: str = Field(..., description="Logical expression for constraint")
    expected_outcome: str = Field(..., description="Expected outcome if satisfied")
    actual_outcome: str = Field(..., description="Actual outcome (violation evidence)")

    # Vector representation for DMN
    constraint_vector: List[float] = Field(..., description="Embedding of constraint for semantic matching")

    # Impact
    affects_objectives: List[str] = Field(default_factory=list, description="Judge objectives affected")
    severity: DTCSeverity = Field(...)


# ============================================================================
# Transformer Output Diff
# ============================================================================

class TransformerDiff(BaseModel):
    """Tracks differences in transformer (LLM) output vs expected"""
    diff_id: str = Field(..., description="Unique diff identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Context
    prompt_id: str = Field(..., description="Original prompt used")
    generation_id: str = Field(..., description="Model generation identifier")

    # Embeddings
    prompt_embedding: List[float] = Field(..., description="Embedding of prompt input")
    generated_embedding: List[float] = Field(..., description="Embedding of generated output")
    expected_embedding: List[float] = Field(..., description="Embedding of expected/reference")

    # Diff metrics
    prompt_to_generated_distance: float = Field(..., description="Cosine distance: prompt → generated")
    generated_to_expected_distance: float = Field(..., description="Cosine distance: generated → expected")

    # Artifacts
    generated_artifact_id: str = Field(...)
    status: str = Field(..., description="ALIGNED, DRIFTED, CRITICAL_MISS")


# ============================================================================
# DMN-Ready Telemetry Token
# ============================================================================

class DMNToken(BaseModel):
    """Token formatted for Decision Model and Notation (DMN) consumption"""
    token_id: str = Field(..., description="Token identifier for DMN")
    loose_thread_id: str = Field(..., description="Reference to unresolved issue")

    # Vector representation
    vector: List[float] = Field(..., description="768-dim embedding for semantic operations")

    # Problem description
    problem_statement: str = Field(...)
    context_artifacts: List[str] = Field(default_factory=list, description="Related artifact IDs")

    # Constraints extracted
    constraints: List[ConstraintViolation] = Field(default_factory=list)

    # Decision inputs
    decision_criteria_input: Dict[str, float] = Field(
        default_factory=dict,
        description="Values for each judge criterion (SAFETY, SPEC_ALIGNMENT, PLAYER_INTENT, LATENCY)"
    )

    # Expected decision output from Judge
    expected_decision_score: Optional[float] = Field(default=None, description="Judge score (0-1)")
