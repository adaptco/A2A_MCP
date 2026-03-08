"""Base contracts and DTOs for LLM adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class InternalLLMMessage:
    """Normalized chat message passed to adapter implementations."""

    role: str
    content: str


@dataclass(frozen=True)
class InternalLLMRequest:
    """Provider-agnostic generation request used by orchestration services."""

    prompt: str
    system_prompt: str = "You are a helpful coding assistant."
    provider: Optional[str] = None
    model: Optional[str] = None
    messages: Optional[List[InternalLLMMessage]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InternalLLMResponse:
    """Provider-agnostic generation response returned by adapters."""

    content: str
    provider: str
    model: str
    raw_response: Any = None


class BaseLLMAdapter(ABC):
    """Strict interface every concrete adapter must implement."""

    provider_name: str

    @abstractmethod
    def generate(self, request: InternalLLMRequest) -> InternalLLMResponse:
        """Generate a response using a concrete provider transport."""
