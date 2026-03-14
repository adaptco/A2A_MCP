"""Tests for app.agent_shell — AGENTS.md + Skills.md parsing."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from app.agent_shell import (
    AgentShellContext,
    load_agents_manifest,
    load_skills_manifest,
    build_agent_shell,
)


@pytest.fixture()
def agents_md(tmp_path: Path) -> Path:
    content = dedent("""\
        # AGENTS.md

        ## Agent cards (roles with embedded skills)
        | Agent ID | Frontier LLM | RBAC role | Embedded skills | MCP tool pull scope |
        | --- | --- | --- | --- | --- |
        | `agent:frontier.endpoint.gpt` | `endpoint / gpt-4o-mini` | `pipeline_operator` | planning, implementation | full MCP tool scope |
        | `agent:frontier.anthropic.claude` | `anthropic / claude-3-5-sonnet-latest` | `admin` | governance, orchestration | full MCP tool scope |
    """)
    path = tmp_path / "AGENTS.md"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture()
def skills_md(tmp_path: Path) -> Path:
    content = dedent("""\
        ## Skills.md

        ### C5SymmetricChorusOrchestrator

        **Version:** 1.0

        #### Phase 1: SAMPLE - ByteSampler determinism
        #### Phase 2: COMPOSE - Constitutional enforcement
        #### Phase 3: GENERATE - Black-box delegation
        #### Phase 4: LEDGER - Receipt continuity

        ### Canonical Skill Phases with MCP

        1. **SAMPLE**: Ingest objective and initialize state.
        2. **RESOLVE**: Query MCP servers for relevant tools.
        3. **PLAN**: Construct a DAG of tool calls.
        4. **EXECUTE**: Invoke MCP tools.
        5. **VERIFY**: Validate tool outputs against the WorldModel.
    """)
    path = tmp_path / "Skills.md"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_agents_manifest(agents_md: Path) -> None:
    cards = load_agents_manifest(agents_md)
    assert len(cards) == 2
    assert cards[0].agent_id == "agent:frontier.endpoint.gpt"
    assert cards[0].rbac_role == "pipeline_operator"
    assert "planning" in cards[0].embedded_skills
    assert cards[1].agent_id == "agent:frontier.anthropic.claude"
    assert cards[1].rbac_role == "admin"


def test_load_agents_manifest_missing() -> None:
    cards = load_agents_manifest(Path("/nonexistent/AGENTS.md"))
    assert cards == []


def test_load_skills_manifest(skills_md: Path) -> None:
    phases, registrations = load_skills_manifest(skills_md)
    # Should find phases from both section patterns
    assert len(phases) >= 4  # At least the C5 phases
    phase_names = [p.phase for p in phases]
    assert "SAMPLE" in phase_names
    assert "COMPOSE" in phase_names

    # Should have registrations
    assert len(registrations) == 2
    reg_names = [r.skill_name for r in registrations]
    assert "C5SymmetricChorusOrchestrator" in reg_names
    assert "MCPEntropyTemplateRouter" in reg_names


def test_load_skills_manifest_missing() -> None:
    phases, regs = load_skills_manifest(Path("/nonexistent/Skills.md"))
    assert phases == []
    assert regs == []


def test_build_agent_shell(agents_md: Path, skills_md: Path) -> None:
    shell = build_agent_shell(agents_path=agents_md, skills_path=skills_md)
    assert isinstance(shell, AgentShellContext)
    assert len(shell.agent_cards) == 2
    assert len(shell.skill_phases) >= 4
    assert len(shell.skill_registrations) == 2

    # Test serialization
    d = shell.to_dict()
    assert "agent_cards" in d
    assert "skill_phases" in d
    assert "env_vars" in d


def test_build_agent_shell_from_repo_root() -> None:
    """Verify that build_agent_shell works with default repo-root paths."""
    shell = build_agent_shell()
    # The repo has AGENTS.md with 4 agent cards
    assert isinstance(shell, AgentShellContext)
    assert len(shell.agent_cards) >= 1
