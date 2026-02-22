import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents.coder import CoderAgent


def test_generate_solution_returns_and_persists_artifact(monkeypatch):
    agent = CoderAgent()

    monkeypatch.setattr(agent.db, "get_artifact", lambda _id: SimpleNamespace(content="parent context"))
    monkeypatch.setattr(agent.llm, "call_llm", lambda prompt: f"generated::{prompt}")

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
