"""Common-thread mapping across IDE workspaces for agent/MCP repositories.

This module builds a deterministic graph of repositories and GitHub workflows,
then derives a working-model bundle with normalized vector scoring.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping, Sequence

import yaml

try:
    from core_orchestrator.world_model import normalize_vector, normalized_dot_product
except Exception:  # pragma: no cover - fallback for limited runtimes
    import math

    def normalize_vector(vector: Sequence[float]) -> tuple[float, ...]:
        if not vector:
            raise ValueError("vector must not be empty")
        norm = math.sqrt(sum(float(value) * float(value) for value in vector))
        if norm <= 0.0:
            raise ValueError("vector norm must be positive")
        return tuple(float(value) / norm for value in vector)

    def normalized_dot_product(lhs: Sequence[float], rhs: Sequence[float]) -> float:
        if len(lhs) != len(rhs):
            raise ValueError("vectors must have equal dimensions")
        left = normalize_vector(lhs)
        right = normalize_vector(rhs)
        return sum(a * b for a, b in zip(left, right))


DEFAULT_IDE_ROOTS = [
    r"C:\Users\eqhsp\.antigravity",
    r"C:\Users\eqhsp\.claude",
    r"C:\Users\eqhsp\.codex",
    r"C:\Users\eqhsp\.docker",
    r"C:\Users\eqhsp\.kimi",
    r"C:\Users\eqhsp\.vscode",
]

DEFAULT_TEMPLATE_DIR = Path(r"C:\Users\eqhsp\.gemini\A2A_MCP\templates")
DEFAULT_OUTPUT_DIR = Path("build/common_thread")

EXCLUDED_DIR_NAMES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".sandbox",
    ".venv",
    "__pycache__",
    "backups",
    "build",
    "coverage",
    "dist",
    "extensions",
    "history",
    "log",
    "logs",
    "node_modules",
    "sessions",
    "sqlite",
    "telemetry",
    "tmp",
    "vendor_imports",
    "worktrees",
}

SCOPE_KEYWORDS = {
    "a2a",
    "agent",
    "governance",
    "github",
    "mcp",
    "orchestrator",
    "qube",
    "rbac",
    "ssot",
    "world",
    "workflow",
}

WORKFLOW_KEYWORDS = (
    "a2a",
    "agent",
    "gemini",
    "github",
    "handshake",
    "mcp",
    "oauth",
    "orchestrator",
    "rbac",
    "wasm",
    "world_model",
    "world-model",
)

SECRET_REF_RE = re.compile(r"\${{\s*secrets\.([A-Za-z0-9_]+)\s*}}", re.IGNORECASE)
TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


@dataclass(frozen=True)
class RepoCandidate:
    """One discovered git repository path before deduplication."""

    path: str
    root: str
    origin: str
    branch: str
    commit_ts: int
    activity_ts: int


@dataclass(frozen=True)
class WorkflowJob:
    """Normalized workflow job node."""

    job_id: str
    workflow_id: str
    display_name: str
    needs: tuple[str, ...]
    steps: tuple[str, ...]
    mcp_a2a_steps: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowSummary:
    """Normalized workflow node."""

    workflow_id: str
    repo_id: str
    file_path: str
    name: str
    triggers: tuple[str, ...]
    secrets: tuple[str, ...]
    tags: tuple[str, ...]
    jobs: tuple[WorkflowJob, ...]


def _iso_from_epoch(epoch_seconds: int) -> str:
    if epoch_seconds <= 0:
        return datetime.fromtimestamp(0, tz=timezone.utc).isoformat()
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def _canonical_json(value: Mapping[str, Any] | Sequence[Any] | str | int | float | bool | None) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _git(repo_path: str, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", repo_path, *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except Exception:
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _tokenize(value: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(value)]


def _deterministic_vector(tokens: Iterable[str], *, dimensions: int = 16) -> tuple[float, ...]:
    raw = [0.0] * dimensions
    normalized_tokens = sorted(set(token.strip().lower() for token in tokens if token.strip()))
    if not normalized_tokens:
        normalized_tokens = ["empty"]

    for token in normalized_tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = -1.0 if digest[4] % 2 else 1.0
        magnitude = 1.0 + (digest[5] / 255.0)
        raw[index] += sign * magnitude

    return normalize_vector(raw)


def _should_include_repo(path: str, origin: str, scope: str) -> bool:
    if scope == "all":
        return True
    corpus = f"{path} {origin}".lower()
    if any(keyword in corpus for keyword in SCOPE_KEYWORDS):
        return True

    repo_path = Path(path)
    marker_files = {
        "agents.md",
        "mcp_config.json",
        "mcp_server.py",
        "runtime_mcp_server.py",
    }
    marker_dirs = {
        ".github",
        "agent",
        "agents",
        "governance",
        "mcp",
        "mcp_servers",
    }
    try:
        entries = {entry.name.lower() for entry in repo_path.iterdir()}
    except OSError:
        entries = set()
    if marker_files.intersection(entries):
        return True
    if marker_dirs.intersection(entries):
        return True
    if any(any(keyword in entry for keyword in SCOPE_KEYWORDS) for entry in entries):
        return True

    workflows_dir = repo_path / ".github" / "workflows"
    if workflows_dir.exists() and any(workflows_dir.glob("*.y*ml")):
        return True
    return False


def _walk_repo_paths(root: str, max_depth: int = 6) -> list[str]:
    repo_paths: list[str] = []
    abs_root = os.path.abspath(root)
    if not os.path.isdir(abs_root):
        return repo_paths

    for current, dirs, _files in os.walk(abs_root):
        has_git_dir = ".git" in dirs
        rel = os.path.relpath(current, abs_root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if has_git_dir:
            repo_paths.append(current)
            dirs[:] = [entry for entry in dirs if entry != ".git"]
            # Continue under root-level repos to discover nested project repos.
            if depth > 0:
                dirs[:] = []
                continue
        dirs[:] = [
            entry
            for entry in dirs
            if entry not in EXCLUDED_DIR_NAMES and not entry.endswith(".worktrees")
        ]
        if depth > max_depth:
            dirs[:] = []
            continue
    return sorted(set(repo_paths))


def discover_repo_candidates(roots: Sequence[str], scope: str = "agent-mcp") -> list[RepoCandidate]:
    """Discover repositories and capture metadata for dedupe."""

    discovered: list[RepoCandidate] = []
    for root in roots:
        for repo_path in _walk_repo_paths(root):
            origin = _git(repo_path, "remote", "get-url", "origin")
            if not _should_include_repo(repo_path, origin, scope):
                continue
            branch = _git(repo_path, "rev-parse", "--abbrev-ref", "HEAD") or "(unknown)"
            commit_ts_raw = _git(repo_path, "log", "-1", "--format=%ct")
            commit_ts = int(commit_ts_raw) if commit_ts_raw.isdigit() else 0
            activity_ts = int(Path(repo_path).stat().st_mtime)
            discovered.append(
                RepoCandidate(
                    path=os.path.abspath(repo_path),
                    root=os.path.abspath(root),
                    origin=origin,
                    branch=branch,
                    commit_ts=commit_ts,
                    activity_ts=activity_ts,
                )
            )
    return sorted(discovered, key=lambda item: (item.origin, item.path))


def _repo_key(candidate: RepoCandidate) -> str:
    if candidate.origin:
        return f"origin::{candidate.origin.lower()}"
    return f"path::{candidate.path.lower()}"


def _repo_slug(origin: str, path: str) -> str:
    value = origin or Path(path).name
    value = value.rstrip("/").split("/")[-1]
    value = value.removesuffix(".git")
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value or "repo"


def _build_logical_repositories(candidates: Sequence[RepoCandidate]) -> list[dict[str, Any]]:
    grouped: dict[str, list[RepoCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(_repo_key(candidate), []).append(candidate)

    logical_repos: list[dict[str, Any]] = []
    for key, group in sorted(grouped.items(), key=lambda entry: entry[0]):
        ranked = sorted(
            group,
            key=lambda item: (item.commit_ts, item.activity_ts, item.path),
            reverse=True,
        )
        primary = ranked[0]
        slug = _repo_slug(primary.origin, primary.path)
        repo_hash = _sha256_text(f"{key}|{primary.path}")[:8]
        repo_id = f"repo-{slug}-{repo_hash}"
        mirrors = sorted({entry.path for entry in group})
        roots = sorted({entry.root for entry in group})
        logical_repos.append(
            {
                "id": repo_id,
                "slug": slug,
                "origin": primary.origin,
                "branch": primary.branch,
                "primary_path": primary.path,
                "mirror_paths": mirrors,
                "roots": roots,
                "latest_commit_ts": max(entry.commit_ts for entry in group),
                "latest_activity_ts": max(entry.activity_ts for entry in group),
            }
        )
    return logical_repos


def _normalize_trigger_names(on_value: Any) -> tuple[str, ...]:
    if on_value is None:
        return tuple()
    if isinstance(on_value, str):
        return (on_value,)
    if isinstance(on_value, list):
        return tuple(sorted(str(item) for item in on_value))
    if isinstance(on_value, dict):
        return tuple(sorted(str(item) for item in on_value.keys()))
    return (str(on_value),)


def _extract_workflow_jobs(workflow_id: str, jobs_payload: Any) -> tuple[WorkflowJob, ...]:
    if not isinstance(jobs_payload, dict):
        return tuple()
    normalized: list[WorkflowJob] = []
    for job_id, job_cfg in sorted(jobs_payload.items(), key=lambda item: item[0]):
        job_name = job_id
        needs_raw: list[str] = []
        step_names: list[str] = []
        relevant_steps: list[str] = []
        if isinstance(job_cfg, dict):
            if isinstance(job_cfg.get("name"), str) and job_cfg.get("name", "").strip():
                job_name = str(job_cfg["name"]).strip()
            needs = job_cfg.get("needs")
            if isinstance(needs, str):
                needs_raw = [needs]
            elif isinstance(needs, list):
                needs_raw = [str(value) for value in needs]
            steps = job_cfg.get("steps")
            if isinstance(steps, list):
                for entry in steps:
                    if not isinstance(entry, dict):
                        continue
                    label = str(entry.get("name") or entry.get("uses") or entry.get("run") or "").strip()
                    if not label:
                        continue
                    step_names.append(label)
                    text = label.lower()
                    if any(keyword in text for keyword in WORKFLOW_KEYWORDS):
                        relevant_steps.append(label)
        normalized.append(
            WorkflowJob(
                job_id=str(job_id),
                workflow_id=workflow_id,
                display_name=job_name,
                needs=tuple(sorted({item for item in needs_raw if item})),
                steps=tuple(step_names),
                mcp_a2a_steps=tuple(sorted(set(relevant_steps))),
            )
        )
    return tuple(normalized)


def extract_workflows(logical_repositories: Sequence[Mapping[str, Any]]) -> list[WorkflowSummary]:
    """Parse and normalize GitHub workflows for each logical repository."""

    results: list[WorkflowSummary] = []
    for repo in logical_repositories:
        repo_id = str(repo["id"])
        primary_path = Path(str(repo["primary_path"]))
        workflows_dir = primary_path / ".github" / "workflows"
        if not workflows_dir.exists():
            continue
        for workflow_file in sorted(workflows_dir.glob("*.y*ml")):
            try:
                raw_text = workflow_file.read_text(encoding="utf-8")
            except OSError:
                continue
            try:
                parsed = yaml.safe_load(raw_text) or {}
            except yaml.YAMLError:
                parsed = {}
            if not isinstance(parsed, dict):
                parsed = {}
            workflow_name = str(parsed.get("name") or workflow_file.stem)
            workflow_hash = _sha256_text(f"{repo_id}|{workflow_file.as_posix()}")[:8]
            workflow_id = f"workflow-{workflow_hash}"
            # PyYAML may parse key "on" as boolean True in YAML 1.1 mode.
            on_value = parsed["on"] if "on" in parsed else parsed.get(True)
            triggers = _normalize_trigger_names(on_value)
            secrets = tuple(sorted(set(SECRET_REF_RE.findall(raw_text))))
            tags = tuple(sorted({kw for kw in WORKFLOW_KEYWORDS if kw in raw_text.lower()}))
            jobs = _extract_workflow_jobs(workflow_id, parsed.get("jobs"))
            results.append(
                WorkflowSummary(
                    workflow_id=workflow_id,
                    repo_id=repo_id,
                    file_path=str(workflow_file.resolve()),
                    name=workflow_name,
                    triggers=triggers,
                    secrets=secrets,
                    tags=tags,
                    jobs=jobs,
                )
            )
    return sorted(results, key=lambda item: (item.repo_id, item.file_path))


def build_projects_graph(roots: Sequence[str], *, scope: str = "agent-mcp") -> dict[str, Any]:
    """Build normalized graph from workspace roots."""

    candidates = discover_repo_candidates(roots, scope=scope)
    repos = _build_logical_repositories(candidates)
    workflows = extract_workflows(repos)

    workflow_nodes = []
    job_nodes = []
    edges = []

    for workflow in workflows:
        workflow_mcp_steps = sorted({step for job in workflow.jobs for step in job.mcp_a2a_steps})
        workflow_nodes.append(
            {
                "id": workflow.workflow_id,
                "repo_id": workflow.repo_id,
                "name": workflow.name,
                "file_path": workflow.file_path,
                "triggers": list(workflow.triggers),
                "required_secrets": list(workflow.secrets),
                "tags": list(workflow.tags),
                "mcp_a2a_steps": workflow_mcp_steps,
            }
        )
        edges.append(
            {
                "type": "repo_has_workflow",
                "from": workflow.repo_id,
                "to": workflow.workflow_id,
            }
        )
        for job in workflow.jobs:
            job_node_id = f"{workflow.workflow_id}::job::{job.job_id}"
            job_nodes.append(
                {
                    "id": job_node_id,
                    "workflow_id": workflow.workflow_id,
                    "job_id": job.job_id,
                    "name": job.display_name,
                    "steps": list(job.steps),
                    "mcp_a2a_steps": list(job.mcp_a2a_steps),
                }
            )
            edges.append(
                {
                    "type": "workflow_has_job",
                    "from": workflow.workflow_id,
                    "to": job_node_id,
                }
            )
            for dependency in job.needs:
                dep_node_id = f"{workflow.workflow_id}::job::{dependency}"
                edges.append(
                    {
                        "type": "job_needs_job",
                        "from": dep_node_id,
                        "to": job_node_id,
                    }
                )

    latest_timestamp = max(
        [int(repo.get("latest_commit_ts", 0)) for repo in repos]
        + [int(repo.get("latest_activity_ts", 0)) for repo in repos]
        + [0]
    )

    graph = {
        "schema_version": "common-thread.projects-graph.v1",
        "generated_at": _iso_from_epoch(latest_timestamp),
        "scope": scope,
        "roots": [os.path.abspath(root) for root in roots],
        "logical_repositories": repos,
        "workflows": workflow_nodes,
        "jobs": sorted(job_nodes, key=lambda item: item["id"]),
        "edges": sorted(edges, key=lambda item: (item["type"], item["from"], item["to"])),
    }
    graph["graph_hash"] = _sha256_text(_canonical_json(graph))
    return graph


def _workflow_tokens(workflow: Mapping[str, Any], jobs: Sequence[Mapping[str, Any]]) -> list[str]:
    token_sources: list[str] = []
    token_sources.append(str(workflow.get("name", "")))
    token_sources.append(str(workflow.get("file_path", "")))
    token_sources.extend(str(item) for item in workflow.get("triggers", []))
    token_sources.extend(str(item) for item in workflow.get("required_secrets", []))
    token_sources.extend(str(item) for item in workflow.get("tags", []))
    token_sources.extend(str(item) for item in workflow.get("mcp_a2a_steps", []))
    token_sources.extend(str(job.get("job_id", "")) for job in jobs)
    token_sources.extend(str(item) for job in jobs for item in job.get("mcp_a2a_steps", []))
    merged = " ".join(token_sources)
    return _tokenize(merged)


def build_working_model_bundle(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Derive working-model routing bundle from graph metadata."""

    workflows = list(graph.get("workflows", []))
    jobs = list(graph.get("jobs", []))
    jobs_by_workflow: dict[str, list[dict[str, Any]]] = {}
    for job in jobs:
        jobs_by_workflow.setdefault(str(job.get("workflow_id", "")), []).append(dict(job))

    capability_tokens = [
        "a2a",
        "agent",
        "github",
        "handshake",
        "mcp",
        "oauth",
        "rbac",
        "wasm",
        "world_model",
    ]
    capability_vector = _deterministic_vector(capability_tokens, dimensions=16)

    workflow_vectors: list[dict[str, Any]] = []
    routing_scores: list[dict[str, Any]] = []
    for workflow in sorted(workflows, key=lambda item: str(item.get("id", ""))):
        wf_id = str(workflow["id"])
        wf_tokens = _workflow_tokens(workflow, jobs_by_workflow.get(wf_id, []))
        wf_vector = _deterministic_vector(wf_tokens, dimensions=16)
        score = normalized_dot_product(capability_vector, wf_vector)
        workflow_vectors.append(
            {
                "workflow_id": wf_id,
                "tokens": sorted(set(wf_tokens)),
                "vector": [round(value, 8) for value in wf_vector],
            }
        )
        routing_scores.append(
            {
                "workflow_id": wf_id,
                "score": round(score, 8),
            }
        )

    routing_scores.sort(key=lambda item: (-item["score"], item["workflow_id"]))
    bundle = {
        "schema_version": "common-thread.working-model.v1",
        "generated_at": str(graph.get("generated_at", _iso_from_epoch(0))),
        "graph_hash": str(graph.get("graph_hash", "")),
        "world_model": {
            "embedding_dim": 16,
            "normalization": "l2",
            "scoring": "normalized_dot_product",
            "capability_tokens": capability_tokens,
            "capability_vector": [round(value, 8) for value in capability_vector],
        },
        "workflow_vectors": workflow_vectors,
        "routing_scores": routing_scores,
        "wasm_template": {
            "template_id": "a2a-common-thread-wasm.v1",
            "entrypoint": "wasm://a2a/common-thread",
            "storage": "template-directory",
        },
    }
    bundle["world_model_hash"] = _sha256_text(_canonical_json(bundle))
    return bundle


