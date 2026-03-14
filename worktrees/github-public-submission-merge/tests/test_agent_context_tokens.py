from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from agents.coder import CoderAgent
from agents.tester import TesterAgent


def test_coder_agent_consumes_context_tokens_in_llm_prompt():
    agent = CoderAgent()
    agent.db = MagicMock()
    agent.db.get_artifact.return_value = SimpleNamespace(content="Prior architecture context")
    agent.db.save_artifact.return_value = None

    captured = {}

    def fake_call_llm(prompt: str, system_prompt: str = ""):
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt
        return "def build():\n    return True"

    agent.llm.call_llm = fake_call_llm

    tokens = [
        SimpleNamespace(
            token_id="tok-1",
            source_artifact_id="arch-1",
            score=0.91,
            text="Use parameterized SQL queries and strict input validation.",
        )
    ]

    asyncio.run(
        agent.generate_solution(
            parent_id="plan-ctx-1",
            feedback="Build the repository layer",
            context_tokens=tokens,
        )
    )

    assert "Runtime Context Tokens" in captured["prompt"]
    assert "tok-1" in captured["prompt"]
    assert "parameterized SQL queries" in captured["prompt"]
    assert "Use runtime context tokens as grounding" in captured["system_prompt"]


def test_tester_agent_consumes_context_tokens_in_llm_prompt():
    agent = TesterAgent()
    agent.db = MagicMock()
    agent.db.get_artifact.return_value = SimpleNamespace(content="def query_user(user_id): pass")

    captured = {}

    def fake_call_llm(prompt: str, system_prompt: str = ""):
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt
        return "All checks passed"

    agent.llm.call_llm = fake_call_llm

    tokens = [
        SimpleNamespace(
            token_id="tok-2",
            source_artifact_id="arch-2",
            score=0.88,
            text="All database access must be parameterized and validated.",
        )
    ]

    report = asyncio.run(
        agent.validate(
            artifact_id="artifact-1",
            supplemental_context="extra vector context",
            context_tokens=tokens,
        )
    )

    assert report.status == "PASS"
    assert "Runtime Context Tokens" in captured["prompt"]
    assert "tok-2" in captured["prompt"]
    assert "parameterized and validated" in captured["prompt"]
    assert "Retrieved vector context" in captured["prompt"]
    assert "Use runtime context tokens to evaluate" in captured["system_prompt"]
