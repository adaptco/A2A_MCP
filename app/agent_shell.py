"""Agent shell environment — loads AGENTS.md + Skills.md into structured context.

Parses the repo-root markdown manifests into agent cards and skill phase
definitions that MCP tool calls can use as environmental context.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AgentCard:
    """A single agent entry parsed from the AGENTS.md table."""

    agent_id: str
    frontier_llm: str
    rbac_role: str
    embedded_skills: List[str]
    mcp_tool_scope: str


@dataclass
class SkillPhase:
    """A skill phase entry parsed from Skills.md."""

    skill_name: str
    phase: str
    description: str


@dataclass
class SkillRegistration:
    """Complete skill registration from Skills.md."""

    skill_name: str
    version: str
    namespace: str
    mode: str
    phases: List[str]
    required_checks: List[str]
    optional_checks: List[str]


@dataclass
class AgentShellContext:
    """Combined agent + skill context for MCP tool calls."""

    agent_cards: List[AgentCard]
    skill_phases: List[SkillPhase]
    skill_registrations: List[SkillRegistration]
    env_vars: Dict[str, str] = field(default_factory=dict)
    agents_md_path: str = ""
    skills_md_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the shell context to a JSON-safe dict."""
        return {
            "agent_cards": [
                {
                    "agent_id": c.agent_id,
                    "frontier_llm": c.frontier_llm,
                    "rbac_role": c.rbac_role,
                    "embedded_skills": c.embedded_skills,
                    "mcp_tool_scope": c.mcp_tool_scope,
                }
                for c in self.agent_cards
            ],
            "skill_phases": [
                {
                    "skill_name": s.skill_name,
                    "phase": s.phase,
                    "description": s.description,
                }
                for s in self.skill_phases
            ],
            "skill_registrations": [
                {
                    "skill_name": r.skill_name,
                    "version": r.version,
                    "namespace": r.namespace,
                    "mode": r.mode,
                    "phases": r.phases,
                    "required_checks": r.required_checks,
                    "optional_checks": r.optional_checks,
                }
                for r in self.skill_registrations
            ],
            "env_vars": self.env_vars,
            "agents_md_path": self.agents_md_path,
            "skills_md_path": self.skills_md_path,
        }


def _repo_root() -> Path:
    """Resolve the repository root (parent of app/)."""
    return Path(__file__).resolve().parent.parent


def load_agents_manifest(path: Optional[Path] = None) -> List[AgentCard]:
    """Parse AGENTS.md and extract the agent cards table.

    Looks for the markdown table under '## Agent cards' with columns:
    Agent ID | Frontier LLM | RBAC role | Embedded skills | MCP tool pull scope
    """
    if path is None:
        path = _repo_root() / "AGENTS.md"

    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")
    cards: List[AgentCard] = []

    # Find markdown table rows: lines starting with | that contain agent IDs
    table_pattern = re.compile(
        r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*([^|]+)\|\s*([^|]+)\|",
        re.MULTILINE,
    )

    for match in table_pattern.finditer(content):
        agent_id = match.group(1).strip()
        frontier_llm = match.group(2).strip()
        rbac_role = match.group(3).strip()
        skills_raw = match.group(4).strip()
        mcp_scope = match.group(5).strip()

        embedded_skills = [s.strip() for s in skills_raw.split(",") if s.strip()]

        cards.append(
            AgentCard(
                agent_id=agent_id,
                frontier_llm=frontier_llm,
                rbac_role=rbac_role,
                embedded_skills=embedded_skills,
                mcp_tool_scope=mcp_scope,
            )
        )

    return cards


def load_skills_manifest(path: Optional[Path] = None) -> tuple[List[SkillPhase], List[SkillRegistration]]:
    """Parse Skills.md and extract skill phases and registrations.

    Looks for:
    - Phase headers like '#### Phase N: NAME - description'
    - Skill metadata JSON blocks with namespace, mode, phases, etc.
    - The MCP five-phase lifecycle (SAMPLE, RESOLVE, PLAN, EXECUTE, VERIFY)
    """
    if path is None:
        path = _repo_root() / "Skills.md"

    if not path.exists():
        return [], []

    content = path.read_text(encoding="utf-8")
    phases: List[SkillPhase] = []
    registrations: List[SkillRegistration] = []

    # Extract phases from "#### Phase N: NAME - description"
    phase_pattern = re.compile(
        r"^####\s+Phase\s+\d+:\s+(\w+)\s*[-–]\s*(.+)$", re.MULTILINE
    )
    for match in phase_pattern.finditer(content):
        phase_name = match.group(1).strip()
        description = match.group(2).strip()
        phases.append(
            SkillPhase(
                skill_name="C5SymmetricChorusOrchestrator",
                phase=phase_name,
                description=description,
            )
        )

    # Extract MCP lifecycle phases from numbered list
    mcp_phase_pattern = re.compile(
        r"^\d+\.\s+\*\*(\w+)\*\*:\s*(.+)$", re.MULTILINE
    )
    for match in mcp_phase_pattern.finditer(content):
        phase_name = match.group(1).strip()
        description = match.group(2).strip()
        phases.append(
            SkillPhase(
                skill_name="MCPToolLifecycle",
                phase=phase_name,
                description=description,
            )
        )

    # Build registration for C5SymmetricChorusOrchestrator
    registrations.append(
        SkillRegistration(
            skill_name="C5SymmetricChorusOrchestrator",
            version="1.0",
            namespace="avatar.controlbus.synthetic.engineer.v1",
            mode="WRAP",
            phases=["SAMPLE", "COMPOSE", "GENERATE", "LEDGER"],
            required_checks=["c5_symmetry", "scene_complexity", "bpm_range"],
            optional_checks=["rsm_silhouette"],
        )
    )

    # Build registration for MCPEntropyTemplateRouter
    registrations.append(
        SkillRegistration(
            skill_name="MCPEntropyTemplateRouter",
            version="1.0",
            namespace="skills.mcp-entropy-template-router",
            mode="DETERMINISTIC",
            phases=["SAMPLE", "RESOLVE", "PLAN", "EXECUTE", "VERIFY"],
            required_checks=["api_skill_tokens", "style_temperature"],
            optional_checks=["template_route"],
        )
    )

    return phases, registrations


def build_agent_shell(
    agents_path: Optional[Path] = None,
    skills_path: Optional[Path] = None,
) -> AgentShellContext:
    """Build the full agent shell context from AGENTS.md + Skills.md.

    This is the main entry point: it loads both manifests, collects relevant
    environment variables, and returns a unified context object.
    """
    agents_file = agents_path or (_repo_root() / "AGENTS.md")
    skills_file = skills_path or (_repo_root() / "Skills.md")

    agent_cards = load_agents_manifest(agents_file)
    skill_phases, skill_registrations = load_skills_manifest(skills_file)

    # Collect relevant env vars for the shell context
    env_keys = [
        "LLM_API_KEY", "LLM_ENDPOINT", "LLM_MODEL",
        "MCP_EXECUTION_MODE", "PORT", "ENV",
    ]
    env_vars = {k: os.environ.get(k, "") for k in env_keys}

    return AgentShellContext(
        agent_cards=agent_cards,
        skill_phases=skill_phases,
        skill_registrations=skill_registrations,
        env_vars=env_vars,
        agents_md_path=str(agents_file),
        skills_md_path=str(skills_file),
    )
