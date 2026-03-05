"""Core MCP package exports with lazy loading for optional modules."""

from __future__ import annotations

from typing import Any

__all__ = [
    "MCPCore",
    "MCPResult",
    "ClientTokenPipe",
    "ClientTokenContext",
    "ClientTokenPipeContext",
    "ContaminationError",
    "InMemoryEventStore",
]


def __getattr__(name: str) -> Any:
    if name in {"MCPCore", "MCPResult"}:
        from a2a_mcp import mcp_core as _mcp_core

        return getattr(_mcp_core, name)

    if name in {
        "ClientTokenPipe",
        "ClientTokenContext",
        "ClientTokenPipeContext",
        "ContaminationError",
        "InMemoryEventStore",
    }:
        from a2a_mcp import client_token_pipe as _client_token_pipe

        if name == "ClientTokenPipeContext":
            return getattr(_client_token_pipe, "ClientTokenContext")
        return getattr(_client_token_pipe, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)

