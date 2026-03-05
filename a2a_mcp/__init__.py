"""Core MCP package for shared protocol logic with tenant isolation."""

from a2a_mcp.mcp_core import MCPCore, MCPResult

try:
    from a2a_mcp.client_token_pipe import (
        ClientTokenPipe,
        ClientTokenPipeContext,
        ContaminationError,
        InMemoryEventStore,
    )
except ModuleNotFoundError:
    ClientTokenPipe = None
    ClientTokenPipeContext = None
    ContaminationError = None
    InMemoryEventStore = None

__all__ = [
    "MCPCore",
    "MCPResult",
]

if ClientTokenPipe is not None:
    __all__.extend(
        [
            "ClientTokenPipe",
            "ClientTokenPipeContext",
            "ContaminationError",
            "InMemoryEventStore",
        ]
    )
