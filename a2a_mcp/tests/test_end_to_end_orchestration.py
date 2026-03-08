from unittest.mock import patch

from orchestrator.end_to_end_orchestration import EndToEndOrchestrator


def test_end_to_end_orchestration_local(tmp_path):
    block_path = tmp_path / "worldline_block.json"
    result_path = tmp_path / "orchestration_result.json"

    orchestrator = EndToEndOrchestrator(
        prompt="Create multimodal avatar orchestration from prompt",
        repository="adaptco/A2A_MCP",
        commit_sha="abc123",
        actor="tester",
        cluster_count=4,
        authorization="Bearer valid-token",
        output_block_path=str(block_path),
        output_result_path=str(result_path),
    )

    with patch(
        "scripts.knowledge_ingestion.verify_github_oidc_token",
        return_value={"repository": "adaptco/A2A_MCP", "actor": "tester"},
    ):
        result = orchestrator.run()

    assert result["status"] == "success"
    assert result["mcp_mode"] == "local"
    assert block_path.exists()
    assert result_path.exists()
    assert result["token_count"] > 0
