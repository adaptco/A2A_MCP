"""
Gloh — RAG Retrieval Agent (agents/Gloh/retrieval.py)

Queries the Gloh MCP vector store to inject codebase context
into implementation plans before code generation.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runner import call_llm  # noqa: E402

import httpx  # noqa: E402

SYSTEM_PROMPT = """You are Gloh, the RAG Retrieval Agent in the Sovereign Orchestrator.

Your role:
- Query vector stores for relevant codebase context
- Enrich implementation plans with discovered references
- Provide code snippets, documentation, and patterns that inform code generation
- Output enriched plans in the same A2A format with injected context
"""


def query_rag(query: str, top_k: int = 5) -> list[dict]:
    """Query the Gloh MCP vector store (or simulate for local dev)."""
    gloh_url = os.environ.get("GLOH_MCP_URL", "")
    gloh_token = os.environ.get("GLOH_MCP_TOKEN", "")

    if gloh_url and gloh_token:
        resp = httpx.post(
            f"{gloh_url}/query",
            headers={"Authorization": f"Bearer {gloh_token}"},
            json={"query": query, "top_k": top_k},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    # Fallback: use LLM to generate synthetic context
    context = call_llm(
        SYSTEM_PROMPT,
        f"Generate relevant code context for this query: {query}",
    )
    return [{"content": context, "score": 1.0, "source": "llm-generated"}]


def enrich_plan(plan_text: str, task_id: str = "T-003") -> str:
    """Enrich an implementation plan with RAG context."""
    print("[Gloh] Querying vector store for context...")
    context_results = query_rag(plan_text)

    context_block = "\n\n".join(
        f"[Context {i+1}]: {r.get('content', '')[:500]}"
        for i, r in enumerate(context_results)
    )

    enriched = call_llm(
        SYSTEM_PROMPT,
        f"Enrich this plan with the retrieved context:\n\n"
        f"PLAN:\n{plan_text}\n\nCONTEXT:\n{context_block}",
    )

    output_dir = Path("artifacts") / task_id
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "output.txt").write_text(enriched, encoding="utf-8")

    print(f"[Gloh] ✅ Enriched plan saved to artifacts/{task_id}/")
    return enriched


if __name__ == "__main__":
    plan = os.environ.get("USER_PROMPT", "")
    if not plan and len(sys.argv) > 1:
        plan = " ".join(sys.argv[1:])
    tid = os.environ.get("TASK_ID", "T-003")
    enrich_plan(plan, tid)
