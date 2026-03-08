import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


REDACTION_PATTERNS = {
    "email": re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}", re.IGNORECASE),
    "phone": re.compile(r"(\\+?\\d[\\d\\s().-]{7,})"),
    "ssn": re.compile(r"\\b\\d{3}-\\d{2}-\\d{4}\\b"),
    "credit_card": re.compile(r"\\b\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}\\b"),
    "gov_id": re.compile(r"\\b[A-Z]{1,2}\\d{6,}\\b"),
    "real_names": re.compile(r"(?i)\\b[A-Z][a-z]+\\s[A-Z][a-z]+\\b"),
    "address": re.compile(r"\\d+\\s+[A-Za-z0-9\\s]+(Street|St\\.|Avenue|Ave\\.|Road|Rd\\.|Boulevard|Blvd\\.)", re.IGNORECASE),
}


def _load_config(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(text: str, newline: str = "lf", trim: bool = True) -> str:
    normalized = text.replace("\\r\\n", "\\n").replace("\\r", "\\n") if newline == "lf" else text
    return normalized.strip() if trim else normalized


def _redact(text: str, rules: Iterable[str]) -> str:
    redacted = text
    for rule in rules:
        pattern = REDACTION_PATTERNS.get(rule)
        if pattern:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _chunk(text: str, max_chars: int, overlap: int) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks


def _hash_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _iter_input_files(inputs: List[str], include_globs: List[str], exclude_globs: List[str]) -> List[Path]:
    files: List[Path] = []
    for base in inputs:
        base_path = Path(base).expanduser()
        for pattern in include_globs:
            for path in base_path.rglob(pattern):
                excluded = any(path.match(ex_pat) for ex_pat in exclude_globs)
                if path.is_file() and not excluded:
                    files.append(path)
    return sorted({p.resolve() for p in files})


def _determine_type(text: str) -> str:
    lower = text.lower()
    if "schema" in lower:
        return "spec"
    if "decision" in text:
        return "decision"
    return "other"


def threadify(config_path: Path, output_path: Path) -> None:
    config = _load_config(config_path)
    include_globs = config.get("include_globs", ["**/*.md", "**/*.txt", "**/*.json"])
    exclude_globs = config.get("exclude_globs", [])
    chunk_cfg = config.get("chunking", {"max_chars": 1800, "overlap_chars": 200})
    normalization = config.get("normalization", {"newline": "lf", "trim": True})
    redaction = config.get("redaction", {"enabled": False, "rules": []})
    labels = config.get("labels", {})

    corpus_id = config.get("corpus_id", "axq:corpus:unspecified")
    project_id = labels.get("project", "unknown_project")
    vertical_id = labels.get("vertical", "unknown_vertical")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    episode_ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    episode_id = f"axq:episode:{project_id}.{episode_ts}.0001"

    files = _iter_input_files(config.get("inputs", []), include_globs, exclude_globs)

    with output_path.open("w", encoding="utf-8") as out:
        for file_path in files:
            raw_bytes = file_path.read_bytes()
            source_hash = hashlib.sha256(raw_bytes).hexdigest()
            normalized = _normalize(raw_bytes.decode("utf-8", errors="ignore"), normalization.get("newline", "lf"), normalization.get("trim", True))
            if redaction.get("enabled"):
                normalized = _redact(normalized, redaction.get("rules", []))

            chunks = _chunk(normalized, chunk_cfg.get("max_chars", 1800), chunk_cfg.get("overlap_chars", 200))
            for idx, chunk_text in enumerate(chunks):
                thread_id_material = f"{file_path.as_posix()}|{idx}|{chunk_text}"
                thread_id = f"axq:thread:{_hash_hex(thread_id_material)}"
                record = {
                    "thread_id": thread_id,
                    "corpus_id": corpus_id,
                    "project_id": project_id,
                    "vertical_id": vertical_id,
                    "episode_id": episode_id,
                    "type": _determine_type(chunk_text),
                    "text": chunk_text,
                    "title": file_path.stem,
                    "source_uri": str(file_path),
                    "source_hash": source_hash,
                    "claims": [],
                    "spec_refs": [],
                    "tags": [labels.get("source_type", "imported")],
                    "sensitivity": labels.get("governance", "internal_only"),
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "hash": _hash_hex(chunk_text),
                }
                out.write(json.dumps(record))
                out.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Threadify corpus into digital threads JSONL")
    parser.add_argument("--config", required=True, help="Path to threadify configuration JSON")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    threadify(Path(args.config), Path(args.out))


if __name__ == "__main__":
    main()
