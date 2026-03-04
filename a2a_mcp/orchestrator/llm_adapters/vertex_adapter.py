"""Vertex AI adapter."""
from __future__ import annotations

import os
from typing import Any, Dict

import requests

from orchestrator.llm_adapters.base import BaseLLMAdapter, InternalLLMRequest, InternalLLMResponse


class VertexAdapter(BaseLLMAdapter):
    """Adapter for Vertex AI Gemini endpoints via REST."""

    provider_name = "vertex"

    def __init__(self) -> None:
        self._api_key = os.getenv("VERTEX_API_KEY")
        self._endpoint = os.getenv("VERTEX_ENDPOINT")
        self._default_model = os.getenv("VERTEX_MODEL", "gemini-1.5-pro")

    def generate(self, request: InternalLLMRequest) -> InternalLLMResponse:
        if not self._api_key or not self._endpoint:
            raise ValueError("VERTEX_API_KEY or VERTEX_ENDPOINT missing from environment variables")

        payload: Dict[str, Any] = {
            "model": request.model or self._default_model,
            "system_instruction": {"parts": [{"text": request.system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
        }
        headers = {"Content-Type": "application/json"}
        endpoint = f"{self._endpoint}?key={self._api_key}"

        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        raw = response.json()

        candidates = raw.get("candidates", [])
        parts = []
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
        content = "".join(part.get("text", "") for part in parts)

        return InternalLLMResponse(
            content=content,
            provider=self.provider_name,
            model=payload["model"],
            raw_response=raw,
        )
