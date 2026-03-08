"""Registry/factory for provider adapter resolution."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional, Type

from orchestrator.llm_adapters.anthropic_adapter import AnthropicAdapter
from orchestrator.llm_adapters.base import BaseLLMAdapter, InternalLLMRequest
from orchestrator.llm_adapters.endpoint_adapter import EndpointAdapter
from orchestrator.llm_adapters.ollama_adapter import OllamaAdapter
from orchestrator.llm_adapters.vertex_adapter import VertexAdapter


@dataclass(frozen=True)
class ProviderRoutingPolicy:
    """Rules used to infer provider when request.provider is omitted."""

    default_provider: str = os.getenv("LLM_PROVIDER", "endpoint")

    def resolve_provider(self, request: InternalLLMRequest) -> str:
        if request.provider:
            return request.provider

        model = (request.model or "").lower()
        if model.startswith("claude"):
            return "anthropic"
        if model.startswith("gemini"):
            return "vertex"
        if model.startswith("llama") or model.startswith("qwen"):
            return "ollama"

        return self.default_provider


class LLMAdapterRegistry:
    """Factory that returns concrete adapters from provider/model routing policy."""

    def __init__(self, routing_policy: Optional[ProviderRoutingPolicy] = None) -> None:
        self._routing_policy = routing_policy or ProviderRoutingPolicy()
        self._adapters: Dict[str, Type[BaseLLMAdapter]] = {
            "endpoint": EndpointAdapter,
            "anthropic": AnthropicAdapter,
            "vertex": VertexAdapter,
            "ollama": OllamaAdapter,
        }

    def resolve(self, request: InternalLLMRequest) -> BaseLLMAdapter:
        provider = self._routing_policy.resolve_provider(request)
        adapter_cls = self._adapters.get(provider)
        if adapter_cls is None:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        return adapter_cls()
