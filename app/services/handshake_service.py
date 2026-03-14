"""Stateful A2A/MCP handshake orchestration service."""

from __future__ import annotations

<<<<<<< HEAD
from datetime import datetime, timezone
=======
from datetime import datetime, timedelta, timezone
>>>>>>> origin/main
import hashlib
import json
import threading
import uuid
from typing import Any, Sequence

try:
    from core_orchestrator.world_model import normalized_dot_product, normalize_vector
except Exception:  # pragma: no cover - fallback for constrained runtimes
    import math

    def normalize_vector(vector: Sequence[float]) -> tuple[float, ...]:
        if not vector:
            raise ValueError("vector must not be empty")
        norm = math.sqrt(sum(float(value) * float(value) for value in vector))
        if norm <= 0.0:
            raise ValueError("vector norm must be positive")
        return tuple(float(value) / norm for value in vector)

    def normalized_dot_product(lhs: Sequence[float], rhs: Sequence[float]) -> float:
        if len(lhs) != len(rhs):
            raise ValueError("vectors must have equal dimensions")
        left = normalize_vector(lhs)
        right = normalize_vector(rhs)
        return sum(a * b for a, b in zip(left, right))

from app.services.auth_broker import A2AAuthBroker, AuthBrokerError
from schemas.handshake import A2AHandshakeEnvelope


DEFAULT_CAPABILITIES = [
    "a2a",
    "agent",
    "gemini",
    "github-actions",
    "mcp",
    "oauth",
    "rbac",
    "wasm",
    "world-model",
]


def _now_iso() -> str:
<<<<<<< HEAD
    return datetime.now(timezone.utc).isoformat()
=======
    return _utc_now().isoformat()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
>>>>>>> origin/main


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _deterministic_vector(tokens: Sequence[str], *, dimensions: int = 16) -> tuple[float, ...]:
    raw = [0.0] * dimensions
    normalized = sorted(set(token.strip().lower() for token in tokens if token.strip()))
    if not normalized:
        normalized = ["empty"]
    for token in normalized:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = -1.0 if digest[4] % 2 else 1.0
        magnitude = 1.0 + (digest[5] / 255.0)
        raw[index] += sign * magnitude
    return normalize_vector(raw)


class A2AHandshakeService:
    """In-memory handshake lifecycle manager."""

    def __init__(self, *, broker: A2AAuthBroker | None = None) -> None:
        self._broker = broker or A2AAuthBroker()
        self._handshakes: dict[str, A2AHandshakeEnvelope] = {}
<<<<<<< HEAD
        self._volatile_tokens: dict[str, dict[str, str]] = {}
=======
        self._volatile_tokens: dict[str, dict[str, Any]] = {}
