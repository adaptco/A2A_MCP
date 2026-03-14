"""FastAPI app for orchestrator HTTP endpoints and plan ingress routes."""

from __future__ import annotations

import logging
import os
<<<<<<< HEAD
from typing import Any, Optional
=======
import time
from collections import OrderedDict
from typing import Any, Callable, Optional
>>>>>>> origin/main
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Depends, Header, Request

from app.api import actions_router, workflow_router
from orchestrator.intent_engine import IntentEngine
from orchestrator.webhook import ingress_router
from orchestrator.auth import authenticate_user
from orchestrator.logging_util import setup_logging
from orchestrator.actions_gateway import router as actions_router
from orchestrator.option_b import (
    OptionBConfigError,
    OptionBRemoteError,
    OptionBService,
    OrchestrateCommandRequest,
    parse_command,
    new_run_id,
)

setup_logging()

def validate_orchestrator_config():
    """Fail-fast on missing critical environment variables."""
    if os.getenv("ENV") == "production":
        if not os.getenv("LLM_API_KEY"):
            raise RuntimeError("LLM_API_KEY is required in production.")
        if not os.getenv("LLM_ENDPOINT"):
            raise RuntimeError("LLM_ENDPOINT is required in production.")

validate_orchestrator_config()

logger = logging.getLogger(__name__)
_IDEMPOTENCY_CACHE: dict[str, dict[str, Any]] = {}


