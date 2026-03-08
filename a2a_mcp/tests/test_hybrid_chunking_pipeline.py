from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = ROOT / "pipeline" / "docling_worker" / "worker.py"


def _load_worker_module():
    if "redis" not in sys.modules:
        redis_stub = ModuleType("redis")
        redis_stub.Redis = lambda *args, **kwargs: SimpleNamespace()
        sys.modules["redis"] = redis_stub
    if "torch" not in sys.modules:
        torch_stub = ModuleType("torch")
        torch_stub.Tensor = object
        torch_stub.nn = SimpleNamespace(functional=SimpleNamespace(normalize=lambda tensor, p=2, dim=-1: tensor))
        sys.modules["torch"] = torch_stub

    spec = importlib.util.spec_from_file_location("docling_worker_module", WORKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_hybrid_chunking_python_uses_ast_boundaries():
    worker = _load_worker_module()
    source = (
        "import os\n\n"
        "class Greeter:\n"
        "    def hello(self) -> str:\n"
        "        return 'hi'\n\n"
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )
    chunks = worker.hybrid_chunk_text(
        text=source,
        source_type="code",
        file_path=Path("sample.py"),
    )

    assert chunks, "Expected at least one code chunk"
    strategies = {chunk.get("chunk_strategy") for chunk in chunks}
    assert "python_ast" in strategies
    symbols = {chunk.get("symbol") for chunk in chunks if chunk.get("symbol")}
    assert {"Greeter", "add"}.issubset(symbols)


def test_hybrid_chunking_document_uses_paragraph_pack():
    worker = _load_worker_module()
    paragraph = "Doc paragraph sentence. " * 50
    text = f"{paragraph}\n\n{paragraph}\n\n{paragraph}"
    chunks = worker.hybrid_chunk_text(
        text=text,
        source_type="document",
        file_path=Path("guide.md"),
    )

    assert chunks, "Expected at least one document chunk"
    assert all(chunk.get("chunk_strategy") == "paragraph_pack" for chunk in chunks)
    assert all(chunk.get("line_start", 0) >= 1 for chunk in chunks)


def test_code_normalization_preserves_indentation():
    worker = _load_worker_module()
    raw = "def f():\r\n\tif True:\r\n\t\treturn 1\r\n"
    normalized = worker._normalize_code_text(raw)
    lines = normalized.split("\n")

    assert lines[0] == "def f():"
    assert lines[1].startswith("\t")
    assert lines[2].startswith("\t\t")


def test_repo_context_derivation_respects_metadata_and_defaults():
    worker = _load_worker_module()

    full = worker._derive_repo_context(
        {
            "filename": "worker.py",
            "metadata": {
                "repo_key": "adaptco-main/A2A_MCP",
                "repo_kind": "git",
                "repo_url": "https://github.com/adaptco-main/A2A_MCP",
                "repo_root": "/workspaces/A2A_MCP",
                "relative_path": "pipeline/docling_worker/worker.py",
                "commit_sha": "abc123",
                "branch": "main",
                "module_name": "pipeline",
            },
        },
        Path("/tmp/worker.py"),
    )
    assert full["repo_key"] == "adaptco-main/A2A_MCP"
    assert full["relative_path"] == "pipeline/docling_worker/worker.py"
    assert full["commit_sha"] == "abc123"

    defaults = worker._derive_repo_context(
        {"filename": "note.txt", "metadata": {}},
        Path("/tmp/note.txt"),
    )
    assert defaults["repo_key"] == "local/unknown"
    assert defaults["repo_kind"] == "workspace"
    assert defaults["repo_root"] == "/workspaces/A2A_MCP"
    assert defaults["relative_path"] == "note.txt"
