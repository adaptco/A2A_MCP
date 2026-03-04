"""Core MCP package for shared protocol logic with tenant isolation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from a2a_mcp.client_token_pipe import (
        ClientTokenPipe,
        ClientTokenContext,
        ContaminationError,
        InMemoryEventStore,
    )
<<<<<<< Updated upstream
except ModuleNotFoundError:
    ClientTokenPipe = None
    ClientTokenContext = None
    ContaminationError = None
    InMemoryEventStore = None
=======
    from a2a_mcp.mcp_core import MCPCore, MCPResult
>>>>>>> Stashed changes

__all__ = [
    "MCPCore",
    "MCPResult",
    "ClientTokenPipe",
    "ClientTokenPipeContext",
    "ContaminationError",
    "InMemoryEventStore",
]

<<<<<<< Updated upstream
if ClientTokenPipe is not None:
    __all__.extend(
        [
            "ClientTokenPipe",
            "ClientTokenContext",
            "ContaminationError",
            "InMemoryEventStore",
        ]
    )
=======

def __getattr__(name: str) -> Any:
    if name in {"MCPCore", "MCPResult"}:
        from a2a_mcp import mcp_core as _mcp_core

        return getattr(_mcp_core, name)

    if name in {
        "ClientTokenPipe",
        "ClientTokenPipeContext",
        "ContaminationError",
        "InMemoryEventStore",
    }:
        try:
            from a2a_mcp import client_token_pipe as _client_token_pipe
        except ModuleNotFoundError as exc:
            raise AttributeError(
                f"{name} is unavailable because an optional dependency is missing: {exc.name}"
            ) from exc

        return getattr(_client_token_pipe, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
>>>>>>> Stashed changes
