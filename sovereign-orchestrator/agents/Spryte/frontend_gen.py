"""
Spryte — Frontend Generator (agents/Spryte/frontend_gen.py)

Creates HTML/JS/CSS frontend artifacts from chat-context specs.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import call_llm  # noqa: E402

SYSTEM_PROMPT = """You are Spryte, the Frontend Generation Agent in the Sovereign Orchestrator.

Your role:
- Generate complete, production-ready HTML/CSS/JS from specifications
- Create responsive, accessible, and beautiful UI components
- Output self-contained files that can be served directly or integrated into a build
- Follow modern web best practices (semantic HTML, CSS custom properties, ES modules)

When generating frontend code, output ALL files as a JSON manifest:
{
  "files": [
    {"path": "index.html", "content": "..."},
    {"path": "styles.css", "content": "..."},
    {"path": "app.js", "content": "..."}
  ]
}
"""


def generate_frontend(spec_text: str, task_id: str = "T-005") -> str:
    """Generate frontend artifacts from a specification."""
    llm_target = os.environ.get("LLM_TARGET", "gemini")
    print(f"[Spryte] Generating frontend via {llm_target}...")

    result = call_llm(SYSTEM_PROMPT, spec_text)

    output_dir = Path("artifacts") / task_id
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "output.txt").write_text(result, encoding="utf-8")

    print(f"[Spryte] ✅ Frontend artifacts written to {output_dir}")
    return result


if __name__ == "__main__":
    spec_text = os.environ.get("USER_PROMPT", "")
    if not spec_text and len(sys.argv) > 1:
        spec_text = " ".join(sys.argv[1:])
    tid = os.environ.get("TASK_ID", "T-005")
    generate_frontend(spec_text, tid)