class _IdempotencyCache:
    """Bounded in-memory idempotency cache with TTL and LRU eviction."""

    def __init__(
        self,
        *,
        ttl_seconds: int,
        max_entries: int,
        now_fn: Callable[[], float] = time.time,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.now_fn = now_fn
        self._entries: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()

    def _evict_expired(self, now: float) -> None:
        expired_keys = [
            key for key, item in self._entries.items() if item["expires_at"] <= now
        ]
        for key in expired_keys:
            self._entries.pop(key, None)

    def get(self, *, idempotency_key: str, actor: str) -> dict[str, Any] | None:
        now = self.now_fn()
        self._evict_expired(now)
        key = (idempotency_key, actor)
        item = self._entries.get(key)
        if item is None:
            return None
        self._entries.move_to_end(key)
        return item["response"]

    def set(self, *, idempotency_key: str, actor: str, response: dict[str, Any]) -> None:
        now = self.now_fn()
        self._evict_expired(now)
        key = (idempotency_key, actor)
        if key in self._entries:
            self._entries.pop(key, None)
        self._entries[key] = {
            "response": response,
            "cached_at": now,
            "expires_at": now + self.ttl_seconds,
            "actor": actor,
            "idempotency_key": idempotency_key,
        }
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()


_IDEMPOTENCY_CACHE = _IdempotencyCache(
    ttl_seconds=int(os.getenv("ORCHESTRATOR_IDEMPOTENCY_TTL_SECONDS", "300")),
    max_entries=int(os.getenv("ORCHESTRATOR_IDEMPOTENCY_MAX_ENTRIES", "1024")),
)

app = FastAPI(title="A2A Orchestrator API", version="1.0.0")
app.include_router(ingress_router)
app.include_router(actions_router)
app.include_router(workflow_router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


def _build_pipeline_response(result: Any) -> dict[str, Any]:
    test_summary = "\n".join(
        f"- {item['artifact']}: {item['status']} (score={item['judge_score']})"
        for item in result.test_verdicts
    )
    final_code = result.code_artifacts[-1].content if result.code_artifacts else ""
    return {
        "status": "A2A Workflow Complete" if result.success else "A2A Workflow Incomplete",
        "pipeline_results": {
            "plan_id": result.plan.plan_id,
            "blueprint_id": result.blueprint.plan_id,
            "research": [artifact.artifact_id for artifact in result.architecture_artifacts],
            "coding": [artifact.artifact_id for artifact in result.code_artifacts],
            "testing": result.test_verdicts,
        },
        "test_summary": test_summary,
        "final_code": final_code,
    }


def _resolve_requester(auth: dict[str, Any], requester: str) -> str:
    return str(auth.get("actor") or requester or "api")


def _response_with_option_b_fields(
    *,
    base: dict[str, Any],
    run_id: str,
    routing_decision: dict[str, Any],
    airtable_record_id: str | None,
    slack_post_status: str,
    trace_id: str,
) -> dict[str, Any]:
    merged = dict(base)
    merged.update(
        {
            "run_id": run_id,
            "routing_decision": routing_decision,
            "airtable_record_id": airtable_record_id,
            "slack_post_status": slack_post_status,
            "trace_id": trace_id,
        }
    )
    return merged


@app.post("/orchestrate")
async def orchestrate(
    request: Request,
    payload: Optional[OrchestrateCommandRequest] = None,
    user_query: str | None = Query(default=None, min_length=1),
    requester: str = Query(default="api"),
    max_healing_retries: int = Query(default=3, ge=1, le=10),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    auth: dict = Depends(authenticate_user),
) -> dict[str, Any]:
    """Run the full multi-agent pipeline for a user query."""
<<<<<<< HEAD
    if x_idempotency_key and x_idempotency_key in _IDEMPOTENCY_CACHE:
        return _IDEMPOTENCY_CACHE[x_idempotency_key]

    trace_id = str(request.headers.get("x-request-id") or request.headers.get("x-correlation-id") or uuid4())
    resolved_requester = _resolve_requester(auth, requester)

=======
    trace_id = str(request.headers.get("x-request-id") or request.headers.get("x-correlation-id") or uuid4())
    resolved_requester = _resolve_requester(auth, requester)

    if x_idempotency_key:
        cached_response = _IDEMPOTENCY_CACHE.get(
            idempotency_key=x_idempotency_key,
            actor=resolved_requester,
        )
        if cached_response is not None:
            return cached_response

>>>>>>> origin/main
    optionb_service: OptionBService | None = None
    run_id: str | None = None
    run_record_id: str | None = None
    routing_decision: dict[str, Any] = {}
    slack_post_status = "skipped"

    try:
        description = user_query or ""

        if payload is not None:
            command = parse_command(payload.command, payload.args)
            description = command.description
            run_id = new_run_id()

            optionb_service = OptionBService.from_env()
            routing_decision = await optionb_service.select_routing(operation=command.operation)

            run_record_id = await optionb_service.create_run_record(
                run_payload=optionb_service.build_initial_run_payload(
                    run_id=run_id,
                    trace_id=trace_id,
                    command=command,
                    requester=resolved_requester,
                    routing_decision=routing_decision,
                )
            )
            await optionb_service.update_run_record(
                record_id=run_record_id,
                fields={"status": "running"},
            )

            if payload.slack is not None:
                ack = await optionb_service.post_slack_message(
                    channel_id=payload.slack.channel_id,
                    thread_ts=payload.slack.thread_ts,
                    text=(
                        f"ACK `{command.normalized_command}` "
                        f"(run_id={run_id}, trace_id={trace_id}) "
                        f"routed to {routing_decision.get('selected_agent', 'unknown')}"
                    ),
                )
                slack_post_status = "sent" if ack.get("ok") else "failed"
        else:
            if not description:
                raise HTTPException(
                    status_code=400,
                    detail="Provide either query param `user_query` or JSON body payload with `command`.",
                )

        engine = IntentEngine()
        result = await engine.run_full_pipeline(
            description=description,
            requester=resolved_requester,
            max_healing_retries=max_healing_retries,
        )
        response = _build_pipeline_response(result)

        if optionb_service is not None and run_record_id:
            await optionb_service.update_run_record(
                record_id=run_record_id,
                fields={
                    "status": "success" if result.success else "failed",
                    "pipeline_status": response.get("status", ""),
                },
            )
            if payload is not None and payload.slack is not None:
                slack_result = await optionb_service.post_slack_message(
                    channel_id=payload.slack.channel_id,
                    thread_ts=payload.slack.thread_ts,
                    text=(
                        f"RESULT `{payload.command}` "
                        f"status={response.get('status')} "
                        f"plan={response.get('pipeline_results', {}).get('plan_id', 'n/a')} "
                        f"trace_id={trace_id}"
                    ),
                )
                slack_post_status = "sent" if slack_result.get("ok") else "failed"

            response = _response_with_option_b_fields(
                base=response,
                run_id=run_id or "",
                routing_decision=routing_decision,
                airtable_record_id=run_record_id,
                slack_post_status=slack_post_status,
                trace_id=trace_id,
            )

        if x_idempotency_key:
<<<<<<< HEAD
            _IDEMPOTENCY_CACHE[x_idempotency_key] = response
=======
            _IDEMPOTENCY_CACHE.set(
                idempotency_key=x_idempotency_key,
                actor=resolved_requester,
                response=response,
            )
>>>>>>> origin/main
        return response
    except (OptionBConfigError, OptionBRemoteError) as exc:
        logger.exception("option-b orchestration failure")
        if optionb_service is not None and run_record_id:
            try:
                await optionb_service.update_run_record(
                    record_id=run_record_id,
                    fields={
                        "status": "failed",
                        "error_code": exc.code,
                        "error_detail": exc.message,
                    },
                )
            except Exception:  # noqa: BLE001
                logger.exception("failed to persist option-b failure state")
        status_code = 400 if isinstance(exc, OptionBConfigError) and exc.code == "OPTB_INVALID_COMMAND" else 503
        raise HTTPException(
            status_code=status_code,
            detail={"error_code": exc.code, "message": exc.message, "trace_id": trace_id},
        ) from None
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 - Catch all to mask internal errors.
        logger.exception("orchestration failure")
        if optionb_service is not None and run_record_id:
            try:
                await optionb_service.update_run_record(
                    record_id=run_record_id,
                    fields={
                        "status": "failed",
                        "error_code": "OPTB_ORCHESTRATION_ERROR",
                    },
                )
            except Exception:  # noqa: BLE001
                logger.exception("failed to persist option-b run failure")
        raise HTTPException(
            status_code=500, detail="orchestration failure: an internal error occurred"
        ) from None
    finally:
        if optionb_service is not None:
            await optionb_service.aclose()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "orchestrator.api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
