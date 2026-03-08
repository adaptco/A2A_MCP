from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_env_example_contains_orchestration_profile_variables():
    env_example = REPO_ROOT / ".env.example"
    assert env_example.exists()
    content = _read_text(env_example)
    assert "LLM_API_KEY=" in content
    assert "LLM_ENDPOINT=" in content
    assert "LLM_MODEL=" in content
    assert "A2A_ORCHESTRATION_MODEL=" in content
    assert "A2A_ORCHESTRATION_EMBEDDING_LANGUAGE=code" in content


def test_env_unified_example_contains_orchestration_profile_variables():
    env_unified_example = REPO_ROOT / ".env.unified.example"
    assert env_unified_example.exists()
    content = _read_text(env_unified_example)
    assert "LLM_MODEL=gpt-4o-mini" in content
    assert "A2A_ORCHESTRATION_MODEL=" in content
    assert "A2A_ORCHESTRATION_EMBEDDING_LANGUAGE=code" in content


def test_unified_runtime_default_template_contains_orchestration_profile_variables():
    script_path = REPO_ROOT / "scripts" / "unified_runtime.ps1"
    content = _read_text(script_path)
    assert "LLM_MODEL=gpt-4o-mini" in content
    assert "A2A_ORCHESTRATION_MODEL=" in content
    assert "A2A_ORCHESTRATION_EMBEDDING_LANGUAGE=code" in content


def test_compose_files_expose_orchestration_profile_variables():
    compose_unified = _read_text(REPO_ROOT / "docker-compose.unified.yml")
    assert "LLM_MODEL: ${LLM_MODEL:-gpt-4o-mini}" in compose_unified
    assert "A2A_ORCHESTRATION_MODEL: ${A2A_ORCHESTRATION_MODEL:-}" in compose_unified
    assert (
        "A2A_ORCHESTRATION_EMBEDDING_LANGUAGE: "
        "${A2A_ORCHESTRATION_EMBEDDING_LANGUAGE:-code}"
    ) in compose_unified

    compose_default = _read_text(REPO_ROOT / "docker-compose.yml")
    assert "LLM_MODEL: ${LLM_MODEL:-gpt-4o-mini}" in compose_default
    assert "A2A_ORCHESTRATION_MODEL: ${A2A_ORCHESTRATION_MODEL:-}" in compose_default
    assert (
        "A2A_ORCHESTRATION_EMBEDDING_LANGUAGE: "
        "${A2A_ORCHESTRATION_EMBEDDING_LANGUAGE:-code}"
    ) in compose_default
