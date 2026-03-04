"""Anthropic API adapter."""
from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

from orchestrator.llm_adapters.base import BaseLLMAdapter, InternalLLMRequest, InternalLLMResponse


class AnthropicAdapter(BaseLLMAdapter):
    """Adapter for Anthropic's messages API."""

    provider_name = "anthropic"

    def __init__(self) -> None:
        self._api_key = os.getenv("ANTHROPIC_API_KEY")
        self._endpoint = os.getenv("ANTHROPIC_ENDPOINT", "https://api.anthropic.com/v1/messages")
        self._default_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")

    def generate(self, request: InternalLLMRequest) -> InternalLLMResponse:
        if not self._api_key:
            raise ValueError("ANTHROPIC_API_KEY missing from environment variables")

        user_content = request.prompt
        if request.messages:
            user_content = "\n".join(msg.content for msg in request.messages if msg.role != "system")

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": request.model or self._default_model,
            "system": request.system_prompt,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": user_content}],
        }

        response = requests.post(self._endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        raw = response.json()
        content_blocks: List[Dict[str, Any]] = raw.get("content", [])
        content = "".join(block.get("text", "") for block in content_blocks if block.get("type") == "text")

        return InternalLLMResponse(
            content=content,
            provider=self.provider_name,
            model=payload["model"],
            raw_response=raw,
        )
