"""World model skill programming — bridges Skills.md phases into worldline generation.

Implements the five-phase MCP skill lifecycle (SAMPLE → RESOLVE → PLAN → EXECUTE → VERIFY)
and provides Codestral API completion for avatar token generation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class CodestralConfig:
    """Configuration for the Codestral chat and FIM completion APIs."""

    api_key: str
    endpoint: str
    fim_endpoint: str
    model: str
    max_tokens: int = 512
    temperature: float = 0.7

    @classmethod
    def from_env(cls) -> "CodestralConfig":
        """Load configuration from environment variables."""
        return cls(
            api_key=os.environ.get("LLM_API_KEY", ""),
            endpoint=os.environ.get(
                "LLM_ENDPOINT",
                "https://codestral.mistral.ai/v1/chat/completions",
            ),
            fim_endpoint=os.environ.get(
                "CODESTRAL_FIM_ENDPOINT",
                "https://codestral.mistral.ai/v1/fim/completions",
            ),
            model=os.environ.get("LLM_MODEL", "codestral-latest"),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.endpoint)


class CodestralClient:
    """Lightweight HTTP client for Codestral chat and FIM completions APIs."""

    def __init__(self, config: Optional[CodestralConfig] = None):
        self.config = config or CodestralConfig.from_env()

    async def complete(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Call the Codestral chat completions endpoint.

        Returns the raw API response as a dict, or an error structure
        if the API key is missing or the request fails.
        """
        if not self.config.is_configured:
            return {
                "error": "codestral_not_configured",
                "message": "LLM_API_KEY or LLM_ENDPOINT not set",
                "choices": [],
            }

        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.config.endpoint,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Codestral API error: %s %s", exc.response.status_code, exc.response.text)
            return {
                "error": "codestral_api_error",
                "status_code": exc.response.status_code,
                "message": exc.response.text[:500],
                "choices": [],
            }
        except httpx.RequestError as exc:
            logger.error("Codestral request error: %s", exc)
            return {
                "error": "codestral_request_error",
                "message": str(exc)[:500],
                "choices": [],
            }

    async def fim_complete(
        self,
        prompt: str,
        suffix: str = "",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Call the Codestral FIM (Fill-in-the-Middle) completions endpoint.

        Used for code infilling — provide a prefix (prompt) and optional suffix,
        and the model generates the code that fills the gap.
        """
        if not self.config.is_configured:
            return {
                "error": "codestral_not_configured",
                "message": "LLM_API_KEY or CODESTRAL_FIM_ENDPOINT not set",
                "choices": [],
            }

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }
        if suffix:
            payload["suffix"] = suffix
        if stop:
            payload["stop"] = stop

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.config.fim_endpoint,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Codestral FIM error: %s %s", exc.response.status_code, exc.response.text)
            return {
                "error": "codestral_fim_error",
                "status_code": exc.response.status_code,
                "message": exc.response.text[:500],
                "choices": [],
            }
        except httpx.RequestError as exc:
            logger.error("Codestral FIM request error: %s", exc)
            return {
                "error": "codestral_fim_request_error",
                "message": str(exc)[:500],
                "choices": [],
            }


def _skill_phase_hash(phase: str, input_data: str) -> str:
    """Deterministic hash for skill phase tracking."""
    return hashlib.sha256(f"{phase}::{input_data}".encode("utf-8")).hexdigest()[:16]


def program_world_model(
    prompt: str,
    repository: str = "A2A_MCP",
    commit_sha: str = "HEAD",
    actor: str = "github-actions",
    risk_profile: str = "medium",
) -> Dict[str, Any]:
    """Run the prompt through the five-phase MCP skill lifecycle.

    SAMPLE → RESOLVE → PLAN → EXECUTE → VERIFY

    Returns a structured worldline block with phase traces.
    """
    from world_foundation_model import build_worldline_block

    # Phase 1: SAMPLE — ingest and hash the prompt
    sample_hash = _skill_phase_hash("SAMPLE", prompt)
    sample_trace = {
        "phase": "SAMPLE",
        "hash": sample_hash,
        "input_length": len(prompt),
    }

    # Phase 2: RESOLVE — determine available MCP tools
    available_tools = [
        "embed_submit", "embed_status", "embed_lookup",
        "embed_dispatch_batch", "route_a2a_intent",
        "submit_runtime_assignment", "get_runtime_assignment",
    ]
    resolve_trace = {
        "phase": "RESOLVE",
        "hash": _skill_phase_hash("RESOLVE", json.dumps(available_tools)),
        "tools_found": len(available_tools),
        "tool_names": available_tools,
    }

    # Phase 3: PLAN — construct the execution DAG
    plan_dag = {
        "steps": [
            {"tool": "embed_submit", "depends_on": []},
            {"tool": "embed_status", "depends_on": ["embed_submit"]},
            {"tool": "build_worldline_block", "depends_on": ["embed_status"]},
        ]
    }
    plan_trace = {
        "phase": "PLAN",
        "hash": _skill_phase_hash("PLAN", json.dumps(plan_dag)),
        "step_count": len(plan_dag["steps"]),
    }

    # Phase 4: EXECUTE — build the worldline block
    worldline = build_worldline_block(
        prompt=prompt,
        repository=repository,
        commit_sha=commit_sha,
        actor=actor,
        risk_profile=risk_profile,
    )
    execute_trace = {
        "phase": "EXECUTE",
        "hash": _skill_phase_hash("EXECUTE", json.dumps({"prompt": prompt})),
        "worldline_pipeline": worldline.get("pipeline", ""),
    }

    # Phase 5: VERIFY — validate output integrity
    verification = {
        "has_infrastructure_agent": "infrastructure_agent" in worldline,
        "has_snapshot": "snapshot" in worldline,
        "has_mcp_tool_call": "github_mcp_tool_call" in worldline,
        "avatar_count": len(
            worldline.get("infrastructure_agent", {}).get("coding_agent_avatars", [])
        ),
    }
    verify_trace = {
        "phase": "VERIFY",
        "hash": _skill_phase_hash("VERIFY", json.dumps(verification)),
        "checks_passed": all(verification.values()),
        "verification": verification,
    }

    return {
        "worldline": worldline,
        "skill_lifecycle": {
            "phases": ["SAMPLE", "RESOLVE", "PLAN", "EXECUTE", "VERIFY"],
            "traces": [sample_trace, resolve_trace, plan_trace, execute_trace, verify_trace],
            "all_phases_passed": verify_trace["checks_passed"],
        },
    }


async def complete_avatar_tokens(
    avatar_prompts: List[Dict[str, str]],
    config: Optional[CodestralConfig] = None,
) -> Dict[str, Any]:
    """Generate completion tokens for avatar system prompts via Codestral.

    Each avatar prompt should have:
      - "avatar_name": the avatar identity
      - "system_prompt": the context prompt for completion

    Returns completion results keyed by avatar name.
    """
    client = CodestralClient(config)
    results: Dict[str, Any] = {}

    for avatar in avatar_prompts:
        name = avatar.get("avatar_name", "unknown")
        system_prompt = avatar.get("system_prompt", "")

        if not system_prompt:
            results[name] = {
                "status": "skipped",
                "reason": "empty_system_prompt",
                "tokens": [],
            }
            continue

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI avatar agent. Generate structured action tokens "
                    "for the following avatar context. Return a JSON array of token objects "
                    "with 'action', 'priority', and 'context' fields."
                ),
            },
            {"role": "user", "content": system_prompt},
        ]

        response = await client.complete(messages, max_tokens=256, temperature=0.3)

        if "error" in response:
            results[name] = {
                "status": "error",
                "error": response["error"],
                "message": response.get("message", ""),
                "tokens": [],
            }
        else:
            choices = response.get("choices", [])
            content = choices[0]["message"]["content"] if choices else ""
            token_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

            results[name] = {
                "status": "completed",
                "content": content,
                "token_hash": token_hash,
                "model": response.get("model", ""),
                "usage": response.get("usage", {}),
            }

    return {
        "avatar_completions": results,
        "total_avatars": len(avatar_prompts),
        "completed": sum(1 for r in results.values() if r.get("status") == "completed"),
        "errors": sum(1 for r in results.values() if r.get("status") == "error"),
    }
