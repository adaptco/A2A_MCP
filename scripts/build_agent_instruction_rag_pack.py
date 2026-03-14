#!/usr/bin/env python3
"""Build an AGENTS instruction XML + CSV + spreadsheet pack for coding-agent RAG."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


DEFAULT_AGENTS_PATH = Path(r"C:\Users\eqhsp\.codex\AGENTS.md")
DEFAULT_REPOS_ROOT = Path(r"C:\Users\eqhsp\Documents\GitHub")

EXCLUDED_REPOS = {
    "backups",
    "node_modules",
}

EXCLUDED_SUFFIXES = (
    ".git",
    ".worktrees",
)


@dataclass(slots=True)
class RagTaskRow:
    task_id: str
    category: str
    agent_role: str
    source_section: str
    title: str
    instruction_summary: str
    context_chunk: str
    lora_stabilizer: str
    embedding_slot: str
    repo_scope: str
    output_artifact: str
    priority: str
    token_budget: int
    winui_surface: str
    source_path: str


@dataclass(slots=True)
class RepoScopeRow:
    repo_id: str
    repo_name: str
    role: str
    mutation_policy: str
    rag_collection: str
    embedding_lane: str


@dataclass(slots=True)
class WinUIBacklogRow:
    backlog_id: str
    area: str
    title: str
    implementation_shape: str
    purpose: str
    source_reference: str
    priority: str


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _read_markdown_sections(path: Path) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = "Overview"
    sections[current] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("## "):
            current = raw_line[3:].strip()
            sections.setdefault(current, [])
            continue
        if raw_line.startswith("# "):
            current = raw_line[2:].strip()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(raw_line.rstrip())
    return sections


def _extract_commands(markdown: str) -> list[str]:
    pattern = re.compile(r"```(?:bash|powershell)?\s*(.*?)```", re.DOTALL)
    commands: list[str] = []
    for block in pattern.findall(markdown):
        for line in block.splitlines():
            stripped = line.strip()
            if stripped:
                commands.append(stripped)
    return commands


def _build_task_rows(agents_path: Path, sections: dict[str, list[str]]) -> list[RagTaskRow]:
    full_text = agents_path.read_text(encoding="utf-8")
    commands = _extract_commands(full_text)

    rows = [
        RagTaskRow(
            task_id="rag-bootstrap-repo-inventory",
            category="bootstrap",
            agent_role="Planner",
            source_section="Standard Commands",
            title="Bootstrap repository inventory",
            instruction_summary="Initialize the repository inventory before any deterministic MoA routing begins.",
            context_chunk=commands[0] if commands else "python ... bootstrap_repo_inventory.py",
            lora_stabilizer="inventory-first grounding",
            embedding_slot="vec.bootstrap.inventory",
            repo_scope="all_repositories",
            output_artifact="repo_inventory.json",
            priority="high",
            token_budget=1200,
            winui_surface="RepoInfraPage",
            source_path=str(agents_path),
        ),
        RagTaskRow(
            task_id="rag-bootstrap-subagents",
            category="bootstrap",
            agent_role="Architect",
            source_section="Standard Commands",
            title="Generate sub-agent contract",
            instruction_summary="Refresh the deterministic Planner/Architect/Coder/Tester/Reviewer contract file.",
            context_chunk=commands[1] if len(commands) > 1 else "python ... generate_subagents.py",
            lora_stabilizer="fixed-agent topology",
            embedding_slot="vec.bootstrap.subagents",
            repo_scope="all_repositories",
            output_artifact="subagents.v1.json",
            priority="high",
            token_budget=1400,
            winui_surface="TaskCatalogPage",
            source_path=str(agents_path),
        ),
        RagTaskRow(
            task_id="rag-plan-only-moa",
            category="execution",
            agent_role="Planner",
            source_section="Standard Commands",
            title="Plan-only MoA run",
            instruction_summary="Route a task in dry-run mode first to keep command execution deterministic.",
            context_chunk=commands[2] if len(commands) > 2 else "python ... run_moa_task.py --mode auto",
            lora_stabilizer="dry-run before mutation",
            embedding_slot="vec.execution.plan_only",
            repo_scope="repo_scoped",
            output_artifact="plan.json",
            priority="high",
            token_budget=2200,
            winui_surface="MainShellWindow",
            source_path=str(agents_path),
        ),
        RagTaskRow(
            task_id="rag-guarded-checks",
            category="execution",
            agent_role="Tester",
            source_section="Safety Model",
            title="Execute guarded checks",
            instruction_summary="Run repo checks only after policy evaluation and only within repo scope.",
            context_chunk=commands[3] if len(commands) > 3 else "python ... run_moa_task.py --execute",
            lora_stabilizer="policy-gated execution",
            embedding_slot="vec.execution.guarded_checks",
            repo_scope="repo_scoped",
            output_artifact="execution.json",
            priority="medium",
            token_budget=2600,
            winui_surface="TaskCatalogPage",
            source_path=str(agents_path),
        ),
        RagTaskRow(
            task_id="rag-release-confirm-risk",
            category="governance",
            agent_role="Reviewer",
            source_section="Safety Model",
            title="Require explicit release confirmation",
            instruction_summary="High-risk release operations require an explicit confirmation flag before execution.",
            context_chunk=commands[4] if len(commands) > 4 else "python ... run_moa_task.py --confirm-risk",
            lora_stabilizer="risk-confirmation latch",
            embedding_slot="vec.governance.confirm_risk",
            repo_scope="repo_scoped",
            output_artifact="execution.json",
            priority="high",
            token_budget=1800,
            winui_surface="CommandBar",
            source_path=str(agents_path),
        ),
        RagTaskRow(
            task_id="rag-auto-retrieval-fallback",
            category="retrieval",
            agent_role="Architect",
            source_section="Retrieval Mode",
            title="Fallback from pgvector to local context",
            instruction_summary="Auto retrieval chooses pgvector only when manifest and Docker health checks pass; otherwise it falls back to deterministic local context.",
            context_chunk="Auto chooses pgvector only when manifest and Docker health checks pass; otherwise local context is used.",
            lora_stabilizer="retrieval-mode stability",
            embedding_slot="vec.retrieval.auto_fallback",
            repo_scope="all_repositories",
            output_artifact="retrieval_mode=auto",
            priority="medium",
            token_budget=1600,
            winui_surface="SettingsPage",
            source_path=str(agents_path),
        ),
        RagTaskRow(
            task_id="rag-repo-scope-guard",
            category="infrastructure",
            agent_role="Coder",
            source_section="Repository Coverage",
            title="Enforce repo-scoped mutation",
            instruction_summary="Coding agents may inspect the whole GitHub workspace but must mutate only the repo selected by --repo.",
            context_chunk="Primary scope is all repositories under Documents/GitHub, but mutations remain repo-scoped by --repo.",
            lora_stabilizer="mutation-boundary discipline",
            embedding_slot="vec.infrastructure.repo_scope",
            repo_scope="all_repositories",
            output_artifact="repo_scope_guard",
            priority="high",
            token_budget=1500,
            winui_surface="RepoInfraPage",
            source_path=str(agents_path),
        ),
        RagTaskRow(
            task_id="rag-run-artifact-capture",
            category="artifacts",
            agent_role="Tester",
            source_section="Run Artifacts",
            title="Persist run artifacts for replay",
            instruction_summary="Each routed run persists plan.json and execution.json so RAG chunks can compact context without rereading raw console history.",
            context_chunk="Persist plan.json and execution.json under .codex/tmp/moa/runs/<run-id>/",
            lora_stabilizer="artifact-backed replay",
            embedding_slot="vec.artifacts.run_pack",
            repo_scope="repo_scoped",
            output_artifact="plan.json;execution.json",
            priority="high",
            token_budget=1700,
            winui_surface="ArtifactsPage",
            source_path=str(agents_path),
        ),
        RagTaskRow(
            task_id="rag-context-compaction-catalog",
            category="lora",
            agent_role="Planner",
            source_section="Codex MoA CLI Environment",
            title="Compact instruction context into chunkable tasks",
            instruction_summary="Convert top-level AGENTS instructions into stable CSV rows that carry summaries, chunk text, vector slots, and output targets for coding agents.",
            context_chunk="Summarize instructions into agent-task chunks with explicit embedding slots and token budgets.",
            lora_stabilizer="context-window compaction",
            embedding_slot="vec.lora.context_compaction",
            repo_scope="all_repositories",
            output_artifact="agent_instruction_rag_tasks.csv",
            priority="high",
            token_budget=2100,
            winui_surface="TaskCatalogPage",
            source_path=str(agents_path),
        ),
    ]
    return rows


def _build_repo_rows(repos_root: Path) -> list[RepoScopeRow]:
    rows: list[RepoScopeRow] = []
    for repo in sorted(repos_root.iterdir()):
        if not repo.is_dir():
            continue
        if repo.name in EXCLUDED_REPOS or repo.name.endswith(EXCLUDED_SUFFIXES):
            continue
        if "filterrepo" in repo.name.lower():
            continue
        role = (
            "control-plane"
            if repo.name == ".github"
            else "orchestrator"
            if repo.name == "A2A_MCP"
            else "supporting-repo"
        )
        rows.append(
            RepoScopeRow(
                repo_id=f"repo:{_slug(repo.name)}",
                repo_name=repo.name,
                role=role,
                mutation_policy="repo-scoped-only",
                rag_collection=f"rag.{_slug(repo.name)}.instructions",
                embedding_lane=f"vec.repo.{_slug(repo.name)}",
            )
        )
    return rows


def _build_winui_backlog() -> list[WinUIBacklogRow]:
    return [
        WinUIBacklogRow(
            backlog_id="winui-shell-001",
            area="shell",
            title="Create a NavigationView-based coding-agent shell",
            implementation_shape="MainWindow with NavigationView and minimal stable destinations",
            purpose="Host Instructions, Task Catalog, Repo Infrastructure, and Artifact views in a native desktop shell.",
            source_reference="shell-navigation-and-windowing.md",
            priority="high",
        ),
        WinUIBacklogRow(
            backlog_id="winui-structure-002",
            area="structure",
            title="Split Pages, Services, Styles, and ViewModels cleanly",
            implementation_shape="Pages/Controls/ViewModels/Services/Styles folder structure",
            purpose="Keep RAG task browsing and artifact inspection maintainable as the host grows.",
            source_reference="foundation-winui-app-structure.md",
            priority="high",
        ),
        WinUIBacklogRow(
            backlog_id="winui-import-003",
            area="services",
            title="Add spreadsheet and CSV import services",
            implementation_shape="Services layer for workbook, XML, and CSV ingestion",
            purpose="Load the generated instruction pack into the desktop host without custom parsing in page code.",
            source_reference="foundation-winui-app-structure.md",
            priority="medium",
        ),
        WinUIBacklogRow(
            backlog_id="winui-rag-004",
            area="pages",
            title="Expose a compact RAG task browser",
            implementation_shape="Task catalog page with filters for role, repo, priority, and embedding slot",
            purpose="Let coding agents and operators browse the compacted context-window tasks quickly.",
            source_reference="shell-navigation-and-windowing.md",
            priority="high",
        ),
    ]


def _write_csv(path: Path, rows: list[RagTaskRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _write_xml(
    path: Path,
    agents_path: Path,
    tasks: list[RagTaskRow],
    repos: list[RepoScopeRow],
    backlog: list[WinUIBacklogRow],
) -> None:
    root = ET.Element(
        "AgentInstructionPack",
        {
            "version": "1.0",
            "source": str(agents_path),
            "ragCsv": "agent_instruction_rag_tasks.csv",
            "winuiWorkbook": "agent_instruction_rag_pack.xlsx",
        },
    )
    meta = ET.SubElement(root, "Meta")
    ET.SubElement(meta, "Goal").text = (
        "Compact AGENTS instructions into stable RAG task rows, LoRA stabilizer labels, and repository-scoped coding tasks."
    )
    ET.SubElement(meta, "ContextStrategy").text = "chunked-instruction-catalog"

    tasks_node = ET.SubElement(root, "Tasks")
    for row in tasks:
        node = ET.SubElement(
            tasks_node,
            "Task",
            {
                "id": row.task_id,
                "role": row.agent_role,
                "category": row.category,
                "priority": row.priority,
                "embeddingSlot": row.embedding_slot,
            },
        )
        ET.SubElement(node, "Title").text = row.title
        ET.SubElement(node, "InstructionSummary").text = row.instruction_summary
        ET.SubElement(node, "ContextChunk").text = row.context_chunk
        ET.SubElement(node, "LoRAStabilizer").text = row.lora_stabilizer
        ET.SubElement(node, "RepoScope").text = row.repo_scope
        ET.SubElement(node, "OutputArtifact").text = row.output_artifact
        ET.SubElement(node, "WinUISurface").text = row.winui_surface

    repos_node = ET.SubElement(root, "RepositoryInfrastructure")
    for repo in repos:
        ET.SubElement(
            repos_node,
            "Repository",
            {
                "id": repo.repo_id,
                "name": repo.repo_name,
                "role": repo.role,
                "mutationPolicy": repo.mutation_policy,
                "ragCollection": repo.rag_collection,
                "embeddingLane": repo.embedding_lane,
            },
        )

    backlog_node = ET.SubElement(root, "WinUIBacklog")
    for item in backlog:
        node = ET.SubElement(
            backlog_node,
            "BacklogItem",
            {"id": item.backlog_id, "area": item.area, "priority": item.priority},
        )
        ET.SubElement(node, "Title").text = item.title
        ET.SubElement(node, "ImplementationShape").text = item.implementation_shape
        ET.SubElement(node, "Purpose").text = item.purpose
        ET.SubElement(node, "SourceReference").text = item.source_reference

    ET.indent(root)
    tree = ET.ElementTree(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _column_letter(index: int) -> str:
    if index < 1:
        raise ValueError("column index must be 1-based")
    result = ""
    current = index
    while current:
        current, remainder = divmod(current - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _string_cell(ref: str, value: str, *, style: int = 0) -> str:
    preserve = ' xml:space="preserve"' if value != value.strip() or "\n" in value or "  " in value else ""
    return (
        f'<c r="{ref}" t="inlineStr" s="{style}">'
        f"<is><t{preserve}>{escape(value)}</t></is>"
        "</c>"
    )


def _number_cell(ref: str, value: int | float, *, style: int = 0) -> str:
    return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'


def _formula_cell(ref: str, formula: str, *, cached_value: int | float | str, style: int = 0) -> str:
    return f'<c r="{ref}" s="{style}"><f>{escape(formula)}</f><v>{escape(str(cached_value))}</v></c>'


def _cell(ref: str, value: Any, *, style: int = 0, formula: str | None = None, cached_value: Any | None = None) -> str:
    if formula is not None:
        return _formula_cell(ref, formula, cached_value="" if cached_value is None else cached_value, style=style)
    if isinstance(value, bool):
        return _number_cell(ref, int(value), style=style)
    if isinstance(value, (int, float)):
        return _number_cell(ref, value, style=style)
    return _string_cell(ref, "" if value is None else str(value), style=style)


def _column_width(values: list[str], *, minimum: float = 12.0, maximum: float = 48.0) -> float:
    if not values:
        return minimum
    longest = max(len(value) for value in values)
    width = min(maximum, max(minimum, (longest * 1.1) + 2.0))
    return round(width, 1)


def _cols_xml(widths: list[float]) -> str:
    return "<cols>" + "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    ) + "</cols>"


def _worksheet_xml(
    *,
    rows_xml: list[str],
    widths: list[float],
    sheet_ref: str,
    auto_filter_ref: str | None = None,
    freeze_top_row: bool = False,
    merges: list[str] | None = None,
) -> str:
    sheet_views = (
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        "</sheetView></sheetViews>"
        if freeze_top_row
        else '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
    )
    merge_cells = ""
    if merges:
        merge_cells = (
            f'<mergeCells count="{len(merges)}">'
            + "".join(f'<mergeCell ref="{merge_ref}"/>' for merge_ref in merges)
            + "</mergeCells>"
        )
    auto_filter = f'<autoFilter ref="{auto_filter_ref}"/>' if auto_filter_ref else ""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{sheet_ref}"/>'
        f"{sheet_views}"
        f"{_cols_xml(widths)}"
        f'<sheetData>{"".join(rows_xml)}</sheetData>'
        f"{auto_filter}"
        f"{merge_cells}"
        '<pageMargins left="0.25" right="0.25" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
        "</worksheet>"
    )


def _overview_sheet_xml(agents_path: Path, summary: dict[str, Any]) -> str:
    rows = [
        f'<row r="1">{_string_cell("A1", "Agent Instruction RAG Pack", style=1)}{_string_cell("B1", "", style=1)}</row>',
        f'<row r="2">{_string_cell("A2", "Source AGENTS", style=3)}{_string_cell("B2", str(agents_path), style=2)}</row>',
        f'<row r="3">{_string_cell("A3", "Task Count", style=3)}{_number_cell("B3", summary["task_count"])}</row>',
        f'<row r="4">{_string_cell("A4", "Repo Count", style=3)}{_number_cell("B4", summary["repo_count"])}</row>',
        f'<row r="5">{_string_cell("A5", "High Priority Tasks", style=3)}{_number_cell("B5", summary["high_priority_tasks"])}</row>',
        f'<row r="6">{_string_cell("A6", "", style=0)}{_string_cell("B6", "", style=0)}</row>',
        (
            '<row r="7">'
            f'{_string_cell("A7", "Workbook purpose", style=3)}'
            f'{_string_cell("B7", "Compact AGENTS instructions into coding-agent task rows, repo lanes, and WinUI host backlog items.", style=2)}'
            "</row>"
        ),
    ]
    widths = [20.0, 96.0]
    return _worksheet_xml(rows_xml=rows, widths=widths, sheet_ref="A1:B7", merges=["A1:B1"])


def _task_sheet_xml(tasks: list[RagTaskRow]) -> str:
    headers = [
        "Task ID",
        "Category",
        "Agent Role",
        "Source Section",
        "Title",
        "Instruction Summary",
        "Context Chunk",
        "LoRA Stabilizer",
        "Embedding Slot",
        "Repo Scope",
        "Output Artifact",
        "Priority",
        "Token Budget",
        "WinUI Surface",
        "Source Path",
        "Chunk Weight",
    ]
    rows_xml = [
        "<row r=\"1\">"
        + "".join(_string_cell(f"{_column_letter(index)}1", header, style=1) for index, header in enumerate(headers, start=1))
        + "</row>"
    ]
    width_samples = [[header] for header in headers]
    wrap_columns = {4, 5, 6, 7, 8, 10, 11, 14, 15}

    for row_index, task in enumerate(tasks, start=2):
        values = [
            task.task_id,
            task.category,
            task.agent_role,
            task.source_section,
            task.title,
            task.instruction_summary,
            task.context_chunk,
            task.lora_stabilizer,
            task.embedding_slot,
            task.repo_scope,
            task.output_artifact,
            task.priority,
            task.token_budget,
            task.winui_surface,
            task.source_path,
        ]
        cells: list[str] = []
        for column_index, value in enumerate(values, start=1):
            cell_style = 2 if column_index in wrap_columns else 0
            ref = f"{_column_letter(column_index)}{row_index}"
            cells.append(_cell(ref, value, style=cell_style))
            width_samples[column_index - 1].append(str(value))
        chunk_formula = f"LEN(F{row_index})+LEN(G{row_index})"
        chunk_weight = len(task.instruction_summary) + len(task.context_chunk)
        cells.append(_formula_cell(f"P{row_index}", chunk_formula, cached_value=chunk_weight))
        width_samples[15].append(str(chunk_weight))
        rows_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    max_row = len(tasks) + 1
    widths = [_column_width(samples) for samples in width_samples]
    return _worksheet_xml(
        rows_xml=rows_xml,
        widths=widths,
        sheet_ref=f"A1:P{max_row}",
        auto_filter_ref=f"A1:P{max_row}",
        freeze_top_row=True,
    )


def _repo_sheet_xml(repos: list[RepoScopeRow]) -> str:
    headers = ["Repo ID", "Repo Name", "Role", "Mutation Policy", "RAG Collection", "Embedding Lane"]
    rows_xml = [
        "<row r=\"1\">"
        + "".join(_string_cell(f"{_column_letter(index)}1", header, style=1) for index, header in enumerate(headers, start=1))
        + "</row>"
    ]
    width_samples = [[header] for header in headers]
    for row_index, repo in enumerate(repos, start=2):
        values = [
            repo.repo_id,
            repo.repo_name,
            repo.role,
            repo.mutation_policy,
            repo.rag_collection,
            repo.embedding_lane,
        ]
        cells = []
        for column_index, value in enumerate(values, start=1):
            ref = f"{_column_letter(column_index)}{row_index}"
            cells.append(_string_cell(ref, value))
            width_samples[column_index - 1].append(value)
        rows_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    max_row = len(repos) + 1
    widths = [_column_width(samples) for samples in width_samples]
    return _worksheet_xml(
        rows_xml=rows_xml,
        widths=widths,
        sheet_ref=f"A1:F{max_row}",
        auto_filter_ref=f"A1:F{max_row}",
        freeze_top_row=True,
    )


def _winui_sheet_xml(backlog: list[WinUIBacklogRow]) -> str:
    headers = ["Backlog ID", "Area", "Title", "Implementation Shape", "Purpose", "Source Reference", "Priority"]
    rows_xml = [
        "<row r=\"1\">"
        + "".join(_string_cell(f"{_column_letter(index)}1", header, style=1) for index, header in enumerate(headers, start=1))
        + "</row>"
    ]
    width_samples = [[header] for header in headers]
    wrap_columns = {3, 4, 5}
    for row_index, item in enumerate(backlog, start=2):
        values = [
            item.backlog_id,
            item.area,
            item.title,
            item.implementation_shape,
            item.purpose,
            item.source_reference,
            item.priority,
        ]
        cells = []
        for column_index, value in enumerate(values, start=1):
            ref = f"{_column_letter(column_index)}{row_index}"
            style = 2 if column_index in wrap_columns else 0
            cells.append(_string_cell(ref, value, style=style))
            width_samples[column_index - 1].append(value)
        rows_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    max_row = len(backlog) + 1
    widths = [_column_width(samples) for samples in width_samples]
    return _worksheet_xml(
        rows_xml=rows_xml,
        widths=widths,
        sheet_ref=f"A1:G{max_row}",
        auto_filter_ref=f"A1:G{max_row}",
        freeze_top_row=True,
    )


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/worksheets/sheet4.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )


def _root_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def _app_properties_xml(sheet_names: list[str]) -> str:
    heading_pairs = escape(f"Worksheets{len(sheet_names)}")
    part_titles = "".join(f"<vt:lpstr>{escape(name)}</vt:lpstr>" for name in sheet_names)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>Codex Spreadsheet Builder</Application>"
        "<DocSecurity>0</DocSecurity>"
        "<ScaleCrop>false</ScaleCrop>"
        f"<HeadingPairs><vt:vector size=\"2\" baseType=\"variant\"><vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant><vt:variant><vt:i4>{len(sheet_names)}</vt:i4></vt:variant></vt:vector></HeadingPairs>"
        f"<TitlesOfParts><vt:vector size=\"{len(sheet_names)}\" baseType=\"lpstr\">{part_titles}</vt:vector></TitlesOfParts>"
        "<Company>OpenAI Codex</Company>"
        "<LinksUpToDate>false</LinksUpToDate>"
        "<SharedDoc>false</SharedDoc>"
        "<HyperlinksChanged>false</HyperlinksChanged>"
        "<AppVersion>1.0</AppVersion>"
        "</Properties>"
    )


def _core_properties_xml() -> str:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:title>Agent Instruction RAG Pack</dc:title>"
        "<dc:subject>Codex agent instruction compaction</dc:subject>"
        "<dc:creator>OpenAI Codex</dc:creator>"
        "<cp:lastModifiedBy>OpenAI Codex</cp:lastModifiedBy>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def _workbook_xml(sheet_names: list[str]) -> str:
    sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(sheet_names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<bookViews><workbookView xWindow="0" yWindow="0" windowWidth="24000" windowHeight="12000"/></bookViews>'
        f"<sheets>{sheets}</sheets>"
        '<calcPr calcId="191029" fullCalcOnLoad="1"/>'
        "</workbook>"
    )


def _workbook_relationships_xml(sheet_count: int) -> str:
    sheet_rels = "".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, sheet_count + 1)
    )
    style_rel_id = sheet_count + 1
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{sheet_rels}"
        f'<Relationship Id="rId{style_rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<fonts count=\"3\">"
        "<font><sz val=\"11\"/><color rgb=\"000000\"/><name val=\"Aptos\"/><family val=\"2\"/></font>"
        "<font><b/><sz val=\"11\"/><color rgb=\"FFFFFF\"/><name val=\"Aptos\"/><family val=\"2\"/></font>"
        "<font><b/><sz val=\"11\"/><color rgb=\"000000\"/><name val=\"Aptos\"/><family val=\"2\"/></font>"
        "</fonts>"
        "<fills count=\"4\">"
        "<fill><patternFill patternType=\"none\"/></fill>"
        "<fill><patternFill patternType=\"gray125\"/></fill>"
        "<fill><patternFill patternType=\"solid\"><fgColor rgb=\"7F6000\"/><bgColor indexed=\"64\"/></patternFill></fill>"
        "<fill><patternFill patternType=\"solid\"><fgColor rgb=\"EDEDED\"/><bgColor indexed=\"64\"/></patternFill></fill>"
        "</fills>"
        "<borders count=\"2\">"
        "<border><left/><right/><top/><bottom/><diagonal/></border>"
        "<border><left style=\"thin\"/><right style=\"thin\"/><top style=\"thin\"/><bottom style=\"thin\"/><diagonal/></border>"
        "</borders>"
        "<cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs>"
        "<cellXfs count=\"4\">"
        "<xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\"/>"
        "<xf numFmtId=\"0\" fontId=\"1\" fillId=\"2\" borderId=\"1\" xfId=\"0\" applyFont=\"1\" applyFill=\"1\" applyBorder=\"1\" applyAlignment=\"1\"><alignment horizontal=\"center\" vertical=\"center\"/></xf>"
        "<xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\" applyAlignment=\"1\"><alignment vertical=\"top\" wrapText=\"1\"/></xf>"
        "<xf numFmtId=\"0\" fontId=\"2\" fillId=\"3\" borderId=\"1\" xfId=\"0\" applyFont=\"1\" applyFill=\"1\" applyBorder=\"1\" applyAlignment=\"1\"><alignment vertical=\"center\"/></xf>"
        "</cellXfs>"
        "<cellStyles count=\"1\"><cellStyle name=\"Normal\" xfId=\"0\" builtinId=\"0\"/></cellStyles>"
        "</styleSheet>"
    )


def _write_xlsx(
    path: Path,
    *,
    agents_path: Path,
    tasks: list[RagTaskRow],
    repos: list[RepoScopeRow],
    backlog: list[WinUIBacklogRow],
    summary: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet_names = ["Overview", "RAGTasks", "RepoInfra", "WinUIBacklog"]
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as workbook_zip:
        workbook_zip.writestr("[Content_Types].xml", _content_types_xml())
        workbook_zip.writestr("_rels/.rels", _root_relationships_xml())
        workbook_zip.writestr("docProps/app.xml", _app_properties_xml(sheet_names))
        workbook_zip.writestr("docProps/core.xml", _core_properties_xml())
        workbook_zip.writestr("xl/workbook.xml", _workbook_xml(sheet_names))
        workbook_zip.writestr("xl/_rels/workbook.xml.rels", _workbook_relationships_xml(len(sheet_names)))
        workbook_zip.writestr("xl/styles.xml", _styles_xml())
        workbook_zip.writestr("xl/worksheets/sheet1.xml", _overview_sheet_xml(agents_path, summary))
        workbook_zip.writestr("xl/worksheets/sheet2.xml", _task_sheet_xml(tasks))
        workbook_zip.writestr("xl/worksheets/sheet3.xml", _repo_sheet_xml(repos))
        workbook_zip.writestr("xl/worksheets/sheet4.xml", _winui_sheet_xml(backlog))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents", default=str(DEFAULT_AGENTS_PATH))
    parser.add_argument("--repos-root", default=str(DEFAULT_REPOS_ROOT))
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[1] / "output" / "spreadsheet"),
    )
    parser.add_argument(
        "--tmp-dir",
        default=str(Path(__file__).resolve().parents[1] / "tmp" / "spreadsheets"),
    )
    args = parser.parse_args()

    agents_path = Path(args.agents)
    repos_root = Path(args.repos_root)
    output_dir = Path(args.output_dir)
    tmp_dir = Path(args.tmp_dir)

    sections = _read_markdown_sections(agents_path)
    tasks = _build_task_rows(agents_path, sections)
    repos = _build_repo_rows(repos_root)
    backlog = _build_winui_backlog()

    csv_path = output_dir / "agent_instruction_rag_tasks.csv"
    xml_path = output_dir / "agent_instruction_rag_pack.xml"
    workbook_path = output_dir / "agent_instruction_rag_pack.xlsx"
    json_path = tmp_dir / "agent_instruction_rag_pack.json"
    summary = {
        "task_count": len(tasks),
        "repo_count": len(repos),
        "high_priority_tasks": sum(1 for task in tasks if task.priority == "high"),
    }

    _write_csv(csv_path, tasks)
    _write_xml(xml_path, agents_path, tasks, repos, backlog)
    _write_json(
        json_path,
        {
            "agents_path": str(agents_path),
            "tasks": [asdict(task) for task in tasks],
            "repos": [asdict(repo) for repo in repos],
            "winui_backlog": [asdict(item) for item in backlog],
            "summary": summary,
        },
    )
    _write_xlsx(
        workbook_path,
        agents_path=agents_path,
        tasks=tasks,
        repos=repos,
        backlog=backlog,
        summary=summary,
    )

    print(f"wrote csv: {csv_path}")
    print(f"wrote xml: {xml_path}")
    print(f"wrote xlsx: {workbook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
