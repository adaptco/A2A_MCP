"""Root world foundation model for agent-avatar MCP worldline payloads."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Sequence

from agent_style_entropy import build_style_temperature_plan
from avatars.registry import get_avatar_registry
from avatars.setup import setup_default_avatars

DEFAULT_CODING_AGENT_CAST: tuple[str, ...] = (
    "ManagingAgent",
    "OrchestrationAgent",
    "ArchitectureAgent",
    "CoderAgent",
    "TesterAgent",
)


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
    """Build deterministic token identifier."""
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


def _serialize_avatar_bound_agent(agent_name: str, avatar: Any | None) -> Dict[str, Any]:
    """Serialize a coding agent avatar binding into MCP-safe JSON."""
    if avatar is None:
        return {
            "agent_name": agent_name,
            "avatar_id": "",
            "avatar_name": "",
            "style": "engineer",
            "bound_agent": agent_name,
            "voice_config": {},
            "ui_config": {},
            "system_prompt": "",
            "description": "",
        }

    profile = avatar.profile
    style = getattr(profile.style, "value", str(profile.style))
    return {
        "agent_name": agent_name,
        "avatar_id": profile.avatar_id,
        "avatar_name": profile.name,
        "style": style,
        "bound_agent": profile.bound_agent or agent_name,
        "voice_config": dict(profile.voice_config),
        "ui_config": dict(profile.ui_config),
        "system_prompt": avatar.get_system_context(),
        "description": profile.description,
    }


def build_coding_agent_avatar_cast(
    agent_names: Sequence[str] = DEFAULT_CODING_AGENT_CAST,
) -> List[Dict[str, Any]]:
    """
    Build avatar bindings for the coding agent cast.

    This ensures the world foundation model includes embodied avatar metadata
    for planning, coding, and testing workers.
    """
    registry = get_avatar_registry()
    if not registry.list_avatars():
        setup_default_avatars()

    cast: List[Dict[str, Any]] = []
    for agent_name in agent_names:
        avatar = registry.get_avatar_for_agent(agent_name)
        cast.append(_serialize_avatar_bound_agent(agent_name, avatar))
    return cast


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
    risk_profile: str = "medium",
) -> Dict[str, Any]:
    """
    Build the local world foundation model block.

    prompt -> embedding -> tokens -> clustered artifacts -> LoRA weights ->
    avatar-embedded coding cast -> MCP server tool payload.
    """
    tokens = tokenize_prompt(prompt)
    token_ids = [token_to_id(token, idx) for idx, token in enumerate(tokens)]
    embedding = deterministic_embedding(prompt, dimensions=32)

    artifacts = [f"artifact::{token}" for token in tokens] or ["artifact::default"]
    clusters = cluster_artifacts(artifacts, cluster_count=cluster_count)
    weights = lora_attention_weights(clusters)
    coding_avatar_cast = build_coding_agent_avatar_cast()
    style_plan = build_style_temperature_plan(
        prompt=prompt,
        risk_profile=risk_profile,
        changed_path_count=len(artifacts),
    )

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
                "Load embedding vector, token stream, LoRA weights, and coding "
                "agent avatar cast. Instantiate Unity object class and dispatch "
                "worldline task."
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
        "coding_agent_avatars": coding_avatar_cast,
        "style_temperature_profile": {
            "enthalpy": style_plan["enthalpy"],
            "entropy": style_plan["entropy"],
            "temperature": style_plan["temperature"],
            "model_style_preferences": style_plan["model_style_preferences"],
        },
        "template_route": {
            "selected_template": style_plan["selected_template"],
            "template_scores": style_plan["template_scores"],
            "selected_actions": style_plan["selected_actions"],
        },
        "api_skill_tokens": style_plan["api_skill_tokens"],
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


def build_world_foundation_model(
    *,
    prompt: str,
    repository: str,
    commit_sha: str,
    actor: str = "github-actions",
    cluster_count: int = 4,
    risk_profile: str = "medium",
) -> Dict[str, Any]:
    """Alias for world foundation model generation."""
    return build_worldline_block(
        prompt=prompt,
        repository=repository,
        commit_sha=commit_sha,
        actor=actor,
        cluster_count=cluster_count,
        risk_profile=risk_profile,
    )


def serialize_worldline_block(block: Dict[str, Any]) -> str:
    """Serialize worldline block as formatted JSON."""
    return json.dumps(block, indent=2, ensure_ascii=True)


__all__ = [
    "DEFAULT_CODING_AGENT_CAST",
    "deterministic_embedding",
    "tokenize_prompt",
    "token_to_id",
    "cluster_artifacts",
    "lora_attention_weights",
    "build_coding_agent_avatar_cast",
    "build_unity_class",
    "build_worldline_block",
    "build_world_foundation_model",
    "serialize_worldline_block",
    "_pascal_case",
]
