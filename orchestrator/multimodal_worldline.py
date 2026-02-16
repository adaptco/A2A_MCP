"""Multimodal worldline builder for prompt -> embedding -> token -> MCP payload."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Iterable, List


def deterministic_embedding(text: str, dimensions: int = 32) -> List[float]:
    """Create a deterministic embedding vector from text."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: List[float] = []
    for idx in range(dimensions):
        byte = digest[idx % len(digest)]
        values.append((byte / 255.0) * 2.0 - 1.0)
    return values


def tokenize_prompt(prompt: str) -> List[str]:
    """Tokenize prompt into lower-cased words."""
    return re.findall(r"[a-zA-Z0-9_]+", prompt.lower())


def token_to_id(token: str, idx: int) -> str:
    return hashlib.sha1(f"{idx}:{token}".encode("utf-8")).hexdigest()[:16]


def cluster_artifacts(artifacts: Iterable[str], cluster_count: int = 4) -> Dict[str, List[str]]:
    """Cluster artifacts deterministically using hash buckets."""
    count = max(1, int(cluster_count))
    clusters: Dict[str, List[str]] = {f"cluster_{i}": [] for i in range(count)}

    for artifact in artifacts:
        digest = hashlib.sha256(artifact.encode("utf-8")).digest()
        bucket = digest[0] % count
        clusters[f"cluster_{bucket}"].append(artifact)

    return clusters


def lora_attention_weights(clusters: Dict[str, List[str]]) -> Dict[str, float]:
    """Map clustered artifact volume into normalized LoRA attention weights."""
    total = sum(len(items) for items in clusters.values())
    if total == 0:
        unit = 1.0 / max(1, len(clusters))
        return {name: unit for name in clusters}
    return {name: len(items) / total for name, items in clusters.items()}


def _pascal_case(value: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", value)
    return "".join(part.capitalize() for part in parts) or "QubeAgent"


def build_unity_class(class_name: str, env_keys: Dict[str, str]) -> str:
    """Create a Unity C# object class wired to environment variables."""
    return (
        "using System;\n"
        "using UnityEngine;\n\n"
        f"public class {class_name} : MonoBehaviour\n"
        "{\n"
        '    [SerializeField] private string mcpApiUrl = "";\n'
        '    [SerializeField] private string worldlineId = "";\n\n'
        "    void Awake()\n"
        "    {\n"
        f'        mcpApiUrl = Environment.GetEnvironmentVariable("{env_keys["mcp_api_url"]}") ?? mcpApiUrl;\n'
        f'        worldlineId = Environment.GetEnvironmentVariable("{env_keys["worldline_id"]}") ?? worldlineId;\n'
        "    }\n"
        "}\n"
    )


def build_worldline_block(
    *,
    prompt: str,
    repository: str,
    commit_sha: str,
    actor: str = "github-actions",
    cluster_count: int = 4,
) -> Dict[str, Any]:
    """
    Build a deterministic multimodal orchestration block:
    prompt -> embedding -> tokens -> clustered artifacts -> LoRA weights -> MCP payload.
    """
    tokens = tokenize_prompt(prompt)
    token_ids = [token_to_id(token, idx) for idx, token in enumerate(tokens)]
    embedding = deterministic_embedding(prompt, dimensions=32)

    artifacts = [f"artifact::{token}" for token in tokens] or ["artifact::default"]
    clusters = cluster_artifacts(artifacts, cluster_count=cluster_count)
    weights = lora_attention_weights(clusters)

    class_base = _pascal_case(prompt)[:48]
    unity_class_name = f"{class_base}InfrastructureAgent"
    unity_env = {
        "mcp_api_url": "UNITY_MCP_API_URL",
        "worldline_id": "UNITY_WORLDLINE_ID",
        "unity_project_root": "UNITY_PROJECT_ROOT",
    }

    multimodal_plan = {
        "text_to_image": {
            "engine": "stable-diffusion-compatible",
            "prompt": prompt,
            "style": "technical storyboard",
        },
        "image_to_video": {
            "engine": "video-diffusion-compatible",
            "fps": 24,
            "seconds": 6,
            "input_frames": ["frame_001.png", "frame_002.png"],
        },
        "video_to_multimodal_script": {
            "avatar_name": "QubeInfrastructureAvatar",
            "script": (
                "Scene boot. Resolve MCP endpoint from env. "
                "Load embedding vector, token stream, and LoRA weights. "
                "Instantiate Unity object class and dispatch worldline task."
            ),
        },
    }

    infrastructure_agent = {
        "agent_name": "QubeInfrastructureAgent",
        "mode": "agentic-worldline",
        "embedding_vector": embedding,
        "token_stream": [{"token": t, "token_id": tid} for t, tid in zip(tokens, token_ids)],
        "artifact_clusters": clusters,
        "lora_attention_weights": weights,
        "unity_object_class_name": unity_class_name,
        "unity_object_class_source": build_unity_class(unity_class_name, unity_env),
        "unity_env": unity_env,
        "multimodal_plan": multimodal_plan,
    }

    snapshot = {
        "repository": repository,
        "commit_sha": commit_sha,
        "actor": actor,
    }

    github_mcp_tool_call = {
        "provider": "github-mcp",
        "api_mapping": {
            "endpoint_env_var": "GITHUB_MCP_API_URL",
            "method": "POST",
            "path": "/tools/call",
        },
        "tool_name": "ingest_worldline_block",
        "arguments": {
            "authorization": "Bearer ${GITHUB_TOKEN}",
            "worldline_block": {
                "snapshot": snapshot,
                "infrastructure_agent": infrastructure_agent,
            },
        },
    }

    return {
        "pipeline": "qube-multimodal-worldline",
        "prompt": prompt,
        "repository": repository,
        "commit_sha": commit_sha,
        "actor": actor,
        "snapshot": snapshot,
        "infrastructure_agent": infrastructure_agent,
        "github_mcp_tool_call": github_mcp_tool_call,
    }


def serialize_worldline_block(block: Dict[str, Any]) -> str:
    """Serialize worldline block as formatted JSON."""
    return json.dumps(block, indent=2, ensure_ascii=True)
