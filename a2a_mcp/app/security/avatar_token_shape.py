"""Avatar token shaping and validation helpers for protected ingestion flows."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class AvatarTokenShapeError(ValueError):
    """Structured error raised when avatar token shaping fails."""

    code: str
    message: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


@dataclass(frozen=True)
class AvatarTokenShapeResult:
    """Shaped token payload passed to model-facing code."""

    namespace: str
    token_count: int
    tokens: list[float]
    execution_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "token_count": self.token_count,
            "tokens": self.tokens,
            "execution_hash": self.execution_hash,
        }


def shape_avatar_token_stream(
    *,
    raw_tokens: Any,
    namespace: str,
    max_tokens: int,
    fingerprint_seed: str,
) -> AvatarTokenShapeResult:
    """Validate, normalize, namespace, and fingerprint a raw token stream."""
    token_array = _coerce_token_array(raw_tokens)
    token_count = int(token_array.size)
    if token_count > max_tokens:
        raise AvatarTokenShapeError(
            code="TOKEN_STREAM_TOO_LARGE",
            message="Token stream exceeds configured maximum",
            details={"max_tokens": max_tokens, "token_count": token_count},
        )

    normalized = _normalize_embedding(token_array)
    namespaced = _namespace_embedding(namespace, normalized)
    execution_hash = _execution_hash(
        namespaced=namespaced,
        namespace=namespace,
        token_count=token_count,
        fingerprint_seed=fingerprint_seed,
    )

    return AvatarTokenShapeResult(
        namespace=namespace,
        token_count=token_count,
        tokens=namespaced.astype(float).ravel().tolist(),
        execution_hash=execution_hash,
    )


def _coerce_token_array(raw_tokens: Any) -> np.ndarray:
    if isinstance(raw_tokens, str):
        raise AvatarTokenShapeError(
            code="TOKEN_TYPE_INVALID",
            message="Token payload must be numeric and one-dimensional",
            details={"expected": "list[float]|np.ndarray", "received": "str"},
        )

    arr = np.asarray(raw_tokens, dtype=float)
    if arr.ndim != 1:
        raise AvatarTokenShapeError(
            code="TOKEN_SHAPE_INVALID",
            message="Token payload must be one-dimensional",
            details={"ndim": int(arr.ndim)},
        )

    if arr.size == 0:
        raise AvatarTokenShapeError(
            code="TOKEN_STREAM_EMPTY",
            message="Token payload must contain at least one value",
            details={},
        )

    if not np.isfinite(arr).all():
        raise AvatarTokenShapeError(
            code="TOKEN_VALUE_INVALID",
            message="Token payload includes NaN or infinite values",
            details={},
        )

    return arr.astype(np.float64)


def _normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    scale = max(float(np.linalg.norm(embedding)), 1.0)
    return embedding / scale


def _namespace_embedding(namespace: str, embedding: np.ndarray) -> np.ndarray:
    seed = int(hashlib.sha256(namespace.encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    projection = rng.uniform(0.95, 1.05, size=embedding.shape)
    return embedding * projection


def _execution_hash(*, namespaced: np.ndarray, namespace: str, token_count: int, fingerprint_seed: str) -> str:
    digest = hashlib.sha256()
    digest.update(fingerprint_seed.encode("utf-8"))
    digest.update(namespace.encode("utf-8"))
    digest.update(str(token_count).encode("utf-8"))
    digest.update(np.asarray(namespaced, dtype=np.float64).tobytes())
    return digest.hexdigest()
