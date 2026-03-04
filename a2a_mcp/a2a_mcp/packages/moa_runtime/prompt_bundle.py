from pathlib import Path
from typing import List

from .types import ContextBundle, RunContext


def _load_preamble(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def assemble_prompt(
    ctx: RunContext,
    preamble_path: str,
    bundle: ContextBundle,
    output_contract: str,
) -> str:
    parts: List[str] = []
    parts.append(_load_preamble(preamble_path).strip())
    parts.append(f"Task: {ctx.query}")
    parts.append("Context:")
    for chunk in bundle.chunks:
        parts.append(f"- [{chunk.thread_id}]\n{chunk.content}")
    parts.append(f"Output contract: {output_contract}")
    return "\n\n".join(parts)
