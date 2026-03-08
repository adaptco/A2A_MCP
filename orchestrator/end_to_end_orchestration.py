"""End-to-end orchestration runner for Qube multimodal worldline processing."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from mcp.client import Client

from knowledge_ingestion import app_ingest
from orchestrator.multimodal_worldline import build_worldline_block, serialize_worldline_block


def _extract_tool_text(response: Any) -> str:
    """Normalize fastmcp call_tool responses across client versions."""
    if hasattr(response, "content") and response.content:
        return str(response.content[0].text)
    if isinstance(response, list) and response:
        return str(response[0].text)
    return str(response)


@dataclass
class EndToEndOrchestrationResult:
    status: str
    mcp_mode: str
    ingestion_status: str
    token_count: int
    cluster_count: int
    output_block_path: str
    output_result_path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EndToEndOrchestrator:
    """Run prompt-to-MCP orchestration with local or remote MCP transport."""

    def __init__(
        self,
        *,
        prompt: str,
        repository: str,
        commit_sha: str,
        actor: str = "github-actions",
        cluster_count: int = 4,
        authorization: str = "Bearer valid-token",
        mcp_api_url: Optional[str] = None,
        output_block_path: str = "worldline_block.json",
        output_result_path: str = "orchestration_result.json",
    ) -> None:
        self.prompt = prompt
        self.repository = repository
        self.commit_sha = commit_sha
        self.actor = actor
        self.cluster_count = int(cluster_count)
        self.authorization = authorization
        self.mcp_api_url = mcp_api_url
        self.output_block_path = Path(output_block_path)
        self.output_result_path = Path(output_result_path)

    async def _ingest_local(self, worldline_payload: Dict[str, Any]) -> str:
        async with Client(app_ingest) as client:
            response = await client.call_tool(
                "ingest_worldline_block",
                {"worldline_block": worldline_payload, "authorization": self.authorization},
            )
        return _extract_tool_text(response)

    def _ingest_remote(self, worldline_payload: Dict[str, Any]) -> str:
        if not self.mcp_api_url:
            return "error: missing mcp_api_url"
        endpoint = f"{self.mcp_api_url.rstrip('/')}/tools/call"
        payload = {
            "tool_name": "ingest_worldline_block",
            "arguments": {"worldline_block": worldline_payload, "authorization": self.authorization},
        }
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Authorization": self.authorization, "Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return response.text

    def run(self) -> Dict[str, Any]:
        """Build worldline, ingest through MCP, and persist artifacts."""
        block = build_worldline_block(
            prompt=self.prompt,
            repository=self.repository,
            commit_sha=self.commit_sha,
            actor=self.actor,
            cluster_count=self.cluster_count,
        )
        worldline_payload = {
            "snapshot": block["snapshot"],
            "infrastructure_agent": block["infrastructure_agent"],
        }

        self.output_block_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_block_path.write_text(serialize_worldline_block(block), encoding="utf-8")

        if self.mcp_api_url:
            mcp_mode = "remote"
            ingestion_status = self._ingest_remote(worldline_payload)
        else:
            mcp_mode = "local"
            ingestion_status = asyncio.run(self._ingest_local(worldline_payload))

        status = "success" if "success" in ingestion_status.lower() else "failed"
        result = EndToEndOrchestrationResult(
            status=status,
            mcp_mode=mcp_mode,
            ingestion_status=ingestion_status,
            token_count=len(block["infrastructure_agent"]["token_stream"]),
            cluster_count=len(block["infrastructure_agent"]["artifact_clusters"]),
            output_block_path=str(self.output_block_path),
            output_result_path=str(self.output_result_path),
        )
        self.output_result_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_result_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        return result.to_dict()
