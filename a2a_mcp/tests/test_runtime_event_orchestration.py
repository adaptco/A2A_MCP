from orchestrator.adapter_normalizer import normalize_provider_response
from orchestrator.stateflow import State, StateMachine
from schemas.runtime_event import EventPayload, RuntimeEvent, ToolRequest


def test_normalize_provider_response_with_tool_call() -> None:
    provider_obj = {
        "content": "I need a tool",
        "tool_calls": [{"name": "search_docs", "arguments": {"q": "stateflow"}}],
    }

    event = normalize_provider_response(
        provider_obj,
        trace_id="trace-123",
        parent_span_id="span-parent",
        provider="mock-sdk",
    )

    assert event.event_type == "AGENT_RESPONSE"
    assert event.trace_id == "trace-123"
    assert event.parent_span_id == "span-parent"
    assert event.content.tool_request is not None
    assert event.content.tool_request.tool_name == "search_docs"
    assert event.content.status == "tool_request"


def test_consume_agent_response_branches_to_tool_invoke() -> None:
    sm = StateMachine(max_retries=2)
    sm.trigger("OBJECTIVE_INGRESS")
    sm.trigger("RUN_DISPATCHED")
    sm.trigger("EXECUTION_COMPLETE")

    event = RuntimeEvent(
        trace_id="trace-001",
        span_id="span-001",
        parent_span_id="span-000",
        event_type="AGENT_RESPONSE",
        content=EventPayload(
            content="Call tool",
            tool_request=ToolRequest(tool_name="lookup", arguments={"id": 7}),
            status="tool_request",
        ),
    )

    rec = sm.consume_runtime_event(event)
    assert sm.current_state() == State.TOOL_INVOKE
    assert rec.meta["trace_id"] == "trace-001"
    assert rec.meta["span_id"] == "span-001"


def test_consume_agent_response_success_to_terminal() -> None:
    sm = StateMachine(max_retries=2)
    sm.trigger("OBJECTIVE_INGRESS")
    sm.trigger("RUN_DISPATCHED")
    sm.trigger("EXECUTION_COMPLETE")

    event = RuntimeEvent(
        trace_id="trace-002",
        span_id="span-002",
        event_type="AGENT_RESPONSE",
        content=EventPayload(content="done", status="success"),
    )

    sm.consume_runtime_event(event)
    assert sm.current_state() == State.TERMINATED_SUCCESS


def test_build_next_hop_preserves_trace_and_rolls_span() -> None:
    sm = StateMachine()
    source = RuntimeEvent(
        trace_id="trace-hop",
        span_id="span-origin",
        event_type="AGENT_RESPONSE",
        content=EventPayload(content="source"),
    )

    child = sm.build_next_hop_event(
        source,
        event_type="TOOL_RESULT",
        payload=EventPayload(content={"result": "ok"}),
    )

    assert child.trace_id == "trace-hop"
    assert child.parent_span_id == "span-origin"
    assert child.span_id != "span-origin"
    assert child.event_type == "TOOL_RESULT"
