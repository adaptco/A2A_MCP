#!/usr/bin/env python3
"""Build a compact zero-shot avatar launch packet from the A2A_MCP repo root."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]

IMPORTANT_PATHS: dict[str, str] = {
    "root_agents": "AGENTS.md",
    "avatar_system": "AVATAR_SYSTEM.md",
    "avatar_bindings": "avatar_bindings.v1.json",
    "frontier_agent_index": "registry/agents/frontier_agent_index.v1.json",
    "frontier_agent_cards": "registry/agents/frontier_agent_cards.v1.json",
    "mcp_tooling": "app/mcp_tooling.py",
    "runtime_mcp_server": "runtime_mcp_server.py",
    "mcp_server": "mcp_server.py",
    "embed_control_plane": "embed_control_plane.py",
}


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_json(path: Path) -> Any:
    return json.loads(_read_text(path))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def _detect_repository_slug() -> str:
    remote = _git("config", "--get", "remote.origin.url")
    if remote:
        match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote)
        if match:
            return match.group(1)
    return REPO_ROOT.name


def _extract_agents_summary(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    overview: list[str] = []
    commands: list[str] = []
    artifacts: list[str] = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "Core areas include:":
            cursor = index + 1
            while cursor < len(lines) and lines[cursor].strip().startswith("- "):
                overview.append(lines[cursor].strip()[2:])
                cursor += 1
        if stripped.startswith("Generate the Frontier LLM agent index"):
            cursor = index + 1
            while cursor < len(lines) and lines[cursor].strip().startswith("- "):
                commands.append(lines[cursor].strip()[2:])
                cursor += 1
        if stripped == "Artifacts written by the command:":
            cursor = index + 1
            while cursor < len(lines) and lines[cursor].strip().startswith("- "):
                artifacts.append(lines[cursor].strip()[2:])
                cursor += 1

    return {
        "overview": overview,
        "frontier_index_commands": commands,
        "frontier_index_artifacts": artifacts,
    }


def _extract_tool_registry(mcp_tooling_text: str) -> dict[str, list[str]]:
    protected: list[str] = []
    open_tools: list[str] = []
    pattern = re.compile(
        r'"([^"]+)"\s*:\s*\{\s*"func"\s*:\s*[^,]+,\s*"protected"\s*:\s*(True|False)',
        re.DOTALL,
    )
    for tool_name, protected_flag in pattern.findall(mcp_tooling_text):
        if protected_flag == "True":
            protected.append(tool_name)
        else:
            open_tools.append(tool_name)
    return {
        "protected": sorted(set(protected)),
        "open": sorted(set(open_tools)),
    }


def _extract_runtime_tools(runtime_server_text: str) -> list[str]:
    return sorted(set(re.findall(r"mcp\.tool\(\)\(([a-zA-Z0-9_]+)\)", runtime_server_text)))


def _artifact_refs() -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for label, relative_path in IMPORTANT_PATHS.items():
        path = REPO_ROOT / relative_path
        if not path.exists():
            continue
        refs.append(
            {
                "id": label,
                "path": _relative(path),
                "sha256": _sha256_file(path),
            }
        )
    return refs


def _avatar_summary(bindings: dict[str, Any]) -> list[dict[str, Any]]:
    avatars = []
    for avatar in bindings.get("avatars", []):
        avatars.append(
            {
                "id": avatar.get("id"),
                "name": avatar.get("name"),
                "vessel": avatar.get("vessel"),
                "capsule": avatar.get("capsule"),
                "capsule_gate": avatar.get("capsule_gate"),
            }
        )
    return avatars


def _frontier_summary(cards_doc: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for card in cards_doc.get("cards", []):
        cards.append(
            {
                "agent_id": card.get("agent_id"),
                "display_name": card.get("display_name"),
                "role": card.get("role"),
                "default_model": card.get("llm", {}).get("default_model"),
                "embedded_skills": card.get("embedded_skills", []),
                "mcp_tool_scope_count": len(card.get("mcp_tool_scope", [])),
            }
        )
    return cards


def build_packet(
    prompt: str,
    actor: str,
    risk_profile: str,
    cluster_count: int,
) -> dict[str, Any]:
    repository = _detect_repository_slug()
    commit_sha = _git("rev-parse", "HEAD") or "UNKNOWN"

    agents_doc = _read_text(REPO_ROOT / IMPORTANT_PATHS["root_agents"])
    avatar_bindings = _read_json(REPO_ROOT / IMPORTANT_PATHS["avatar_bindings"])
    frontier_index = _read_json(REPO_ROOT / IMPORTANT_PATHS["frontier_agent_index"])
    frontier_cards = _read_json(REPO_ROOT / IMPORTANT_PATHS["frontier_agent_cards"])
    mcp_tooling_text = _read_text(REPO_ROOT / IMPORTANT_PATHS["mcp_tooling"])
    runtime_server_text = _read_text(REPO_ROOT / IMPORTANT_PATHS["runtime_mcp_server"])

    tool_registry = _extract_tool_registry(mcp_tooling_text)
    runtime_tools = _extract_runtime_tools(runtime_server_text)
    avatars = _avatar_summary(avatar_bindings)
    frontier_agents = _frontier_summary(frontier_cards)
    artifact_refs = _artifact_refs()

    avatar_namespace = f"avatar::{repository}"
    key_artifact_paths = [item["path"] for item in artifact_refs]

    return {
        "repo_root": str(REPO_ROOT),
        "repository": repository,
        "commit_sha": commit_sha,
        "artifact_refs": artifact_refs,
        "root_summary": _extract_agents_summary(agents_doc),
        "avatar_cast": {
            "count": len(avatars),
            "avatars": avatars,
        },
        "frontier_agents": {
            "count": len(frontier_agents),
            "mcp_tool_count": frontier_index.get("mcp_tool_count", 0),
            "mcp_tools": frontier_index.get("mcp_tools", []),
            "agents": frontier_agents,
        },
        "mcp_surfaces": {
            "protected_tools": tool_registry["protected"],
            "open_tools": tool_registry["open"],
            "runtime_tools": runtime_tools,
            "preferred_runtime_entrypoint": "runtime_mcp_server.py",
            "compatibility_entrypoint": "mcp_server.py",
        },
        "zero_shot_state": {
            "prompt": prompt,
            "actor": actor,
            "risk_profile": risk_profile,
            "cluster_count": cluster_count,
            "avatar_namespace": avatar_namespace,
            "tool_sequence": [
                {
                    "tool": "get_coding_agent_avatar_cast",
                    "reason": "hydrate the coding-agent avatar cast before token shaping",
                },
                {
                    "tool": "build_local_world_foundation_model",
                    "reason": "produce the root-repo context block for the downstream chat model",
                },
                {
                    "tool": "ingest_repository_data",
                    "reason": "verify the repository snapshot with the bearer token claim",
                },
                {
                    "tool": "ingest_avatar_token_stream",
                    "reason": "shape and namespace the API-triggered avatar token stream",
                },
                {
                    "tool": "route_a2a_intent",
                    "reason": "route the prepared launch request into the runtime MCP node",
                },
            ],
            "payload_templates": {
                "build_local_world_foundation_model": {
                    "prompt": prompt,
                    "repository": repository,
                    "commit_sha": commit_sha,
                    "actor": actor,
                    "cluster_count": cluster_count,
                    "risk_profile": risk_profile,
                },
                "ingest_repository_data": {
                    "snapshot": {
                        "repository": repository,
                        "commit_sha": commit_sha,
                        "artifacts": key_artifact_paths,
                        "frontier_agents": [agent["agent_id"] for agent in frontier_agents],
                        "avatar_ids": [avatar["id"] for avatar in avatars],
                    },
                    "authorization": "Bearer <OIDC token>",
                },
                "ingest_avatar_token_stream": {
                    "payload": {
                        "namespace": avatar_namespace,
                        "max_tokens": 64,
                        "tokens": [
                            {
                                "token": "<api-triggered-token>",
                                "kind": "skill",
                                "artifact_ref": "avatar_bindings.v1.json#<avatar-id>",
                            }
                        ],
                    },
                    "authorization": "Bearer <OIDC token>",
                },
                "route_a2a_intent": {
                    "message": {
                        "intent": "root_repo_context_launch",
                        "repository": repository,
                        "commit_sha": commit_sha,
                        "prompt": prompt,
                        "avatar_namespace": avatar_namespace,
                        "actor": actor,
                    }
                },
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True, help="Objective or user request for the downstream model")
    parser.add_argument("--actor", default="api_user", help="Actor name for the world foundation model payload")
    parser.add_argument(
        "--risk-profile",
        default="medium",
        choices=["low", "medium", "high"],
        help="Risk profile for the launch packet",
    )
    parser.add_argument("--cluster-count", type=int, default=4, help="Cluster count hint for the world model payload")
    parser.add_argument("--output", help="Optional file path to write the JSON packet")
    args = parser.parse_args()

    packet = build_packet(
        prompt=args.prompt,
        actor=args.actor,
        risk_profile=args.risk_profile,
        cluster_count=args.cluster_count,
    )
    rendered = json.dumps(packet, indent=2, sort_keys=False)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        sys.stdout.write(rendered + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
