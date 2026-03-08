from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

from orchestrator.common_thread import build_projects_graph, write_common_thread_artifacts


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(
        cmd,
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def _git_date(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")


def _init_repo(path: Path, *, remote: str, commit_epoch: int, workflow_text: str | None = None) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _run(["git", "init"], cwd=path)
    _run(["git", "config", "user.email", "test@example.com"], cwd=path)
    _run(["git", "config", "user.name", "Test Runner"], cwd=path)
    _run(["git", "remote", "add", "origin", remote], cwd=path)

    (path / "README.md").write_text("# test\n", encoding="utf-8")
    if workflow_text:
        workflow_file = path / ".github" / "workflows" / "ci.yml"
        workflow_file.parent.mkdir(parents=True, exist_ok=True)
        workflow_file.write_text(workflow_text, encoding="utf-8")

    _run(["git", "add", "."], cwd=path)
    env = dict(os.environ)
    date = _git_date(commit_epoch)
    env["GIT_AUTHOR_DATE"] = date
    env["GIT_COMMITTER_DATE"] = date
    _run(["git", "commit", "-m", f"seed-{commit_epoch}"], cwd=path, env=env)


def test_discovery_dedup_and_primary_mirror_selection(tmp_path: Path) -> None:
    root_a = tmp_path / "root-a"
    root_b = tmp_path / "root-b"
    repo_older = root_a / "agent-mcp-source"
    repo_newer = root_b / "agent-mcp-mirror"
    ignored_repo = root_a / "node_modules" / "noise-agent"

    _init_repo(
        repo_older,
        remote="https://github.com/example/agent-mcp.git",
        commit_epoch=1_700_000_000,
    )
    _init_repo(
        repo_newer,
        remote="https://github.com/example/agent-mcp.git",
        commit_epoch=1_700_000_900,
    )
    _init_repo(
        ignored_repo,
        remote="https://github.com/example/agent-mcp-noise.git",
        commit_epoch=1_700_001_000,
    )

    graph = build_projects_graph([str(root_a), str(root_b)], scope="agent-mcp")
    assert len(graph["logical_repositories"]) == 1

    repo = graph["logical_repositories"][0]
    assert repo["primary_path"] == str(repo_newer.resolve())
    assert sorted(repo["mirror_paths"]) == sorted([str(repo_older.resolve()), str(repo_newer.resolve())])
    assert all("node_modules" not in path for path in repo["mirror_paths"])


def test_workflow_parser_extracts_triggers_jobs_edges_and_secrets(tmp_path: Path) -> None:
    root = tmp_path / "root"
    repo = root / "agent-mcp-workflow"
    _init_repo(
        repo,
        remote="https://github.com/example/agent-mcp-workflow.git",
        commit_epoch=1_700_002_000,
        workflow_text=(
            "name: Agent Pipeline\n"
            "on:\n"
            "  push:\n"
            "  workflow_dispatch:\n"
            "jobs:\n"
            "  build:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - name: Prepare MCP context\n"
            "        run: echo ${{ secrets.OPENAI_API_KEY }}\n"
            "  deploy:\n"
            "    needs: build\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - name: A2A handshake finalize\n"
            "        run: echo done\n"
        ),
    )

    graph = build_projects_graph([str(root)], scope="agent-mcp")
    assert len(graph["workflows"]) == 1
    workflow = graph["workflows"][0]

    assert workflow["triggers"] == ["push", "workflow_dispatch"]
    assert "OPENAI_API_KEY" in workflow["required_secrets"]
    assert any("A2A handshake finalize" in step for step in workflow["mcp_a2a_steps"])

    workflow_id = workflow["id"]
    build_job = f"{workflow_id}::job::build"
    deploy_job = f"{workflow_id}::job::deploy"
    edge_tuples = {(edge["type"], edge["from"], edge["to"]) for edge in graph["edges"]}
    assert ("workflow_has_job", workflow_id, build_job) in edge_tuples
    assert ("workflow_has_job", workflow_id, deploy_job) in edge_tuples
    assert ("job_needs_job", build_job, deploy_job) in edge_tuples


def test_common_thread_artifacts_are_deterministic_and_template_exported(tmp_path: Path) -> None:
    root = tmp_path / "root"
    repo = root / "agent-mcp-repo"
    _init_repo(
        repo,
        remote="https://github.com/example/agent-mcp-det.git",
        commit_epoch=1_700_003_000,
        workflow_text=(
            "name: Deterministic Build\n"
            "on: [push]\n"
            "jobs:\n"
            "  score:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - name: World model scoring\n"
            "        run: echo score\n"
        ),
    )

    output_dir = tmp_path / "build" / "common_thread"
    template_dir = tmp_path / "templates"

    first = write_common_thread_artifacts(
        roots=[str(root)],
        scope="agent-mcp",
        output_dir=output_dir,
        template_dir=template_dir,
    )
    snapshot_one = {
        "projects_graph": Path(first["projects_graph"]).read_text(encoding="utf-8"),
        "workflow_map": Path(first["workflow_map"]).read_text(encoding="utf-8"),
        "working_model_bundle": Path(first["working_model_bundle"]).read_text(encoding="utf-8"),
    }

    second = write_common_thread_artifacts(
        roots=[str(root)],
        scope="agent-mcp",
        output_dir=output_dir,
        template_dir=template_dir,
    )
    snapshot_two = {
        "projects_graph": Path(second["projects_graph"]).read_text(encoding="utf-8"),
        "workflow_map": Path(second["workflow_map"]).read_text(encoding="utf-8"),
        "working_model_bundle": Path(second["working_model_bundle"]).read_text(encoding="utf-8"),
    }

    assert snapshot_one == snapshot_two

    graph_payload = json.loads(snapshot_one["projects_graph"])
    bundle_payload = json.loads(snapshot_one["working_model_bundle"])
    assert bundle_payload["graph_hash"] == graph_payload["graph_hash"]
    assert bundle_payload["world_model"]["scoring"] == "normalized_dot_product"

    exported_graph = (template_dir / "projects_graph.json").read_text(encoding="utf-8")
    exported_workflow = (template_dir / "workflow_map.mmd").read_text(encoding="utf-8")
    exported_bundle = (template_dir / "working_model_bundle.json").read_text(encoding="utf-8")
    assert exported_graph == snapshot_one["projects_graph"]
    assert exported_workflow == snapshot_one["workflow_map"]
    assert exported_bundle == snapshot_one["working_model_bundle"]


def test_malformed_workflow_yaml_is_ignored_without_crashing(tmp_path: Path) -> None:
    root = tmp_path / "root"
    repo = root / "agent-mcp-bad-yaml"
    _init_repo(
        repo,
        remote="https://github.com/example/agent-mcp-bad-yaml.git",
        commit_epoch=1_700_004_000,
        workflow_text=(
            "name: bad-workflow\n"
            "  on:\n"
            "    push:\n"
            "jobs:\n"
            "  build:\n"
            "    runs-on: ubuntu-latest\n"
        ),
    )

    graph = build_projects_graph([str(root)], scope="agent-mcp")
    assert len(graph["workflows"]) == 1
    assert graph["workflows"][0]["name"] == "ci"
    assert graph["workflows"][0]["triggers"] == []
