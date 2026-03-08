"""Compatibility layer exposing shared MCP core under `orchestrator`."""

from a2a_mcp.mcp_core import MCPResult, MCPCore, namespace_project_embedding

__all__ = ["MCPResult", "MCPCore", "namespace_project_embedding"]
