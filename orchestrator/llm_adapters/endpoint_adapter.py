"""OpenAI-compatible endpoint adapter (generic HTTP transport)."""
from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

from orchestrator.llm_adapters.base import (
    BaseLLMAdapter,
    InternalLLMRequest,
    InternalLLMResponse,
)


class EndpointAdapter(BaseLLMAdapter):
    """Adapter for OpenAI-compatible chat completion endpoints."""

    provider_name = "endpoint"

    def __init__(self) -> None:
        self._api_key = os.getenv("LLM_API_KEY")
        self._endpoint = os.getenv("LLM_ENDPOINT")
        self._default_model = os.getenv("LLM_MODEL", "codestral-latest")

    def _normalize_messages(self, request: InternalLLMRequest) -> List[Dict[str, str]]:
        if request.messages:
            return [{"role": m.role, "content": m.content} for m in request.messages]

        return [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.prompt},
        ]

    def generate(self, request: InternalLLMRequest) -> InternalLLMResponse:
        if not self._api_key or not self._endpoint:
            raise ValueError("API Key or Endpoint missing from environment variables")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": request.model or self._default_model,
            "messages": self._normalize_messages(request),
        }

        response = requests.post(self._endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        raw = response.json()
        content = raw["choices"][0]["message"]["content"]

        return InternalLLMResponse(
            content=content,
            provider=self.provider_name,
            model=payload["model"],
            raw_response=raw,
        )
