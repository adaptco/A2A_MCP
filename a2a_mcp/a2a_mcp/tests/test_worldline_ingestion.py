from unittest.mock import patch

import pytest
pytest.importorskip("fastmcp", reason="Skipping due to rpds-py C-extension environment issue")

from fastmcp import Client

from knowledge_ingestion import app_ingest


@pytest.mark.asyncio
async def test_ingest_worldline_block_success():
    payload = {
        "snapshot": {"repository": "adaptco/A2A_MCP"},
        "infrastructure_agent": {
            "embedding_vector": [0.1, 0.2],
            "token_stream": [{"token": "a", "token_id": "id"}],
            "artifact_clusters": {"cluster_0": ["artifact::a"]},
            "lora_attention_weights": {"cluster_0": 1.0},
        },
    }
    mock_claims = {"repository": "adaptco/A2A_MCP", "actor": "github-actions"}

    with patch("scripts.knowledge_ingestion.verify_github_oidc_token", return_value=mock_claims):
        async with Client(app_ingest) as client:
            response = await client.call_tool(
                "ingest_worldline_block",
                {"worldline_block": payload, "authorization": "Bearer valid-token"},
            )
            text = response.content[0].text if hasattr(response, "content") else response[0].text
            assert "success" in text


@pytest.mark.asyncio
async def test_ingest_worldline_block_missing_fields():
    payload = {
        "snapshot": {"repository": "adaptco/A2A_MCP"},
        "infrastructure_agent": {},
    }
    mock_claims = {"repository": "adaptco/A2A_MCP", "actor": "github-actions"}

    with patch("scripts.knowledge_ingestion.verify_github_oidc_token", return_value=mock_claims):
        async with Client(app_ingest) as client:
            response = await client.call_tool(
                "ingest_worldline_block",
                {"worldline_block": payload, "authorization": "Bearer valid-token"},
            )
            text = response.content[0].text if hasattr(response, "content") else response[0].text
            assert "missing required fields" in text