>>>>>>> origin/main
        self._lock = threading.RLock()

    def init_handshake(
        self,
        *,
        tenant_id: str,
        client_id: str,
        avatar_id: str,
        capabilities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> A2AHandshakeEnvelope:
        handshake_id = f"hs-{uuid.uuid4().hex[:16]}"
        envelope = A2AHandshakeEnvelope(
            handshake_id=handshake_id,
            tenant_id=tenant_id or "default",
            client_id=client_id,
            avatar_id=avatar_id,
            status="initialized",
            capabilities=sorted(set(capabilities or DEFAULT_CAPABILITIES)),
            metadata=metadata or {},
        )
        with self._lock:
            self._handshakes[handshake_id] = envelope
        return envelope

    def exchange_handshake(
        self,
        *,
        handshake_id: str,
        requested_scopes: list[str],
        requested_tools: list[str],
        ttl_seconds: int = 900,
        metadata: dict[str, Any] | None = None,
    ) -> A2AHandshakeEnvelope:
        with self._lock:
            envelope = self._handshakes.get(handshake_id)
            if envelope is None:
                raise KeyError(f"Unknown handshake_id: {handshake_id}")

        auth_result = self._broker.exchange(
            tenant_id=envelope.tenant_id,
            client_id=envelope.client_id,
            avatar_id=envelope.avatar_id,
            requested_scopes=requested_scopes,
            requested_tools=requested_tools,
            ttl_seconds=ttl_seconds,
        )
        proposal = auth_result["claim_proposal"]
        capability_scores = self._score_capabilities(
            capabilities=envelope.capabilities,
            scopes=proposal.scopes,
            tools=proposal.tools,
            roles=proposal.roles,
        )
        world_model_hash = _sha256_text(
            json.dumps(
                {
                    "handshake_id": handshake_id,
                    "tenant_id": envelope.tenant_id,
                    "client_id": envelope.client_id,
                    "avatar_id": envelope.avatar_id,
                    "capability_scores": capability_scores,
                    "proposal": proposal.model_dump(mode="json"),
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
        )

        updated = envelope.model_copy(
            update={
                "status": "exchanged",
                "claim_proposal": proposal,
                "rbac_token_ref": auth_result["rbac_token_ref"],
                "rbac_token_fingerprint": auth_result["rbac_token_fingerprint"],
                "gemini_token_ref": auth_result["gemini_token_ref"],
                "gemini_token_fingerprint": auth_result["gemini_token_fingerprint"],
                "world_model_hash": world_model_hash,
                "capability_scores": capability_scores,
                "metadata": {**envelope.metadata, **(metadata or {})},
                "updated_at": _now_iso(),
            }
        )
        with self._lock:
            self._handshakes[handshake_id] = updated
<<<<<<< HEAD
            self._volatile_tokens[handshake_id] = {
                "rbac_access_token": auth_result["rbac_access_token"],
                "gemini_access_token": auth_result["gemini_access_token"],
=======
            issued_at = _utc_now()
            proposal_ttl_seconds = max(int(proposal.ttl_seconds), 0)
            gemini_expires_in = max(int(auth_result.get("gemini_expires_in", 0)), 0)
            self._volatile_tokens[handshake_id] = {
                "rbac_access_token": auth_result["rbac_access_token"],
                "gemini_access_token": auth_result["gemini_access_token"],
                "issued_at": issued_at,
                "rbac_expires_at": issued_at + timedelta(seconds=proposal_ttl_seconds),
                "gemini_expires_at": issued_at + timedelta(seconds=gemini_expires_in),
>>>>>>> origin/main
            }
        return updated

    def finalize_handshake(self, *, handshake_id: str, metadata: dict[str, Any] | None = None) -> A2AHandshakeEnvelope:
        with self._lock:
            envelope = self._handshakes.get(handshake_id)
            if envelope is None:
                raise KeyError(f"Unknown handshake_id: {handshake_id}")
            if envelope.status not in {"exchanged", "finalized"}:
                raise AuthBrokerError("Handshake must be exchanged before finalization")
            updated = envelope.model_copy(
                update={
                    "status": "finalized",
                    "metadata": {**envelope.metadata, **(metadata or {})},
                    "updated_at": _now_iso(),
                }
            )
            self._handshakes[handshake_id] = updated
<<<<<<< HEAD
=======
            self._volatile_tokens.pop(handshake_id, None)
>>>>>>> origin/main
            return updated

    def get_handshake(self, handshake_id: str) -> A2AHandshakeEnvelope:
        with self._lock:
            envelope = self._handshakes.get(handshake_id)
            if envelope is None:
                raise KeyError(f"Unknown handshake_id: {handshake_id}")
            return envelope

    def get_runtime_tokens(self, handshake_id: str) -> dict[str, str]:
        """Return volatile runtime tokens (never persisted in envelope artifacts)."""

        with self._lock:
<<<<<<< HEAD
            return dict(self._volatile_tokens.get(handshake_id, {}))
=======
            envelope = self._handshakes.get(handshake_id)
            if envelope is None or envelope.status == "finalized":
                self._volatile_tokens.pop(handshake_id, None)
                return {}

            token_bundle = self._volatile_tokens.get(handshake_id)
            if token_bundle is None:
                return {}

            now = _utc_now()
            rbac_expires_at = token_bundle.get("rbac_expires_at")
            gemini_expires_at = token_bundle.get("gemini_expires_at")
            rbac_expired = isinstance(rbac_expires_at, datetime) and now >= rbac_expires_at
            gemini_expired = isinstance(gemini_expires_at, datetime) and now >= gemini_expires_at
            if rbac_expired or gemini_expired:
                self._volatile_tokens.pop(handshake_id, None)
                return {}

            return {
                "rbac_access_token": str(token_bundle["rbac_access_token"]),
                "gemini_access_token": str(token_bundle["gemini_access_token"]),
            }
>>>>>>> origin/main

    @staticmethod
    def _score_capabilities(
        *,
        capabilities: Sequence[str],
        scopes: Sequence[str],
        tools: Sequence[str],
        roles: Sequence[str],
    ) -> dict[str, float]:
        query_tokens = list(scopes) + list(tools) + list(roles)
        query_vector = _deterministic_vector(query_tokens)
        scores: dict[str, float] = {}
        for capability in sorted(set(capabilities)):
            cap_vector = _deterministic_vector([capability])
            scores[capability] = round(normalized_dot_product(query_vector, cap_vector), 8)
        return scores
<<<<<<< HEAD

=======
>>>>>>> origin/main
