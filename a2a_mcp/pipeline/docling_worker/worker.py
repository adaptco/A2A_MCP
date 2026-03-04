"""
Docling Worker
Parses documents using IBM Docling and normalizes text.
"""

import ast
import json
import redis
import time
from pathlib import Path
from typing import List, Dict, Any
import sys

# Add parent directory to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.canonical import hash_canonical_without_integrity
from lib.normalize import normalize_text

# Import Docling
try:
    from docling.document_converter import DocumentConverter
except ImportError:
    print("Warning: Docling not installed. Install with: pip install docling")
    DocumentConverter = None

# Redis connection
redis_client = redis.Redis(
    host='redis',
    port=6379,
    db=0,
    decode_responses=True
)

PARSE_QUEUE = "parse_queue"
EMBED_QUEUE = "embed_queue"
BATCH_SIZE = 32  # Chunks per batch for embedding
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".cc",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".kts",
    ".scala",
    ".sh",
}
DOCUMENT_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".adoc",
    ".pdf",
    ".docx",
    ".html",
}


def _normalized_route_value(value: Any, default: str = "") -> str:
    return str(value or default).strip()


def _derive_repo_context(task_payload: dict[str, Any], file_path: Path) -> dict[str, str]:
    metadata = task_payload.get("metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}

    repo_key = _normalized_route_value(metadata.get("repo_key"), "local/unknown")
    repo_kind = _normalized_route_value(metadata.get("repo_kind"), "workspace")
    repo_url = _normalized_route_value(metadata.get("repo_url"))
    repo_root = _normalized_route_value(metadata.get("repo_root"), "/workspaces/A2A_MCP")

    relative_path = _normalized_route_value(metadata.get("relative_path"))
    if not relative_path:
        filename = _normalized_route_value(task_payload.get("filename")) or file_path.name
        relative_path = filename

    commit_sha = _normalized_route_value(metadata.get("commit_sha"))
    branch = _normalized_route_value(metadata.get("branch"))
    module_name = _normalized_route_value(metadata.get("module_name"))

    return {
        "repo_key": repo_key,
        "repo_kind": repo_kind,
        "repo_url": repo_url,
        "repo_root": repo_root,
        "relative_path": relative_path,
        "commit_sha": commit_sha,
        "branch": branch,
        "module_name": module_name,
    }


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    for idx, char in enumerate(text):
        if char == "\n":
            offsets.append(idx + 1)
    return offsets


def _line_number_for_offset(offsets: list[int], offset: int) -> int:
    # Binary search over line start offsets for deterministic line mapping.
    lo, hi = 0, len(offsets)
    while lo < hi:
        mid = (lo + hi) // 2
        if offsets[mid] <= offset:
            lo = mid + 1
        else:
            hi = mid
    return max(1, lo)


def _infer_source_type(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix in CODE_EXTENSIONS:
        return "code"
    if suffix in DOCUMENT_EXTENSIONS:
        return "document"
    return "text"


def _normalize_code_text(text: str) -> str:
    # Preserve indentation for syntax-aware chunking while normalizing newlines.
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized_lines = [line.rstrip() for line in normalized.split("\n")]
    return "\n".join(normalized_lines).strip()


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Input text
        chunk_size: Maximum characters per chunk
        overlap: Overlap between chunks
    
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < text_len:
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > chunk_size // 2:
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1
        
        chunks.append(chunk.strip())
        start = end - overlap
    
    return [c for c in chunks if c]  # Filter empty chunks


def _fixed_window_chunks_with_lines(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50,
    strategy: str = "fixed_window",
) -> list[dict[str, Any]]:
    chunks = []
    offsets = _line_offsets(text)
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]

        if end < text_len:
            last_period = chunk.rfind(".")
            last_newline = chunk.rfind("\n")
            break_point = max(last_period, last_newline)
            if break_point > chunk_size // 2:
                chunk = chunk[: break_point + 1]
                end = start + break_point + 1

        cleaned = chunk.strip()
        if cleaned:
            line_start = _line_number_for_offset(offsets, start)
            line_end = _line_number_for_offset(offsets, max(start, end - 1))
            chunks.append(
                {
                    "text_content": cleaned,
                    "line_start": line_start,
                    "line_end": line_end,
                    "chunk_strategy": strategy,
                }
            )

        if end >= text_len:
            break
        start = max(end - overlap, start + 1)

    return chunks


def _chunk_python_ast(text: str, max_chars: int = 1800) -> list[dict[str, Any]]:
    lines = text.splitlines()
    if not lines:
        return []

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _fixed_window_chunks_with_lines(
            text=text,
            chunk_size=900,
            overlap=120,
            strategy="code_fallback_window",
        )

    node_spans: list[tuple[int, int, str]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            line_start = int(getattr(node, "lineno", 1))
            line_end = int(getattr(node, "end_lineno", line_start))
            node_spans.append((line_start, line_end, getattr(node, "name", "")))

    if not node_spans:
        return _fixed_window_chunks_with_lines(
            text=text,
            chunk_size=900,
            overlap=120,
            strategy="code_line_window",
        )

    chunks: list[dict[str, Any]] = []
    cursor = 1
    for line_start, line_end, symbol in node_spans:
        if cursor < line_start:
            preamble = "\n".join(lines[cursor - 1 : line_start - 1]).strip()
            if preamble:
                preamble_chunks = _fixed_window_chunks_with_lines(
                    text=preamble,
                    chunk_size=900,
                    overlap=120,
                    strategy="code_preamble_window",
                )
                for block in preamble_chunks:
                    block["line_start"] = cursor + int(block["line_start"]) - 1
                    block["line_end"] = cursor + int(block["line_end"]) - 1
                    chunks.append(block)

        node_text = "\n".join(lines[line_start - 1 : line_end]).strip()
        if not node_text:
            cursor = line_end + 1
            continue

        if len(node_text) <= max_chars:
            chunks.append(
                {
                    "text_content": node_text,
                    "line_start": line_start,
                    "line_end": line_end,
                    "chunk_strategy": "python_ast",
                    "symbol": symbol,
                }
            )
        else:
            fallback = _fixed_window_chunks_with_lines(
                text=node_text,
                chunk_size=1200,
                overlap=200,
                strategy="python_ast_split",
            )
            for block in fallback:
                # Translate chunk-local lines into file-global lines.
                block["line_start"] = line_start + int(block["line_start"]) - 1
                block["line_end"] = line_start + int(block["line_end"]) - 1
                if symbol:
                    block["symbol"] = symbol
                chunks.append(block)

        cursor = line_end + 1

    if cursor <= len(lines):
        trailer = "\n".join(lines[cursor - 1 :]).strip()
        if trailer:
            trailer_chunks = _fixed_window_chunks_with_lines(
                text=trailer,
                chunk_size=900,
                overlap=120,
                strategy="code_trailer_window",
            )
            for block in trailer_chunks:
                block["line_start"] = cursor + int(block["line_start"]) - 1
                block["line_end"] = cursor + int(block["line_end"]) - 1
                chunks.append(block)

    return chunks


def _chunk_paragraphs(text: str, max_chars: int = 1200) -> list[dict[str, Any]]:
    paragraphs: list[dict[str, Any]] = []
    offsets = _line_offsets(text)
    cursor = 0
    for paragraph in text.split("\n\n"):
        raw = paragraph.strip()
        if not raw:
            cursor += len(paragraph) + 2
            continue

        start_offset = text.find(paragraph, cursor)
        end_offset = start_offset + len(paragraph)
        cursor = end_offset + 2
        paragraphs.append(
            {
                "text": raw,
                "line_start": _line_number_for_offset(offsets, start_offset),
                "line_end": _line_number_for_offset(offsets, max(start_offset, end_offset - 1)),
            }
        )

    if not paragraphs:
        return _fixed_window_chunks_with_lines(
            text=text,
            chunk_size=900,
            overlap=100,
            strategy="doc_fallback_window",
        )

    chunks: list[dict[str, Any]] = []
    current: list[str] = []
    line_start = paragraphs[0]["line_start"]
    line_end = paragraphs[0]["line_end"]

    for para in paragraphs:
        candidate = "\n\n".join(current + [para["text"]])
        if current and len(candidate) > max_chars:
            chunks.append(
                {
                    "text_content": "\n\n".join(current),
                    "line_start": line_start,
                    "line_end": line_end,
                    "chunk_strategy": "paragraph_pack",
                }
            )
            current = [para["text"]]
            line_start = para["line_start"]
            line_end = para["line_end"]
        else:
            if not current:
                line_start = para["line_start"]
            current.append(para["text"])
            line_end = para["line_end"]

    if current:
        chunks.append(
            {
                "text_content": "\n\n".join(current),
                "line_start": line_start,
                "line_end": line_end,
                "chunk_strategy": "paragraph_pack",
            }
        )
    return chunks


def hybrid_chunk_text(text: str, source_type: str, file_path: Path) -> list[dict[str, Any]]:
    if source_type == "code":
        if file_path.suffix.lower() == ".py":
            return _chunk_python_ast(text)
        return _fixed_window_chunks_with_lines(
            text=text,
            chunk_size=900,
            overlap=120,
            strategy="code_line_window",
        )

    if source_type == "document":
        return _chunk_paragraphs(text)

    return _fixed_window_chunks_with_lines(
        text=text,
        chunk_size=700,
        overlap=90,
        strategy="text_window",
    )


def process_document(task_payload: Dict[str, Any]) -> None:
    """
    Process a document: parse with Docling, normalize, chunk, and enqueue for embedding.
    
    Args:
        task_payload: Task payload from ingest API
    """
    bundle_id = task_payload['bundle_id']
    file_path = Path(task_payload['file_path'])
    pipeline_version = task_payload['pipeline_version']
    
    print(f"Processing bundle {bundle_id}: {file_path}")
    
    try:
        source_type = _infer_source_type(file_path)
        repo_context = _derive_repo_context(task_payload, file_path)
        # Parse with Docling
        if DocumentConverter is None:
            # Fallback: read as plain text
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_text = f.read()
        else:
            converter = DocumentConverter()
            result = converter.convert(str(file_path))
            raw_text = result.document.export_to_markdown()
        
        # Normalize text
        if source_type == "code":
            normalized_text = _normalize_code_text(raw_text)
        else:
            normalized_text = normalize_text(raw_text)
        
        # Create normalized document record
        doc_record = {
            "doc_id": bundle_id,
            "pipeline_version": pipeline_version,
            "content": normalized_text,
            "metadata": task_payload.get('metadata', {}),
            "source_type": source_type,
            "repo_context": repo_context,
            "docling_version": "0.4.0",  # Should be from config
            "normalizer_version": "norm.v1"
        }
        
        # Compute integrity hash
        hash_canonical_without_integrity(doc_record)
        
        # Chunk the text with source-aware strategy for code/document retrieval quality.
        chunks = hybrid_chunk_text(
            text=normalized_text,
            source_type=source_type,
            file_path=file_path,
        )
        print(f"Created {len(chunks)} chunks for bundle {bundle_id}")
        
        # Create chunk records
        chunk_records = []
        for idx, chunk in enumerate(chunks):
            chunk_text_content = str(chunk.get("text_content", "")).strip()
            if not chunk_text_content:
                continue
            chunk_record = {
                "chunk_id": f"{bundle_id}_chunk_{idx}",
                "doc_id": bundle_id,
                "chunk_index": idx,
                "text_content": chunk_text_content,
                "source_type": source_type,
                "chunk_locator": {
                    "line_start": chunk.get("line_start"),
                    "line_end": chunk.get("line_end"),
                    "strategy": chunk.get("chunk_strategy"),
                    "symbol": chunk.get("symbol"),
                },
                "pipeline_version": pipeline_version,
                "chunker_version": "chunk.v2.hybrid",
                "repo_key": repo_context["repo_key"],
                "repo_kind": repo_context["repo_kind"],
                "repo_url": repo_context["repo_url"],
                "repo_root": repo_context["repo_root"],
                "relative_path": repo_context["relative_path"],
                "commit_sha": repo_context["commit_sha"],
                "branch": repo_context["branch"],
                "module_name": repo_context["module_name"],
            }
            hash_canonical_without_integrity(chunk_record)
            chunk_records.append(chunk_record)
        
        # Batch chunks for embedding
        batches = [
            chunk_records[i:i + BATCH_SIZE]
            for i in range(0, len(chunk_records), BATCH_SIZE)
        ]
        
        # Enqueue batches to embed_queue
        for batch_idx, batch in enumerate(batches):
            batch_payload = {
                "batch_id": f"{bundle_id}_batch_{batch_idx}",
                "doc_id": bundle_id,
                "chunks": batch,
                "pipeline_version": pipeline_version
            }
            hash_canonical_without_integrity(batch_payload)
            redis_client.rpush(EMBED_QUEUE, json.dumps(batch_payload))
        
        print(f"Enqueued {len(batches)} batches for embedding")
        
    except Exception as e:
        print(f"Error processing bundle {bundle_id}: {str(e)}")
        raise


def worker_loop():
    """Main worker loop."""
    print("Docling worker started. Waiting for tasks...")
    
    while True:
        try:
            # Blocking pop from queue (timeout 1 second)
            result = redis_client.blpop(PARSE_QUEUE, timeout=1)
            
            if result:
                _, task_json = result
                task_payload = json.loads(task_json)
                process_document(task_payload)
            
        except KeyboardInterrupt:
            print("Worker shutting down...")
            break
        except Exception as e:
            print(f"Worker error: {str(e)}")
            time.sleep(1)


if __name__ == "__main__":
    worker_loop()
