"""Core MCP package for shared protocol logic with tenant isolation."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_MCP_EXPORTS = {"MCPCore", "MCPResult", "namespace_project_embedding"}
_PIPE_EXPORTS = {
    "ClientContext",
    "ClientTokenContext",
    "ClientTokenPipe",
    "ContaminationError",
    "EventStoreProtocol",
    "InMemoryEventStore",
}

__all__ = sorted(_MCP_EXPORTS | _PIPE_EXPORTS)


def __getattr__(name: str) -> Any:
    if name in _MCP_EXPORTS:
        module = import_module("a2a_mcp.mcp_core")
        return getattr(module, name)
    if name in _PIPE_EXPORTS:
        module = import_module("a2a_mcp.client_token_pipe")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return __all__
