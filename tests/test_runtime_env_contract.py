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
<<<<<<< HEAD
=======


def test_automation_env_example_contains_runtime_defaults():
    env_automation_example = REPO_ROOT / ".env.automation.example"
    assert env_automation_example.exists()
    content = _read_text(env_automation_example)
    assert "AUTOMATION_RUNTIME_API_PORT=8010" in content
    assert "AUTOMATION_FRONTEND_PORT=4173" in content
    assert "VITE_RUNTIME_API_BASE_URL=http://localhost:8010" in content


def test_automation_runtime_script_points_to_automation_stack():
    script_path = REPO_ROOT / "scripts" / "automation_runtime.ps1"
    assert script_path.exists()
    content = _read_text(script_path)
    assert "docker-compose.automation.yml" in content
    assert ".env.automation" in content
    assert "http://localhost:{0}/healthz" in content
    assert "http://localhost:{0}" in content


def test_automation_compose_wires_frontend_to_runtime_api():
    compose_automation = _read_text(REPO_ROOT / "docker-compose.automation.yml")
    assert "app.multi_client_api:app" in compose_automation
    assert "\"${AUTOMATION_RUNTIME_API_PORT:-8010}:8010\"" in compose_automation
    assert "\"${AUTOMATION_FRONTEND_PORT:-4173}:4173\"" in compose_automation
    assert "frontend/Dockerfile.automation" in compose_automation
    assert "/healthz" in compose_automation
>>>>>>> origin/main
