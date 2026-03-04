"""Runtime scenario synthesis and manifold integration services."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from drift_suite.gate import gate_drift
from frontend.three.game_engine import GameEngine
from orchestrator.settlement import Event, State, compute_lineage, verify_execution
from schemas.runtime_scenario import (
    LoRACandidate,
    ProjectionMetadata,
    RetrievalChunk,
    RetrievalContext,
    RuntimeScenarioEnvelope,
    ScenarioTraceRecord,
)


TARGET_EMBEDDING_DIM = 1536


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@lru_cache(maxsize=8)
def _projection_matrix(source_dim: int, target_dim: int) -> tuple[np.ndarray, str]:
    seed_text = f"a2a-manifold-v1:{source_dim}->{target_dim}"
    seed_hash = _sha256_text(seed_text)
    seed = int(seed_hash[:16], 16) % (2**32)
    rng = np.random.default_rng(seed)
    matrix = rng.standard_normal((target_dim, source_dim)).astype(np.float64)
    matrix /= np.clip(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-12, None)
    return matrix, seed_hash[:16]


def _deterministic_text_embedding(text: str, dim: int = TARGET_EMBEDDING_DIM) -> np.ndarray:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    embedding = np.zeros(dim, dtype=np.float64)
    for i in range(dim):
        byte = digest[i % len(digest)]
        embedding[i] = (byte / 255.0) * 2.0 - 1.0
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    return embedding


def _hash_expand_projection(vector: np.ndarray, target_dim: int) -> tuple[np.ndarray, str]:
    source = np.asarray(vector, dtype=np.float64).ravel()
    output = np.zeros(target_dim, dtype=np.float64)
    for i in range(target_dim):
        seed = _sha256_text(f"hash-expand:{source.size}:{i}")
        index = int(seed[:8], 16) % source.size
        sign = -1.0 if int(seed[8], 16) % 2 else 1.0
        output[i] = source[index] * sign
    norm = np.linalg.norm(output)
    if norm > 0:
        output = output / norm
    return output, "hash-expand-v1"


def _project_to_target(vector: np.ndarray) -> tuple[np.ndarray, ProjectionMetadata | None]:
    source = np.asarray(vector, dtype=np.float64).ravel()
    source_dim = int(source.size)
    if source_dim < 1:
        raise ValueError("Input token vector must contain at least one element.")

    if source_dim == TARGET_EMBEDDING_DIM:
        return source, None

    if source_dim in (16, 768):
        matrix, seed = _projection_matrix(source_dim, TARGET_EMBEDDING_DIM)
        projected = matrix @ source
        norm = np.linalg.norm(projected)
        if norm > 0:
            projected = projected / norm
        metadata = ProjectionMetadata(
            source_dim=source_dim,
            target_dim=TARGET_EMBEDDING_DIM,
            method="dense-seeded-projection",
            seed=seed,
        )
        return projected, metadata

    projected, method = _hash_expand_projection(source, TARGET_EMBEDDING_DIM)
    metadata = ProjectionMetadata(
        source_dim=source_dim,
        target_dim=TARGET_EMBEDDING_DIM,
        method=method,
        seed=_sha256_text(f"{source_dim}->{TARGET_EMBEDDING_DIM}")[:16],
    )
    return projected, metadata


@dataclass
class CorpusChunk:
    chunk_id: str
    text: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionRecord:
    tenant_id: str
    client_id: str
    baseline_vector: np.ndarray
    envelopes: List[RuntimeScenarioEnvelope] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    corpus: List[CorpusChunk] = field(default_factory=list)


class RuntimeScenarioService:
    """Stateful runtime integration layer for scenario, RAG, and LoRA paths."""

    def __init__(self, forensic_path: Path | None = None) -> None:
        self._lock = threading.RLock()
        self._records: dict[str, ExecutionRecord] = {}
        default_path = Path(os.getenv("A2A_FORENSIC_NDJSON", "/tmp/a2a_runtime_scenario_audit.ndjson"))
        self._forensic_path = forensic_path or default_path

    @staticmethod
    def hash_payload(prev_hash: str | None, payload: dict[str, Any]) -> str:
        """Public helper to support deterministic hash assertions in tests."""
        return compute_lineage(prev_hash, payload)

    def create_scenario(
        self,
        *,
        tenant_id: str,
        client_id: str,
        tokens: np.ndarray,
        runtime_hints: dict[str, Any] | None = None,
        execution_id: str | None = None,
    ) -> RuntimeScenarioEnvelope:
        runtime_hints = runtime_hints or {}
        execution_id = execution_id or f"exec-{uuid4().hex[:12]}"

        projected, projection_metadata = _project_to_target(np.asarray(tokens, dtype=np.float64))
        envelope = self._build_initial_envelope(
            tenant_id=tenant_id,
            execution_id=execution_id,
            manifold_vector=projected,
            runtime_hints=runtime_hints,
            projection_metadata=projection_metadata,
        )

        corpus = self._build_execution_corpus(envelope)

        with self._lock:
            record = ExecutionRecord(
                tenant_id=tenant_id,
                client_id=client_id,
                baseline_vector=projected,
                envelopes=[envelope],
                corpus=corpus,
            )
            self._records[execution_id] = record
            self._append_event_locked(
                record=record,
                execution_id=execution_id,
                state=State.RUNNING.value,
                payload={
                    "stage": "scenario_created",
                    "envelope_hash": envelope.hash_current,
                    "embedding_dim": envelope.embedding_dim,
                },
            )
            self._append_forensic_locked(envelope, event_type="scenario_created")

        return envelope

    def build_rag_context(
        self,
        *,
        execution_id: str,
        top_k: int = 5,
        query_tokens: np.ndarray | None = None,
    ) -> RuntimeScenarioEnvelope:
        with self._lock:
            record = self._records.get(execution_id)
            if record is None:
                raise KeyError(f"Unknown execution_id: {execution_id}")

            current = record.envelopes[-1]
            query_vector = (
                _project_to_target(query_tokens)[0]
                if query_tokens is not None and np.asarray(query_tokens).size > 0
                else record.baseline_vector
            )
            query_hash = _sha256_bytes(np.asarray(query_vector, dtype=np.float64).tobytes())

            ranked: list[tuple[float, CorpusChunk]] = []
            for chunk in record.corpus:
                score = float(np.dot(query_vector, chunk.embedding))
                ranked.append((score, chunk))
            ranked.sort(key=lambda item: item[0], reverse=True)

            selected = ranked[: max(1, top_k)]
            retrieval_chunks = [
                RetrievalChunk(
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    score=score,
                    embedding_hash=_sha256_bytes(np.asarray(chunk.embedding, dtype=np.float64).tobytes()),
                    metadata=chunk.metadata,
                )
                for score, chunk in selected
            ]

            retrieval_context = RetrievalContext(
                query_hash=query_hash,
                chunks=retrieval_chunks,
                provenance={
                    "source_envelope_hash": current.hash_current,
                    "retrieval_hash": _sha256_text(
                        _canonical_json(
                            {
                                "query_hash": query_hash,
                                "chunk_ids": [chunk.chunk_id for chunk in retrieval_chunks],
                                "scores": [round(chunk.score, 8) for chunk in retrieval_chunks],
                            }
                        )
                    ),
                },
            )

            next_envelope = self._derive_envelope(
                current=current,
                retrieval_context=retrieval_context,
                lora_candidates=current.lora_candidates,
            )
            record.envelopes.append(next_envelope)

            self._append_event_locked(
                record=record,
                execution_id=execution_id,
                state=State.RUNNING.value,
                payload={
                    "stage": "rag_context",
                    "envelope_hash": next_envelope.hash_current,
                    "retrieval_hash": retrieval_context.provenance.get("retrieval_hash"),
                },
            )
            self._append_forensic_locked(next_envelope, event_type="rag_context")
            return next_envelope

    def build_lora_dataset(
        self,
        *,
        execution_id: str,
        pvalue_threshold: float = 0.10,
        candidate_tokens: np.ndarray | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            record = self._records.get(execution_id)
            if record is None:
                raise KeyError(f"Unknown execution_id: {execution_id}")

            if not record.envelopes[-1].retrieval_context.chunks:
                self.build_rag_context(execution_id=execution_id, top_k=5)
                record = self._records[execution_id]

            verify_before = verify_execution(record.events)
            if not verify_before.valid:
                raise ValueError(
                    "Execution lineage is invalid; LoRA dataset export is blocked."
                )

            current = record.envelopes[-1]
            candidate_vector = (
                _project_to_target(candidate_tokens)[0]
                if candidate_tokens is not None and np.asarray(candidate_tokens).size > 0
                else record.baseline_vector
            )
            drift_result = gate_drift(
                record.baseline_vector,
                np.asarray(candidate_vector, dtype=np.float64),
                pvalue_threshold=pvalue_threshold,
            )
            if not drift_result.passed:
                raise ValueError(f"Drift gate failed: {drift_result.reason}")

            lora_candidates = self._build_lora_candidates(current)
            next_envelope = self._derive_envelope(
                current=current,
                retrieval_context=current.retrieval_context,
                lora_candidates=lora_candidates,
            )
            record.envelopes.append(next_envelope)

            dataset_payload = [candidate.model_dump(mode="json") for candidate in lora_candidates]
            dataset_commit = _sha256_text(_canonical_json({"rows": dataset_payload}))

            self._append_event_locked(
                record=record,
                execution_id=execution_id,
                state=State.FINALIZED.value,
                payload={
                    "stage": "lora_dataset",
                    "envelope_hash": next_envelope.hash_current,
                    "dataset_commit": dataset_commit,
                    "candidate_count": len(dataset_payload),
                },
            )
            self._append_forensic_locked(next_envelope, event_type="lora_dataset")

            verify_after = verify_execution(record.events)
            if not verify_after.valid:
                raise ValueError("Post-export lineage verification failed.")

            return {
                "execution_id": execution_id,
                "tenant_id": record.tenant_id,
                "dataset_commit": dataset_commit,
                "drift": {
                    "passed": drift_result.passed,
                    "reason": drift_result.reason,
                    "pvalue": drift_result.ks.pvalue,
                },
                "lora_dataset": dataset_payload,
                "envelope": next_envelope.model_dump(mode="json"),
            }

    def verify_execution(self, execution_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._records.get(execution_id)
            if record is None:
                raise KeyError(f"Unknown execution_id: {execution_id}")

            result = verify_execution(record.events)
            if not result.valid:
                return {
                    "valid": False,
                    "execution_id": execution_id,
                    "tenant_id": record.tenant_id,
                    "event_count": result.event_count,
                    "reason": result.reason,
                }

            return {
                "valid": True,
                "execution_id": execution_id,
                "tenant_id": record.tenant_id,
                "event_count": result.event_count,
                "hash_head": result.head_hash,
            }

    def _build_initial_envelope(
        self,
        *,
        tenant_id: str,
        execution_id: str,
        manifold_vector: np.ndarray,
        runtime_hints: dict[str, Any],
        projection_metadata: ProjectionMetadata | None,
    ) -> RuntimeScenarioEnvelope:
        agent_name = str(runtime_hints.get("agent_name", tenant_id))
        action = str(runtime_hints.get("action", "navigate safely"))
        preset = str(runtime_hints.get("preset", "simulation"))

        runtime_state: dict[str, Any]
        scenario_trace: list[ScenarioTraceRecord]

        try:
            engine = GameEngine(preset=preset)
            engine.initialize_player(agent_name)
            engine.update_player_state(
                agent_name=agent_name,
                speed_mph=float(runtime_hints.get("speed_mph", 35.0)),
                rotation=float(runtime_hints.get("heading_deg", 0.0)),
                fuel_gal=float(runtime_hints.get("fuel_gal", 13.2)),
            )
            action_result = engine.judge_action(agent_name, action)
            frame = engine.run_frame()
            runtime_state = frame
            scenario_trace = [
                ScenarioTraceRecord(
                    stage="runtime_seed",
                    event_type="player_initialized",
                    payload={"agent_name": agent_name, "preset": preset},
                ),
                ScenarioTraceRecord(
                    stage="scenario_synthesis",
                    event_type="action_judged",
                    payload=action_result,
                ),
            ]
        except Exception as exc:
            runtime_state = {
                "preset": preset,
                "agent_name": agent_name,
                "fallback": True,
                "error": str(exc),
            }
            scenario_trace = [
                ScenarioTraceRecord(
                    stage="scenario_synthesis",
                    event_type="fallback_state",
                    payload={"error": str(exc)},
                )
            ]

        envelope = RuntimeScenarioEnvelope(
            tenant_id=tenant_id,
            execution_id=execution_id,
            runtime_state=runtime_state,
            scenario_trace=scenario_trace,
            retrieval_context=RetrievalContext(),
            lora_candidates=[],
            embedding_dim=TARGET_EMBEDDING_DIM,
            hash_prev="",
            projection_metadata=projection_metadata,
            timestamp=_now_iso(),
        )
        envelope.hash_current = self.hash_payload(envelope.hash_prev, envelope.hash_payload())
        return envelope

    def _build_execution_corpus(self, envelope: RuntimeScenarioEnvelope) -> List[CorpusChunk]:
        trace_payload = " ".join(
            f"{record.stage}:{record.event_type}:{_canonical_json(record.payload)}"
            for record in envelope.scenario_trace
        )
        runtime_text = _canonical_json(envelope.runtime_state)
        base_texts = [
            ("chunk-runtime-state", runtime_text),
            ("chunk-scenario-trace", trace_payload),
            (
                "chunk-control-plane",
                (
                    "Use stateflow integrity checks and settlement lineage hashes "
                    "before export to retrieval or LoRA datasets."
                ),
            ),
        ]

        corpus = []
        for chunk_id, text in base_texts:
            corpus.append(
                CorpusChunk(
                    chunk_id=chunk_id,
                    text=text,
                    embedding=_deterministic_text_embedding(text),
                    metadata={"execution_id": envelope.execution_id},
                )
            )
        return corpus

    def _derive_envelope(
        self,
        *,
        current: RuntimeScenarioEnvelope,
        retrieval_context: RetrievalContext,
        lora_candidates: List[LoRACandidate],
    ) -> RuntimeScenarioEnvelope:
        next_envelope = RuntimeScenarioEnvelope(
            schema_version=current.schema_version,
            tenant_id=current.tenant_id,
            execution_id=current.execution_id,
            runtime_state=current.runtime_state,
            scenario_trace=current.scenario_trace,
            retrieval_context=retrieval_context,
            lora_candidates=lora_candidates,
            embedding_dim=current.embedding_dim,
            hash_prev=current.hash_current,
            projection_metadata=current.projection_metadata,
            timestamp=_now_iso(),
        )
        next_envelope.hash_current = self.hash_payload(
            next_envelope.hash_prev, next_envelope.hash_payload()
        )
        return next_envelope

    def _build_lora_candidates(
        self, envelope: RuntimeScenarioEnvelope
    ) -> List[LoRACandidate]:
        candidates: list[LoRACandidate] = []
        for chunk in envelope.retrieval_context.chunks:
            text = chunk.text.lower()
            if any(token in text for token in ("error", "retry", "fail", "timeout", "bug")):
                instruction = f"SYSTEM: Apply recovery logic. Context: {chunk.text}"
                output = (
                    "ACTION: Execute deterministic self-healing refinement and "
                    "re-validate against stateflow constraints."
                )
            else:
                instruction = f"SYSTEM: Improve scenario response quality. Context: {chunk.text}"
                output = (
                    "ACTION: Produce a concise plan with safety checks, acceptance "
                    "tests, and provenance-linked outputs."
                )

            provenance_hash = self.hash_payload(
                envelope.hash_current,
                {
                    "source_chunk_id": chunk.chunk_id,
                    "instruction": instruction,
                    "output": output,
                },
            )
            candidates.append(
                LoRACandidate(
                    instruction=instruction,
                    output=output,
                    source_chunk_id=chunk.chunk_id,
                    provenance_hash=provenance_hash,
                    metadata={"retrieval_score": chunk.score},
                )
            )
        return candidates

    def _append_event_locked(
        self,
        *,
        record: ExecutionRecord,
        execution_id: str,
        state: str,
        payload: dict[str, Any],
    ) -> None:
        previous = record.events[-1] if record.events else None
        event = Event(
            id=len(record.events) + 1,
            tenant_id=record.tenant_id,
            execution_id=execution_id,
            state=state,
            payload=payload,
            hash_prev=previous.hash_current if previous else None,
            hash_current=compute_lineage(previous.hash_current if previous else None, payload),
            created_at=_now_iso(),
        )
        record.events.append(event)

    def _append_forensic_locked(
        self,
        envelope: RuntimeScenarioEnvelope,
        *,
        event_type: str,
    ) -> None:
        self._forensic_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "event_type": event_type,
            "execution_id": envelope.execution_id,
            "tenant_id": envelope.tenant_id,
            "embedding_dim": envelope.embedding_dim,
            "canonicalHash": envelope.hash_current,
            "timestamp": envelope.timestamp,
        }
        with self._forensic_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
