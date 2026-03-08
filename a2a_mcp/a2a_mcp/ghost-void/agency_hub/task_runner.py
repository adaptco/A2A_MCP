"""
Task Runner - Drives the Agency Docking Shell through a task graph.

Usage:
    python -m agency_hub.task_runner              # heuristic mode
    python -m agency_hub.task_runner --llm        # Gemini LLM mode
"""
import argparse
import numpy as np
import sys
import os

# Ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agency_hub import DockingShell
from agency_hub.docking_shell import (
    TaskHeuristicSynthesizer,
    LLMSynthesizer,
)
from agency_hub.spokes import TaskSpoke


# ── Knowledge Priming ──────────────────────────────────────────────

def generate_strategy_knowledge(dim: int = 64) -> list:
    """
    Generate knowledge vectors representing task-solving strategies.

    Each vector is a normalized embedding seeded deterministically so
    the RAG unification step can match states to strategy concepts.
    """
    np.random.seed(42)
    strategies = [
        "sequential_execution",      # do tasks in dep-order
        "parallelise_independent",    # start all reachable tasks
        "depth_first_completion",     # finish one before moving on
        "effort_minimisation",        # pick lowest-effort first
        "critical_path",             # prioritise longest chain
    ]
    vectors = []
    for i, name in enumerate(strategies):
        vec = np.random.randn(dim)
        vec = vec / np.linalg.norm(vec)
        vectors.append(vec)
        print(f"  [KNOWLEDGE] Strategy {i}: {name}")
    return vectors


# ── Main ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Task Navigation Agent Runner")
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use Gemini LLM for token synthesis (requires google-genai)",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.0-flash",
        help="Gemini model name (default: gemini-2.0-flash)",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=30,
        help="Maximum cycles before giving up (default: 30)",
    )
    parser.add_argument(
        "--dim",
        type=int,
        default=64,
        help="Embedding dimension (default: 64)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("TASK NAVIGATION AGENT")
    print("=" * 60)

    # 1. Choose synthesizer
    if args.llm:
        synthesizer = LLMSynthesizer(model=args.model)
        print(f"\n[CONFIG] Synthesizer: LLMSynthesizer ({args.model})")
    else:
        synthesizer = TaskHeuristicSynthesizer()
        print("\n[CONFIG] Synthesizer: TaskHeuristicSynthesizer")

    # 2. Create hub
    print(f"[CONFIG] Embedding dim: {args.dim}")
    print(f"[CONFIG] Max cycles: {args.max_cycles}")
    hub = DockingShell(embedding_dim=args.dim, synthesizer=synthesizer)

    # 3. Create and dock the TaskSpoke
    spoke = TaskSpoke()
    hub.dock(spoke)

    # 4. Inject strategy knowledge
    print("\n[INIT] Loading strategy knowledge...")
    knowledge = generate_strategy_knowledge(dim=args.dim)
    hub.inject_knowledge(knowledge)

    # 5. Run the navigation loop
    print("\n" + "-" * 60)
    print("[RUNNING] Agent navigating task graph...")
    print("-" * 60)

    results = []
    for i in range(args.max_cycles):
        print(f"\n{'─' * 40} Cycle {i + 1} {'─' * 40}")

        result = hub.cycle()
        results.append(result)

        # Check completion
        raw = result["raw_state"]
        pct = raw.get("completion_pct", 0)
        print(f"  [PROGRESS] {pct:.0f}% complete")

        if spoke.is_all_done():
            print(f"\n{'=' * 60}")
            print(f"[DONE] All tasks completed in {i + 1} cycles!")
            print(f"{'=' * 60}")
            break
    else:
        print(f"\n[TIMEOUT] Reached max cycles ({args.max_cycles})")

    # 6. Summary
    print("\n" + "=" * 60)
    print("SESSION SUMMARY")
    print("=" * 60)
    stats = hub.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # Decision log
    print(f"\n[DECISION LOG] ({len(spoke.decision_log)} actions)")
    for entry in spoke.decision_log:
        action = entry["action"]
        params = entry.get("params", {})
        param_str = ", ".join(f"{k}={v}" for k, v in params.items()) if params else ""
        print(f"  Cycle {entry['cycle']:>2}: {action}({param_str})")

    # Eigenstate stabilisation
    eigenstates = [r["eigenstate"] for r in results]
    variances = [np.var(e) for e in eigenstates]
    print(f"\n[EIGENSTATE] Variance trend:")
    for i, var in enumerate(variances):
        bar = "█" * int(var * 200)
        print(f"  Cycle {i + 1:>2}: {var:.6f}  {bar}")

    if len(variances) > 1 and variances[0] > 0:
        reduction = (variances[0] - variances[-1]) / variances[0] * 100
        print(f"\n[STABILISATION] Variance change: {reduction:+.1f}%")

    # Final task status
    print(f"\n[FINAL STATE]")
    for name, status in spoke.status.items():
        icon = {"completed": "✅", "skipped": "⏭️", "in_progress": "🔄", "pending": "⬜"}.get(status, "❓")
        print(f"  {icon} {name}: {status}")

    return 0 if spoke.is_all_done() else 1


if __name__ == "__main__":
    sys.exit(main())
