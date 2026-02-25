"""Client-side API helpers for A2A handshake + multimodal RAG grounding."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import httpx

from avatars.registry import get_avatar_registry
from orchestrator.multimodal_worldline import build_worldline_block, deterministic_embedding
from rbac.client import RBACClient

DEFAULT_CORPUS_GLOBS: tuple[str, ...] = (
    "orchestrator/**/*.py",
    "agents/**/*.py",
    "schemas/**/*.py",
    "docs/**/*.md",
    "specs/**/*.yaml",
    "specs/**/*.yml",
)

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".git",
    "build",
    "dist",
    "node_modules",
    ".venv",
    "venv",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".so",
    ".dll",
    ".exe",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".ico",
}


def _l2_normalize(values: Sequence[float]) -> List[float]:
    norm = math.sqrt(sum(float(value) * float(value) for value in values))
    if norm == 0.0:
        return [0.0 for _ in values]
    return [float(value) / norm for value in values]


def _text_chunks(text: str, *, chunk_size: int, overlap: int) -> List[str]:
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 4)

    chunks: List[str] = []
    cursor = 0
    step = max(1, chunk_size - overlap)
    while cursor < len(text):
        segment = text[cursor : cursor + chunk_size].strip()
        if segment:
            chunks.append(segment)
        cursor += step
    return chunks


def _source_type_from_path(path: str) -> str:
    head = path.split("/", 1)[0].strip().lower()
    return head or "unknown"


def _safe_agent_id(agent_name: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", "-", agent_name.lower()).strip("-")
    return compact or "agent"


@dataclass
class HandshakeAgentProfile:
    agent_name: str
    model_id: str = "gpt-4o-mini"
    embedding_dim: int = 768
    fidelity: str = "auto"
    role: str = "worker"
    avatar_key: str = "engineer"
    rbac_role: str = "pipeline_operator"
    metadata: Dict[str, Any] = field(default_factory=dict)


class A2AHandshakeClient:
    """
    Build and submit A2A handshake requests with grounded RAG + LoRA metadata.

    This client also indexes source corpus chunks into Qdrant using the requested
    payload shape:
      path, sha, chunk_index, source_type, grounding_tag
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:8000",
        qdrant_url: str = "http://localhost:6333",
        collection: str = "a2a_worldline_rag_v1",
        embedding_model: str = "sentence-transformers/all-mpnet-base-v2",
        embedding_dimensions: int = 768,
        timeout_seconds: float = 15.0,
        rbac_url: str = "http://localhost:8001",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.qdrant_url = qdrant_url.rstrip("/")
        self.collection = collection
        self.embedding_model = embedding_model
        self.embedding_dimensions = int(embedding_dimensions)
        self.timeout = float(timeout_seconds)
        self.http = httpx.Client(timeout=self.timeout)
        self.rbac = RBACClient(base_url=rbac_url, timeout=int(self.timeout))
        self.avatar_registry = get_avatar_registry()
        self._embedder = None

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> "A2AHandshakeClient":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def build_source_chunks(
        self,
        *,
        repo_root: str | Path,
        grounding_tag: str,
        globs: Sequence[str] = DEFAULT_CORPUS_GLOBS,
        chunk_size: int = 1400,
        overlap: int = 220,
    ) -> List[Dict[str, Any]]:
        root = Path(repo_root).resolve()
        candidates: Dict[Path, None] = {}

        for pattern in globs:
            for path in root.glob(pattern):
                if path.is_file():
                    candidates[path] = None

        chunks: List[Dict[str, Any]] = []
        for path in sorted(candidates):
            rel = path.relative_to(root).as_posix()
            if self._excluded(rel):
                continue

            raw = path.read_bytes()
            text = raw.decode("utf-8", errors="ignore")
            if not text.strip():
                continue

            sha = hashlib.sha256(raw).hexdigest()
            source_type = _source_type_from_path(rel)
            for index, piece in enumerate(
                _text_chunks(text, chunk_size=chunk_size, overlap=overlap)
            ):
                chunks.append(
                    {
                        "id": f"{sha[:16]}-{index}",
                        "text": piece,
                        "path": rel,
                        "sha": sha,
                        "chunk_index": index,
                        "source_type": source_type,
                        "grounding_tag": grounding_tag,
                    }
                )
        return chunks

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []

        try:
            if self._embedder is None:
                from sentence_transformers import SentenceTransformer

                self._embedder = SentenceTransformer(self.embedding_model)

            vectors = self._embedder.encode(  # type: ignore[union-attr]
                list(texts),
                normalize_embeddings=True,
            )
            return [list(map(float, row)) for row in vectors]
        except Exception:
            # Deterministic fallback for constrained environments.
            return [
                deterministic_embedding(
                    text,
                    dimensions=self.embedding_dimensions,
                    normalize=True,
                )
                for text in texts
            ]

    def upsert_chunks_to_qdrant(self, chunks: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        if not chunks:
            return {"collection": self.collection, "indexed": 0}

        vectors = self.embed_texts([str(chunk["text"]) for chunk in chunks])
        if not vectors:
            return {"collection": self.collection, "indexed": 0}

        vector_size = len(vectors[0])
        self._ensure_collection(vector_size=vector_size)

        points = []
        for chunk, vector in zip(chunks, vectors):
            payload = {
                "path": chunk["path"],
                "sha": chunk["sha"],
                "chunk_index": int(chunk["chunk_index"]),
                "source_type": chunk["source_type"],
                "grounding_tag": chunk["grounding_tag"],
            }
            points.append(
                {
                    "id": chunk["id"],
                    "vector": _l2_normalize(vector),
                    "payload": payload,
                }
            )

        response = self.http.put(
            f"{self.qdrant_url}/collections/{self.collection}/points",
            params={"wait": "true"},
            json={"points": points},
        )
        response.raise_for_status()
        return {"collection": self.collection, "indexed": len(points)}

    def index_branch_corpus(
        self,
        *,
        repo_root: str | Path,
        repository: str,
        commit_sha: str,
        actor: str,
        globs: Sequence[str] = DEFAULT_CORPUS_GLOBS,
    ) -> Dict[str, Any]:
        grounding_tag = f"{repository}:{commit_sha}:{actor}"
        chunks = self.build_source_chunks(
            repo_root=repo_root,
            grounding_tag=grounding_tag,
            globs=globs,
        )
        result = self.upsert_chunks_to_qdrant(chunks)
        result["chunk_count"] = len(chunks)
        result["grounding_tag"] = grounding_tag
        return result

    def build_lora_instruction_pairs(
        self,
        verified_nodes: Iterable[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        pairs: List[Dict[str, str]] = []
        for node in verified_nodes:
            metadata = node.get("metadata", {}) if isinstance(node, dict) else {}
            node_type = str(metadata.get("type", "")).strip().lower()
            text = str(node.get("text", "")).strip() if isinstance(node, dict) else ""
            if not text:
                continue

            if node_type == "recovery_logic":
                pairs.append(
                    {
                        "instruction": f"SYSTEM: Recover from failure context: {text}",
                        "output": (
                            "ACTION: Execute self-healing protocol with deterministic "
                            "rollback-safe guards."
                        ),
                    }
                )
            elif node_type == "code_solution":
                pairs.append(
                    {
                        "instruction": f"SYSTEM: Improve this verified solution: {text}",
                        "output": "ACTION: Apply optimization with strict boundary checks.",
                    }
                )
        return pairs

    def build_agent_spec(self, profile: HandshakeAgentProfile) -> Dict[str, Any]:
        agent_id = _safe_agent_id(profile.agent_name)
        role = profile.rbac_role.strip().lower() or "observer"

        rbac_payload: Dict[str, Any] = {"agent_id": agent_id, "role": role}
        try:
            onboarded = self.rbac.onboard_agent(
                agent_id=agent_id,
                agent_name=profile.agent_name,
                role=role,
                embedding_config={
                    "model_id": self.embedding_model,
                    "dim": profile.embedding_dim,
                },
                metadata={"avatar_key": profile.avatar_key},
            )
            permissions = self.rbac.get_permissions(agent_id=agent_id)
            if permissions:
                rbac_payload["actions"] = permissions.get("actions", [])
                rbac_payload["transitions"] = permissions.get("transitions", [])
            if onboarded:
                rbac_payload["onboarded"] = bool(onboarded.get("onboarded", False))
        except RuntimeError:
            # Keep payload deterministic even when RBAC gateway is offline.
            rbac_payload["onboarded"] = False

        avatar_payload: Dict[str, Any] = {}
        avatar = (
            self.avatar_registry.get_avatar(profile.avatar_key)
            or self.avatar_registry.get_avatar_for_agent(profile.agent_name)
        )
        if avatar is not None:
            avatar_payload = {
                "avatar_id": avatar.profile.avatar_id,
                "name": avatar.profile.name,
                "style": avatar.profile.style.value,
                "bound_agent": avatar.profile.bound_agent,
            }

        metadata = dict(profile.metadata)
        metadata["avatar"] = avatar_payload
        metadata["rbac"] = rbac_payload
        metadata["rag"] = {
            "collection": self.collection,
            "model": self.embedding_model,
            "dimensions": self.embedding_dimensions,
        }
        metadata["lora"] = {"encoding": "weight_plus_unit_direction"}

        return {
            "agent_name": profile.agent_name,
            "model_id": profile.model_id,
            "embedding_dim": int(profile.embedding_dim),
            "fidelity": profile.fidelity,
            "role": profile.role,
            "metadata": metadata,
        }

    def build_handshake_payload(
        self,
        *,
        prompt: str,
        repository: str,
        commit_sha: str,
        actor: str,
        api_key: str,
        endpoint: str,
        agent_profiles: Sequence[HandshakeAgentProfile],
        cluster_count: int = 4,
        top_k: int = 3,
        min_similarity: float = 0.10,
    ) -> Dict[str, Any]:
        worldline = build_worldline_block(
            prompt=prompt,
            repository=repository,
            commit_sha=commit_sha,
            actor=actor,
            cluster_count=cluster_count,
        )
        token_stream = worldline["infrastructure_agent"]["token_stream"]

        agent_specs = [self.build_agent_spec(profile) for profile in agent_profiles]
        return {
            "prompt": prompt,
            "repository": repository,
            "commit_sha": commit_sha,
            "actor": actor,
            "snapshot": {
                "repository": repository,
                "commit_sha": commit_sha,
                "actor": actor,
            },
            "cluster_count": int(cluster_count),
            "top_k": int(top_k),
            "min_similarity": float(min_similarity),
            "token_stream": token_stream,
            "agent_specs": agent_specs,
            "mcp": {
                "provider": "github-mcp",
                "tool_name": "ingest_worldline_block",
                "api_key": api_key,
                "endpoint": endpoint,
            },
            "runtime": {
                "wasm_shell": True,
                "engine": "WASD GameEngine",
                "unity_profile": "unity_lora_worker",
                "three_profile": "threejs_compact_worker",
            },
            "rag": {
                "collection": self.collection,
                "model": self.embedding_model,
                "dimensions": self.embedding_dimensions,
            },
            "grounding_worldline": worldline,
        }

    def submit_handshake(self, payload: Dict[str, Any], *, api_key: str) -> Dict[str, Any]:
        response = self.http.post(
            f"{self.base_url}/handshake/init",
            headers={"x-api-key": api_key},
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def _ensure_collection(self, *, vector_size: int) -> None:
        response = self.http.put(
            f"{self.qdrant_url}/collections/{self.collection}",
            json={"vectors": {"size": int(vector_size), "distance": "Cosine"}},
        )
        response.raise_for_status()

    @staticmethod
    def _excluded(rel_path: str) -> bool:
        path = rel_path.replace("\\", "/")
        parts = set(path.split("/"))
        if EXCLUDED_DIR_NAMES.intersection(parts):
            return True
        suffix = Path(path).suffix.lower()
        if suffix in EXCLUDED_SUFFIXES:
            return True
        return False

