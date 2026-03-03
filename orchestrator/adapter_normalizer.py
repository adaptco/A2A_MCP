"""Provider adapter normalization into canonical runtime envelopes."""

from __future__ import annotations

from typing import Any, Dict
from uuid import uuid4

from schemas.runtime_event import EventPayload, RuntimeEvent, ToolRequest


def normalize_provider_response(
    provider_response: Any,
    *,
    trace_id: str,
    parent_span_id: str | None = None,
    provider: str | None = None,
) -> RuntimeEvent:
    """Convert arbitrary provider SDK response objects to canonical RuntimeEvent."""

    raw = _object_to_dict(provider_response)
    tool_request = _extract_tool_request(raw)
    content = _extract_content(raw)
    status = _extract_status(raw, tool_request=tool_request)

    payload = EventPayload(
        content=content,
        tool_request=tool_request,
        status=status,
        provider=provider,
        raw=raw,
    )

    return RuntimeEvent(
        trace_id=trace_id,
        span_id=uuid4().hex,
        parent_span_id=parent_span_id,
        event_type="AGENT_RESPONSE",
        content=payload,
    )


def _object_to_dict(provider_response: Any) -> Dict[str, Any]:
    if provider_response is None:
        return {}
    if isinstance(provider_response, dict):
        return provider_response
    if hasattr(provider_response, "model_dump"):
        return provider_response.model_dump(mode="json")
    if hasattr(provider_response, "dict"):
        return provider_response.dict()
    if hasattr(provider_response, "__dict__"):
        return dict(provider_response.__dict__)
    return {"value": provider_response}


def _extract_tool_request(raw: Dict[str, Any]) -> ToolRequest | None:
    tool_call = raw.get("tool_request")
    if not tool_call:
        tool_calls = raw.get("tool_calls") or []
        tool_call = tool_calls[0] if tool_calls else None
    if not isinstance(tool_call, dict):
        return None

    tool_name = tool_call.get("tool_name") or tool_call.get("name") or tool_call.get("tool")
    if not tool_name:
        return None

    args = tool_call.get("arguments") or tool_call.get("args") or {}
    if not isinstance(args, dict):
        args = {"value": args}

    return ToolRequest(tool_name=str(tool_name), arguments=args)


def _extract_content(raw: Dict[str, Any]) -> Any:
    if "content" in raw:
        return raw.get("content")
    if "message" in raw:
        return raw.get("message")
    choices = raw.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict) and "content" in message:
            return message["content"]
    return raw


def _extract_status(raw: Dict[str, Any], *, tool_request: ToolRequest | None) -> str:
    if tool_request is not None:
        return "tool_request"

    explicit_status = raw.get("status")
    if isinstance(explicit_status, str) and explicit_status:
        return explicit_status.lower()

    if raw.get("error"):
        return "failed"
    return "success"
