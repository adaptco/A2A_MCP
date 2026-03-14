#!/usr/bin/env python3
"""Build Frontier LLM agent cards and RBAC MCP token bundle."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rbac.models import ACTION_PERMISSIONS, ROLE_PERMISSIONS, AgentRole  # noqa: E402
from scripts.frontier_preferences import load_workspace_preferences  # noqa: E402


FRONTIER_MODELS: list[dict[str, Any]] = [
    {
        "agent_id": "agent:frontier.endpoint.gpt",
        "display_name": "Endpoint GPT Operator",
        "provider": "endpoint",
        "model_family": "gpt",
        "default_model": "gpt-4o-mini",
        "role": "pipeline_operator",
        "extra_skills": ["code_generation", "task_planning"],
    },
    {
        "agent_id": "agent:frontier.anthropic.claude",
        "display_name": "Claude Governance Lead",
        "provider": "anthropic",
        "model_family": "claude",
        "default_model": "claude-3-5-sonnet-latest",
        "role": "admin",
        "extra_skills": ["policy_adjudication", "release_governance"],
    },
    {
        "agent_id": "agent:frontier.vertex.gemini",
        "display_name": "Gemini Architecture Mapper",
        "provider": "vertex",
        "model_family": "gemini",
        "default_model": "gemini-1.5-pro",
        "role": "pipeline_operator",
        "extra_skills": ["architecture_mapping", "context_synthesis"],
    },
    {
        "agent_id": "agent:frontier.ollama.llama",
        "display_name": "Llama Healer",
        "provider": "ollama",
        "model_family": "llama",
        "default_model": "llama3.1",
        "role": "healer",
        "extra_skills": ["regression_triage", "self_healing"],
    },
<<<<<<< HEAD
=======
    {
        "agent_id": "agent:frontier.reviewer",
        "display_name": "Frontier Reviewer",
        "provider": "endpoint",
        "model_family": "gpt",
        "default_model": "gpt-4o-mini",
        "role": "observer",
        "extra_skills": ["code_review", "security_audit"],
    },
>>>>>>> origin/main
]


ROLE_SKILLS: dict[str, list[str]] = {
    "admin": [
        "governance",
        "policy_enforcement",
        "orchestration",
        "tool_routing",
    ],
    "pipeline_operator": [
        "planning",
        "implementation",
        "integration",
        "artifact_management",
    ],
    "healer": [
        "failure_recovery",
        "patch_synthesis",
        "verification",
    ],
    "observer": [
        "artifact_review",
        "audit_logging",
    ],
}


READ_TOOL_HINTS = ("get_", "list_", "_status", "_lookup")


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _jwt_hs256(payload: dict[str, Any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    head_enc = _b64url(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    body_enc = _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{head_enc}.{body_enc}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(signature)}"


def _load_mcp_tools(repo_root: Path) -> list[str]:
    tools: list[str] = []

    mcp_tooling_path = repo_root / "app" / "mcp_tooling.py"
    runtime_server_path = repo_root / "runtime_mcp_server.py"

    if mcp_tooling_path.exists():
        text = mcp_tooling_path.read_text(encoding="utf-8")
        tools.extend(re.findall(r'"([a-zA-Z0-9_]+)"\s*:\s*\{\s*"func"\s*:', text))

    if runtime_server_path.exists():
        text = runtime_server_path.read_text(encoding="utf-8")
        tools.extend(re.findall(r"mcp\.tool\(\)\(([a-zA-Z0-9_]+)\)", text))

    seen: set[str] = set()
    deduped: list[str] = []
    for tool in sorted(tools):
        if tool not in seen:
            deduped.append(tool)
            seen.add(tool)
    return deduped


def _tool_scope_for_role(role: str, all_tools: list[str]) -> list[str]:
    if role in {"admin", "pipeline_operator"}:
        return list(all_tools)

    if role == "healer":
        allow_healer = {
            "embed_dispatch_batch",
            "embed_lookup",
            "embed_status",
            "ingest_avatar_token_stream",
            "list_runtime_assignments",
            "get_runtime_assignment",
            "route_a2a_intent",
        }
        tools = [tool for tool in all_tools if tool in allow_healer]
        return tools

    # observer fallback: read-like queries only
    return [tool for tool in all_tools if tool.startswith(READ_TOOL_HINTS)]


def _normalize_token_ref(tokens_out: Path, repo_root: Path) -> str:
    token_ref = str(tokens_out)
    if tokens_out.is_absolute() and str(tokens_out).startswith(str(repo_root)):
        token_ref = str(tokens_out.relative_to(repo_root))
    return token_ref.replace("\\", "/")


def _build_cards(all_tools: list[str], token_ref: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for profile in FRONTIER_MODELS:
        role = AgentRole(profile["role"])
        role_name = role.value

        base_skills = ROLE_SKILLS.get(role_name, [])
        merged_skills = list(dict.fromkeys([*base_skills, *profile.get("extra_skills", [])]))

        cards.append(
            {
                "card_id": f"card:{_slug(profile['agent_id'])}",
                "agent_id": profile["agent_id"],
                "display_name": profile["display_name"],
                "llm": {
                    "provider": profile["provider"],
                    "model_family": profile["model_family"],
                    "default_model": profile["default_model"],
                },
                "role": role_name,
                "embedded_skills": merged_skills,
                "mcp_tool_scope": _tool_scope_for_role(role_name, all_tools),
                "rbac": {
                    "allowed_actions": sorted(ACTION_PERMISSIONS[role]),
                    "allowed_transitions": sorted(ROLE_PERMISSIONS[role]),
                    "token_ref": f"{token_ref}#{profile['agent_id']}",
                },
            }
        )
    return cards


def _build_tokens(
    cards: list[dict[str, Any]],
    secret: str,
    issuer: str,
    ttl_hours: int,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=ttl_hours)
    iat = int(now.timestamp())
    exp_ts = int(exp.timestamp())

    token_docs: list[dict[str, Any]] = []
    for card in cards:
        role = card["role"]
        token_id_src = f"{card['agent_id']}|{role}|{iat}|{issuer}"
        token_id = hashlib.sha256(token_id_src.encode("utf-8")).hexdigest()[:24]
        payload = {
            "iss": issuer,
            "aud": "a2a.mcp.tooling",
            "sub": card["agent_id"],
            "jti": token_id,
            "iat": iat,
            "exp": exp_ts,
            "role": role,
            "provider": card["llm"]["provider"],
            "model_family": card["llm"]["model_family"],
            "allowed_actions": card["rbac"]["allowed_actions"],
            "allowed_transitions": card["rbac"]["allowed_transitions"],
            "allowed_tools": card["mcp_tool_scope"],
            "tool_pull": True,
        }
        jwt_token = _jwt_hs256(payload, secret)
        token_docs.append(
            {
                "agent_id": card["agent_id"],
                "token_id": token_id,
                "issued_at": now.isoformat().replace("+00:00", "Z"),
                "expires_at": exp.isoformat().replace("+00:00", "Z"),
                "token": jwt_token,
            }
        )

    return {
        "version": "v1",
        "issuer": issuer,
        "generated_at": _iso_now(),
        "ttl_hours": ttl_hours,
        "tokens": token_docs,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build frontier LLM agent cards/index and local RBAC token bundle."
    )
    parser.add_argument(
        "--index-out",
        default=str(REPO_ROOT / "registry" / "agents" / "frontier_agent_index.v1.json"),
    )
    parser.add_argument(
        "--cards-out",
        default=str(REPO_ROOT / "registry" / "agents" / "frontier_agent_cards.v1.json"),
    )
    parser.add_argument(
        "--tokens-out",
        default=str(REPO_ROOT / "runtime" / "rbac" / "frontier_rbac_tokens.local.json"),
    )
    parser.add_argument("--issuer", default="mcp://a2a/rbac")
    parser.add_argument("--ttl-hours", type=int, default=24)
    parser.add_argument("--secret-env", default="RBAC_SECRET")
    args = parser.parse_args()

    index_out = Path(args.index_out)
    cards_out = Path(args.cards_out)
    tokens_out = Path(args.tokens_out)

    tools = _load_mcp_tools(REPO_ROOT)
    token_ref = _normalize_token_ref(tokens_out, REPO_ROOT)
    cards = _build_cards(tools, token_ref=token_ref)

    secret = os.getenv(args.secret_env, "dev-secret-change-me")
    tokens = _build_tokens(cards, secret=secret, issuer=args.issuer, ttl_hours=args.ttl_hours)

    preferences = load_workspace_preferences()

    index_payload = {
        "version": "v1",
        "generated_at": _iso_now(),
        "sources": {
            "agent_registry": "registry/agents/agent_registry.json",
            "expert_catalog": "registry/experts/expert_catalog.v1.json",
            "rbac_models": "rbac/models.py",
        },
        "frontier_agent_count": len(cards),
        "mcp_tool_count": len(tools),
        "mcp_tools": tools,
        "workspace_preferences": preferences,
        "agents": [
            {
                "agent_id": card["agent_id"],
                "role": card["role"],
                "provider": card["llm"]["provider"],
                "model_family": card["llm"]["model_family"],
                "card_ref": f"registry/agents/frontier_agent_cards.v1.json#{card['agent_id']}",
            }
            for card in cards
        ],
    }

    cards_payload = {
        "version": "v1",
        "generated_at": _iso_now(),
        "cards": cards,
    }

    _write_json(index_out, index_payload)
    _write_json(cards_out, cards_payload)
    _write_json(tokens_out, tokens)

    print(f"wrote index:  {index_out}")
    print(f"wrote cards:  {cards_out}")
    print(f"wrote tokens: {tokens_out}")
    print(f"frontier agents: {len(cards)}")
    print(f"mcp tools in scope: {len(tools)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
