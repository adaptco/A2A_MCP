from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Dict


@dataclass
class _TextBlock:
    text: str


@dataclass
class ToolResponse:
    content: list[_TextBlock]


class FastMCP:
    def __init__(self, name: str):
        self.name = name
        self._tools: Dict[str, Callable[..., Any]] = {}

    def tool(self):
        def decorator(fn: Callable[..., Any]):
            self._tools[fn.__name__] = fn
            return fn

        return decorator


class Client:
    def __init__(self, app: FastMCP):
        self.app = app

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def call_tool(self, name: str, payload: dict):
        fn = self.app._tools[name]
        result = fn(**payload)
        if inspect.isawaitable(result):
            result = await result
        return ToolResponse(content=[_TextBlock(text=str(result))])
