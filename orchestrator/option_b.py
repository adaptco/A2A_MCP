"""Option-B orchestration helpers for Airtable-driven routing and Slack replies."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field


class OptionBConfigError(RuntimeError):
    """Missing or invalid Option-B configuration."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class OptionBRemoteError(RuntimeError):
    """External integration failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class SlackTarget(BaseModel):
    model_config = ConfigDict(extra="ignore")

    channel_id: str = Field(min_length=1)
    thread_ts: str | None = None


class OrchestrateCommandRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    command: str = Field(min_length=1)
    args: str | None = None
    slack: SlackTarget | None = None


@dataclass(frozen=True)
class ParsedCommand:
    normalized_command: str
    operation: str
    args: str | None
    description: str


def parse_command(raw_command: str, raw_args: str | None = None) -> ParsedCommand:
    command = (raw_command or "").strip()
    if not command:
        raise OptionBConfigError("OPTB_INVALID_COMMAND", "command must not be empty")

    tokenized = command[1:] if command.startswith("!") else command
    parts = [p for p in tokenized.split(" ") if p]
    if not parts:
        raise OptionBConfigError("OPTB_INVALID_COMMAND", "command must include an operation")

    operation = parts[0].lower()
    if operation not in {"run", "triage", "deploy"}:
        raise OptionBConfigError(
            "OPTB_INVALID_COMMAND",
            "unsupported command; expected one of !run, !triage, !deploy",
        )

    inline_args = " ".join(parts[1:]).strip() or None
    args = (raw_args.strip() if raw_args is not None else inline_args) or None
    description = f"{operation} {args}".strip() if args else operation
    return ParsedCommand(
        normalized_command=f"!{operation}",
        operation=operation,
        args=args,
        description=description,
    )


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on", "enabled"}


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


class OptionBService:
    """Coordinates Airtable routing/run-logging and Slack replies."""

    def __init__(
        self,
        *,
        airtable_pat: str,
        airtable_base_id: str,
        airtable_selector_table: str,
        airtable_runs_table: str,
        slack_bot_token: str | None,
        airtable_api_base_url: str,
        slack_api_base_url: str,
    ) -> None:
        self.airtable_pat = airtable_pat
        self.airtable_base_id = airtable_base_id
        self.airtable_selector_table = airtable_selector_table
        self.airtable_runs_table = airtable_runs_table
        self.slack_bot_token = slack_bot_token
        self.airtable_api_base_url = airtable_api_base_url.rstrip("/")
        self.slack_api_base_url = slack_api_base_url.rstrip("/")
        self._http = httpx.AsyncClient(timeout=30)

    @classmethod
    def from_env(cls) -> "OptionBService":
        airtable_pat = (os.getenv("AIRTABLE_PAT") or os.getenv("AIRTABLE_API_KEY") or "").strip()
        airtable_base_id = (os.getenv("AIRTABLE_BASE_ID") or "").strip()
        if not airtable_pat:
            raise OptionBConfigError("OPTB_MISSING_AIRTABLE_PAT", "missing AIRTABLE_PAT (or AIRTABLE_API_KEY)")
        if not airtable_base_id:
            raise OptionBConfigError("OPTB_MISSING_AIRTABLE_BASE_ID", "missing AIRTABLE_BASE_ID")

        return cls(
            airtable_pat=airtable_pat,
            airtable_base_id=airtable_base_id,
            airtable_selector_table=(os.getenv("AIRTABLE_AGENT_MIXTURE_TABLE") or "agent_mixture").strip(),
            airtable_runs_table=(os.getenv("AIRTABLE_AGENT_RUNS_TABLE") or "agent_runs").strip(),
            slack_bot_token=(os.getenv("SLACK_BOT_TOKEN") or "").strip() or None,
            airtable_api_base_url=(os.getenv("AIRTABLE_API_BASE_URL") or "https://api.airtable.com/v0").strip(),
            slack_api_base_url=(os.getenv("SLACK_API_BASE_URL") or "https://slack.com/api").strip(),
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    def _airtable_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.airtable_pat}",
            "Content-Type": "application/json",
        }

    def _airtable_table_url(self, table_name: str) -> str:
        return f"{self.airtable_api_base_url}/{self.airtable_base_id}/{quote(table_name, safe='')}"

    async def select_routing(self, *, operation: str) -> dict[str, Any]:
        url = self._airtable_table_url(self.airtable_selector_table)
        try:
            response = await self._http.get(url, headers=self._airtable_headers())
        except Exception as exc:  # noqa: BLE001
            raise OptionBRemoteError("OPTB_AIRTABLE_UNREACHABLE", f"airtable read failed: {exc}") from exc
        if response.status_code >= 400:
            raise OptionBRemoteError(
                "OPTB_AIRTABLE_READ_FAILED",
                f"airtable read failed with status {response.status_code}",
            )

        data = response.json()
        records = data.get("records", [])
        candidates: list[dict[str, Any]] = []
        for record in records:
            fields = record.get("fields", {})
            enabled = fields.get("enabled")
            if enabled is None:
                enabled = fields.get("active_flag", True)
            if not _truthy(enabled):
                continue

            scopes = fields.get("task_scope")
            if isinstance(scopes, str):
                scopes = [x.strip() for x in scopes.split(",") if x.strip()]
            if not isinstance(scopes, list):
                scopes = []
            scope_text = {str(item).strip().lower() for item in scopes if str(item).strip()}
            match = (operation in scope_text) or ("all" in scope_text) or (not scope_text)

            weight = _safe_float(fields.get("weight_pct", 0))
            score = weight + (100.0 if match else 0.0)
            candidates.append(
                {
                    "record_id": record.get("id"),
                    "agent_id": fields.get("agent_id") or fields.get("name") or "unknown",
                    "model_string": fields.get("model_string") or "",
                    "weight_pct": weight,
                    "task_scope": sorted(scope_text),
                    "enabled": True,
                    "scope_match": match,
                    "score": score,
                }
            )

        candidates = [item for item in candidates if item["scope_match"]]
        if not candidates:
            raise OptionBRemoteError(
                "OPTB_NO_AGENT_CANDIDATES",
                "no enabled routing candidates found in agent_mixture",
            )

        candidates = sorted(
            candidates,
            key=lambda item: (-item["score"], -item["weight_pct"], str(item["agent_id"]).lower()),
        )
        top = candidates[0]
        return {
            "operation": operation,
            "selected_agent": top["agent_id"],
            "model_string": top["model_string"],
            "weight_pct": top["weight_pct"],
            "routing_table_record_id": top["record_id"],
            "candidate_count": len(candidates),
        }

    async def create_run_record(self, *, run_payload: dict[str, Any]) -> str:
        url = self._airtable_table_url(self.airtable_runs_table)
        body = {"records": [{"fields": run_payload}]}
        try:
            response = await self._http.post(url, headers=self._airtable_headers(), json=body)
        except Exception as exc:  # noqa: BLE001
            raise OptionBRemoteError("OPTB_AIRTABLE_WRITE_FAILED", f"airtable write failed: {exc}") from exc
        if response.status_code >= 400:
            raise OptionBRemoteError(
                "OPTB_AIRTABLE_WRITE_FAILED",
                f"airtable write failed with status {response.status_code}",
            )
        payload = response.json()
        return payload.get("records", [{}])[0].get("id", "")

    async def update_run_record(self, *, record_id: str, fields: dict[str, Any]) -> None:
        if not record_id:
            return
        url = self._airtable_table_url(self.airtable_runs_table)
        body = {"records": [{"id": record_id, "fields": fields}]}
        try:
            response = await self._http.patch(url, headers=self._airtable_headers(), json=body)
        except Exception as exc:  # noqa: BLE001
            raise OptionBRemoteError("OPTB_AIRTABLE_WRITE_FAILED", f"airtable write failed: {exc}") from exc
        if response.status_code >= 400:
            raise OptionBRemoteError(
                "OPTB_AIRTABLE_WRITE_FAILED",
                f"airtable write failed with status {response.status_code}",
            )

    async def post_slack_message(
        self,
        *,
        channel_id: str,
        text: str,
        thread_ts: str | None = None,
    ) -> dict[str, Any]:
        if not self.slack_bot_token:
            return {"ok": False, "error": "missing_slack_bot_token"}

        payload: dict[str, Any] = {"channel": channel_id, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        headers = {
            "Authorization": f"Bearer {self.slack_bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        try:
            response = await self._http.post(
                f"{self.slack_api_base_url}/chat.postMessage",
                headers=headers,
                json=payload,
            )
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"slack_request_failed:{exc}"}

        data = response.json() if response.content else {}
        if response.status_code >= 400:
            return {"ok": False, "error": data.get("error") or f"http_{response.status_code}"}
        return {
            "ok": bool(data.get("ok")),
            "error": data.get("error"),
            "ts": data.get("ts"),
            "channel": data.get("channel"),
        }

    @staticmethod
    def build_initial_run_payload(
        *,
        run_id: str,
        trace_id: str,
        command: ParsedCommand,
        requester: str,
        routing_decision: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "trace_id": trace_id,
            "status": "queued",
            "command": command.normalized_command,
            "operation": command.operation,
            "args": command.args or "",
            "requester": requester,
            "routing_decision": str(routing_decision),
        }


def new_run_id() -> str:
    return f"run-{uuid.uuid4()}"
