# adaptco/pipeline.py
"""
AdaptcoPipeline — end-to-end wrapper that chains the normalised
dot-product CI/CD gate with the core-orchestrator's agent swarm.

Flow::

    raw vectors ─► IngressNormalizer (L2 + cosine gate)
                        ↓
               OrchestrationAgent  (bundle task list)
                        ↓
                  ManagingAgent     (LLM categorisation)
                        ↓
               IntentEngine.run_full_pipeline()
                  CoderAgent ⟷ TesterAgent (self-healing)
                        ↓
                  AdaptcoResult
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from adaptco.config import AdaptcoConfig, DEFAULT_CONFIG
from adaptco.normalizer import IngressNormalizer, NormalizedEntry

from agents.managing_agent import ManagingAgent
from agents.orchestration_agent import OrchestrationAgent
from orchestrator.intent_engine import IntentEngine, PipelineResult
from schemas.agent_artifacts import MCPArtifact
from schemas.project_plan import ProjectPlan


@dataclass
class AdaptcoResult:
    """Typed output of a full ADAPTCO pipeline run."""

    # Normalizer outputs
    normalized_entries: List[NormalizedEntry] = field(default_factory=list)
    rejected_entries: List[NormalizedEntry] = field(default_factory=list)

    # Orchestrator outputs
    blueprint: ProjectPlan | None = None

    # Full pipeline result (from IntentEngine)
    pipeline_result: PipelineResult | None = None

    # Top-level success flag
    success: bool = False
    gate_open: bool = True  # False when all vectors were rejected


class AdaptcoPipeline:
    """
    Top-level entry point for ADAPTCO's normalised agent pipeline.

    Usage::

        pipeline = AdaptcoPipeline()
        result = await pipeline.run(
            description="Build a user service",
            ingress_vectors=[("task-1", [0.1, 0.2, ...])],
        )
    """

    def __init__(self, config: AdaptcoConfig | None = None) -> None:
        self.config = config or DEFAULT_CONFIG
        self.normalizer = IngressNormalizer(self.config)
        self.orchestrator = OrchestrationAgent()
        self.manager = ManagingAgent()
        self.engine = IntentEngine()

    async def run(
        self,
        description: str,
        ingress_vectors: List[Tuple[str, Sequence[float]]],
        reference_vector: Sequence[float] | None = None,
    ) -> AdaptcoResult:
        """
        End-to-end pipeline:

        1. **Normalize** — L2-normalise ingress vectors and apply cosine gate.
        2. **Bundle** — Pass qualifying task labels to the OrchestrationAgent.
        3. **Categorise** — ManagingAgent decomposes the description via LLM.
        4. **Execute** — IntentEngine runs the full 5-agent pipeline.
        """
        result = AdaptcoResult()

        # ── Stage 1: Normalise + Gate ───────────────────────────────
        all_entries = self.normalizer.normalize_and_gate(
            ingress_vectors, reference_vector
        )
        result.normalized_entries = [e for e in all_entries if e.passed_gate]
        result.rejected_entries = [e for e in all_entries if not e.passed_gate]

        if not result.normalized_entries:
            result.gate_open = False
            result.success = False
            return result

        # ── Stage 2: OrchestrationAgent bundles the task list ───────
        task_labels = [e.label for e in result.normalized_entries]
        blueprint = await self.orchestrator.build_blueprint(
            project_name=description[:80],
            task_descriptions=task_labels,
            requester=self.config.requester,
        )
        result.blueprint = blueprint

        # ── Stage 3 + 4: ManagingAgent → IntentEngine full pipeline ─
        pipeline_result = await self.engine.run_full_pipeline(
            description=description,
            requester=self.config.requester,
            max_healing_retries=self.config.max_healing_retries,
        )
        result.pipeline_result = pipeline_result
        result.success = pipeline_result.success

        return result
