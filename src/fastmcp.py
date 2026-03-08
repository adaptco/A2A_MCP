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
        await self.close()
        return False

    async def close(self):
        closer = getattr(self.app, "close", None)
        if callable(closer):
            result = closer()
            if inspect.isawaitable(result):
                await result

    @staticmethod
    def _coerce_callable(candidate: Any) -> Callable[..., Any] | None:
        if callable(candidate):
            return candidate
        for attr in ("fn", "func", "function", "callable"):
            value = getattr(candidate, attr, None)
            if callable(value):
                return value
        run_method = getattr(candidate, "run", None)
        if callable(run_method):
            return run_method
        return None

    def _resolve_tool_callable(self, name: str) -> Callable[..., Any] | None:
        for attr in ("_tools", "tools"):
            mapping = getattr(self.app, attr, None)
            if isinstance(mapping, dict) and name in mapping:
                return self._coerce_callable(mapping[name])

        tool_manager = getattr(self.app, "_tool_manager", None)
        if tool_manager is not None:
            for attr in ("_tools", "tools"):
                mapping = getattr(tool_manager, attr, None)
                if isinstance(mapping, dict) and name in mapping:
                    return self._coerce_callable(mapping[name])

            getter = getattr(tool_manager, "get_tool", None)
            if callable(getter):
                try:
                    return self._coerce_callable(getter(name))
                except Exception:
                    return None
        return None

    async def call_tool(self, name: str, payload: dict):
        fn = self._resolve_tool_callable(name)
        if fn is None:
            call_tool = getattr(self.app, "call_tool", None)
            if callable(call_tool):
                result = call_tool(name, payload)
                if inspect.isawaitable(result):
                    result = await result
                if hasattr(result, "content"):
                    return result
                return ToolResponse(content=[_TextBlock(text=str(result))])
            raise KeyError(f"Tool '{name}' was not found on app '{self.app}'.")

        try:
            result = fn(**payload)
        except TypeError:
            result = fn(payload)

        if inspect.isawaitable(result):
            result = await result
        return ToolResponse(content=[_TextBlock(text=str(result))])
