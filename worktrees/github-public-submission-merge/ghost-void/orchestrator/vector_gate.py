"""Vector token retrieval and gating for model context injection."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Set

from schemas.world_model import WorldModel


@dataclass
class VectorMatch:
    """A single semantic match between query and a world-model token."""

    token_id: str
    source_artifact_id: str
    score: float
    text: str


@dataclass
class VectorGateDecision:
    """Gate output for a single pipeline breakpoint."""

    node: str
    is_open: bool
    query: str
    threshold: float
    top_score: float = 0.0
    matches: List[VectorMatch] = field(default_factory=list)
    active_tokens: int = 0
    pruned_tokens: int = 0
    merkle_root: str = ""
    merkle_leaf_count: int = 0


class VectorGate:
    """Deterministic semantic retrieval over PINN WorldModel tokens."""

    def __init__(
        self,
        min_similarity: float = 0.20,
        top_k: int = 3,
        max_token_age_seconds: int | None = 60 * 60 * 24 * 30,
        prune_dead_branches: bool = True,
        orphan_grace_seconds: int = 300,
    ) -> None:
        self.min_similarity = float(min_similarity)
        self.top_k = int(top_k)
        self.max_token_age_seconds = (
            None if max_token_age_seconds is None else int(max_token_age_seconds)
        )
        self.prune_dead_branches = bool(prune_dead_branches)
        self.orphan_grace_seconds = max(0, int(orphan_grace_seconds))

    def evaluate(self, *, node: str, query: str, world_model: WorldModel) -> VectorGateDecision:
        """Evaluate retrieval and return a gate decision for a node."""
        all_tokens = list(world_model.vector_tokens.values())
        active_tokens = self._prune_tokens(
            all_tokens,
            knowledge_graph=world_model.knowledge_graph,
        )
        pruned_count = len(all_tokens) - len(active_tokens)
        merkle_root, leaf_count = self._build_merkle_root(active_tokens)
        if not active_tokens:
            return VectorGateDecision(
                node=node,
                is_open=False,
                query=query,
                threshold=self.min_similarity,
                active_tokens=0,
                pruned_tokens=pruned_count,
                merkle_root=merkle_root,
                merkle_leaf_count=leaf_count,
            )

        dimensions = len(active_tokens[0].vector)
        query_vector = self._deterministic_embedding(query, dimensions=dimensions)

        matches: List[VectorMatch] = []
        for token in active_tokens:
            if len(token.vector) != dimensions:
                # Skip malformed or incompatible vectors rather than breaking execution.
                continue
            score = self._cosine_similarity(query_vector, token.vector)
            matches.append(
                VectorMatch(
                    token_id=token.token_id,
                    source_artifact_id=token.source_artifact_id,
                    score=score,
                    text=token.text,
                )
            )

        matches.sort(key=lambda m: m.score, reverse=True)
        top_matches = matches[: self.top_k]
        top_score = top_matches[0].score if top_matches else 0.0

        return VectorGateDecision(
            node=node,
            is_open=bool(top_matches) and top_score >= self.min_similarity,
            query=query,
            threshold=self.min_similarity,
            top_score=top_score,
            matches=top_matches,
            active_tokens=len(active_tokens),
            pruned_tokens=pruned_count,
            merkle_root=merkle_root,
            merkle_leaf_count=leaf_count,
        )

    def build_retrieval_prompt(
        self,
        decision: VectorGateDecision,
        max_chars: int = 1200,
        include_tensor_model: bool = True,
    ) -> str:
        """Build retrieval prompt text enriched with Merkle and tensor metadata."""
        state = "OPEN" if decision.is_open else "CLOSED"
        lines = [
            (
                f"[VECTOR_GATE node={decision.node} state={state} "
                f"threshold={decision.threshold:.2f} top_score={decision.top_score:.3f}]"
            ),
            (
                f"[MERKLE_ROOT root={decision.merkle_root[:16]} "
                f"leaf_count={decision.merkle_leaf_count} active={decision.active_tokens} "
                f"pruned={decision.pruned_tokens}]"
            ),
        ]
        if include_tensor_model:
            lines.append(
                r"Tensor Elasticity Proxy: $E=\sigma/\epsilon\approx\Delta relevance/\Delta context$"
            )

        if not decision.matches:
            lines.append("No vector tokens available.")
            return "\n".join(lines)

        remaining = max_chars - sum(len(line) for line in lines)
        for idx, match in enumerate(decision.matches, start=1):
            snippet = " ".join(match.text.split())
            if len(snippet) > 220:
                snippet = snippet[:217] + "..."

            line = (
                f"{idx}. score={match.score:.3f} "
                f"token={match.token_id} source={match.source_artifact_id} "
                f"text={snippet}"
            )
            if len(line) > remaining:
                break
            lines.append(line)
            remaining -= len(line)

        return "\n".join(lines)

    def format_prompt_context(self, decision: VectorGateDecision, max_chars: int = 1200) -> str:
        """Backward-compatible alias for retrieval prompt formatting."""
        return self.build_retrieval_prompt(decision=decision, max_chars=max_chars)

    @staticmethod
    def _deterministic_embedding(text: str, dimensions: int = 16) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: List[float] = []
        for i in range(dimensions):
            byte = digest[i % len(digest)]
            values.append((byte / 255.0) * 2.0 - 1.0)
        return values

    @staticmethod
    def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _prune_tokens(self, tokens: Sequence[object], knowledge_graph: Dict[str, List[str]]) -> List[object]:
        connected_artifacts = self._connected_artifacts(knowledge_graph)
        now = datetime.now(timezone.utc)
        active_tokens: List[object] = []

        for token in tokens:
            if not self._is_valid_token(token):
                continue
            if self._is_stale(token, now):
                continue
            if self._is_dead_branch(token, connected_artifacts, now):
                continue
            active_tokens.append(token)

        active_tokens.sort(key=lambda token: str(getattr(token, "token_id", "")))
        return active_tokens

    @staticmethod
    def _is_valid_token(token: object) -> bool:
        vector = getattr(token, "vector", None)
        text = str(getattr(token, "text", "")).strip()
        token_id = str(getattr(token, "token_id", "")).strip()
        source = str(getattr(token, "source_artifact_id", "")).strip()

        if not token_id or not source or not text:
            return False
        if not isinstance(vector, list) or not vector:
            return False
        for value in vector:
            if not isinstance(value, (int, float)):
                return False
            if not math.isfinite(float(value)):
                return False
        return True

    def _is_stale(self, token: object, now: datetime) -> bool:
        if self.max_token_age_seconds is None:
            return False
        age_seconds = self._token_age_seconds(token, now)
        return age_seconds > self.max_token_age_seconds

    def _is_dead_branch(
        self,
        token: object,
        connected_artifacts: Set[str],
        now: datetime,
    ) -> bool:
        if not self.prune_dead_branches or not connected_artifacts:
            return False
        source_artifact_id = str(getattr(token, "source_artifact_id", "")).strip()
        if source_artifact_id in connected_artifacts:
            return False
        return self._token_age_seconds(token, now) > self.orphan_grace_seconds

    @staticmethod
    def _connected_artifacts(knowledge_graph: Dict[str, List[str]]) -> Set[str]:
        connected: Set[str] = set()
        for source, targets in knowledge_graph.items():
            connected.add(str(source))
            for target in targets:
                connected.add(str(target))
        return connected

    @staticmethod
    def _token_age_seconds(token: object, now: datetime) -> float:
        timestamp = getattr(token, "timestamp", None)
        if not isinstance(timestamp, datetime):
            return 0.0
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return max(0.0, (now - timestamp).total_seconds())

    def _build_merkle_root(self, tokens: Sequence[object]) -> tuple[str, int]:
        leaves: List[str] = []
        for token in tokens:
            timestamp = getattr(token, "timestamp", None)
            if isinstance(timestamp, datetime):
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                ts = timestamp.isoformat()
            else:
                ts = ""

            payload = {
                "token_id": str(getattr(token, "token_id", "")),
                "source_artifact_id": str(getattr(token, "source_artifact_id", "")),
                "text": " ".join(str(getattr(token, "text", "")).split()),
                "vector": [round(float(v), 8) for v in list(getattr(token, "vector", []))],
                "timestamp": ts,
            }
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            leaves.append(hashlib.sha256(canonical.encode("utf-8")).hexdigest())

        if not leaves:
            return hashlib.sha256(b"empty").hexdigest(), 0

        level = leaves
        while len(level) > 1:
            if len(level) % 2:
                level = [*level, level[-1]]
            next_level: List[str] = []
            for idx in range(0, len(level), 2):
                combined = f"{level[idx]}{level[idx + 1]}"
                next_level.append(hashlib.sha256(combined.encode("utf-8")).hexdigest())
            level = next_level

        return level[0], len(leaves)