def render_workflow_map_mermaid(graph: Mapping[str, Any]) -> str:
    """Render graph subset as Mermaid flowchart."""

    lines = ["flowchart LR"]
    node_aliases: dict[str, str] = {}

    for repo in graph.get("logical_repositories", []):
        repo_id = str(repo["id"])
        alias = f"R{len(node_aliases) + 1}"
        node_aliases[repo_id] = alias
        label = f"{repo.get('slug', repo_id)}\\n{repo.get('branch', '')}"
        lines.append(f'  {alias}["{label}"]')

    for workflow in graph.get("workflows", []):
        workflow_id = str(workflow["id"])
        alias = f"W{len(node_aliases) + 1}"
        node_aliases[workflow_id] = alias
        label = str(workflow.get("name", workflow_id)).replace('"', "'")
        lines.append(f'  {alias}["{label}"]')

    for edge in graph.get("edges", []):
        if edge.get("type") != "repo_has_workflow":
            continue
        source = node_aliases.get(str(edge.get("from", "")))
        target = node_aliases.get(str(edge.get("to", "")))
        if source and target:
            lines.append(f"  {source} --> {target}")

    return "\n".join(lines) + "\n"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_common_thread_artifacts(
    *,
    roots: Sequence[str],
    scope: str = "agent-mcp",
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    template_dir: Path = DEFAULT_TEMPLATE_DIR,
) -> dict[str, str]:
    """Build and persist graph, Mermaid map, and working-model bundle."""

    graph = build_projects_graph(roots, scope=scope)
    mermaid = render_workflow_map_mermaid(graph)
    working_model = build_working_model_bundle(graph)

    output_dir = output_dir.resolve()
    projects_graph_path = output_dir / "projects_graph.json"
    workflow_map_path = output_dir / "workflow_map.mmd"
    working_model_path = output_dir / "working_model_bundle.json"

    _write_json(projects_graph_path, graph)
    _write_text(workflow_map_path, mermaid)
    _write_json(working_model_path, working_model)

    template_dir = template_dir.resolve()
    _write_json(template_dir / "projects_graph.json", graph)
    _write_text(template_dir / "workflow_map.mmd", mermaid)
    _write_json(template_dir / "working_model_bundle.json", working_model)

    return {
        "projects_graph": str(projects_graph_path),
        "workflow_map": str(workflow_map_path),
        "working_model_bundle": str(working_model_path),
        "template_dir": str(template_dir),
    }
