"""Ollama adapter."""
from __future__ import annotations

import os
from typing import Any, Dict

import requests

from orchestrator.llm_adapters.base import BaseLLMAdapter, InternalLLMRequest, InternalLLMResponse


class OllamaAdapter(BaseLLMAdapter):
    """Adapter for local Ollama chat API."""

    provider_name = "ollama"

    def __init__(self) -> None:
        self._endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/api/chat")
        self._default_model = os.getenv("OLLAMA_MODEL", "llama3.1")

    def generate(self, request: InternalLLMRequest) -> InternalLLMResponse:
        payload: Dict[str, Any] = {
            "model": request.model or self._default_model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ],
            "stream": False,
        }

        response = requests.post(self._endpoint, json=payload, timeout=60)
        response.raise_for_status()
        raw = response.json()
        content = raw.get("message", {}).get("content", "")

        return InternalLLMResponse(
            content=content,
            provider=self.provider_name,
            model=payload["model"],
            raw_response=raw,
        )
