import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents.coder import CoderAgent


def test_generate_solution_returns_and_persists_artifact(monkeypatch):
    agent = CoderAgent()

    monkeypatch.setattr(agent.db, "get_artifact", lambda _id: SimpleNamespace(content="parent context"))
    async def fake_acall_llm(prompt):
        return f"generated::{prompt}"
    monkeypatch.setattr(agent.llm, "acall_llm", fake_acall_llm)

    saved = {}

    def fake_save(artifact):
        saved["artifact"] = artifact

    monkeypatch.setattr(agent.db, "save_artifact", fake_save)

    artifact = asyncio.run(agent.generate_solution("parent-1", "feedback"))

    assert artifact.type == "code_solution"
    assert artifact.agent_name == "CoderAgent"
    assert artifact.metadata["parent_artifact_id"] == "parent-1"
    assert saved["artifact"].parent_artifact_id == "parent-1"
    assert saved["artifact"].artifact_id == artifact.artifact_id
def test_generate_solution_raises_when_llm_returns_none(monkeypatch):
    agent = CoderAgent()

    monkeypatch.setattr(agent.db, "get_artifact", lambda _id: SimpleNamespace(content="parent context"))
    async def fake_acall_llm(prompt):
        return None
    monkeypatch.setattr(agent.llm, "acall_llm", fake_acall_llm)

    try:
        asyncio.run(agent.generate_solution("parent-1", "feedback"))
    except ValueError as exc:
        assert "cannot create MCPArtifact" in str(exc)
    else:
        raise AssertionError("Expected ValueError when LLM returns None")
