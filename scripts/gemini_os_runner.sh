#!/usr/bin/env bash
# =============================================================================
# gemini_os_runner.sh — Gemini OS Pipeline Shell Runner
# =============================================================================
# Usage:  bash scripts/gemini_os_runner.sh [phase]
# Phases: all | lint | test | embed | telemetry | drift
#
# Single entrypoint for the Gemini OS CI pipeline.
# Drives: lint → test → agent embed (vector lake) → telemetry flush → drift guard
# =============================================================================

set -euo pipefail

PHASE="${1:-all}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${REPO_ROOT}/output"
VECTOR_LAKE_DIR="${REPO_ROOT}/data/vector_lake"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

log()  { echo -e "${CYAN}[gemini-os]${RESET} $1"; }
ok()   { echo -e "${GREEN}[✓]${RESET} $1"; }
warn() { echo -e "${YELLOW}[!]${RESET} $1"; }
fail() { echo -e "${RED}[✗]${RESET} $1"; exit 1; }

log "🌌 Gemini OS Runner — phase: ${BOLD}${PHASE}${RESET}"
log "   Repo root: ${REPO_ROOT}"
mkdir -p "${OUTPUT_DIR}" "${VECTOR_LAKE_DIR}"

# =============================================================================
# PHASE: lint
# =============================================================================
run_lint() {
  log "=== Phase: Lint ==="
  if command -v ruff &>/dev/null; then
    ruff check "${REPO_ROOT}" --output-format=text --exclude worktrees || warn "Ruff found issues (non-blocking)"
  fi
  if command -v pylint &>/dev/null; then
    pylint a2a_mcp orchestrator agents schemas --fail-under=6.0 \
      2>&1 | tee "${OUTPUT_DIR}/pylint.log" || warn "Pylint issues (non-blocking)"
  fi
  ok "Lint complete"
}

# =============================================================================
# PHASE: test
# =============================================================================
run_test() {
  log "=== Phase: Test ==="
  if ! command -v pytest &>/dev/null; then
    fail "pytest not found — run: pip install -e .[dev]"
  fi
  pytest "${REPO_ROOT}/tests" \
    -v \
    --tb=short \
    --junit-xml="${OUTPUT_DIR}/test-report.xml" \
    --ignore="${REPO_ROOT}/worktrees" \
    --ignore="${REPO_ROOT}/OfficeDocker" \
    2>&1 | tee "${OUTPUT_DIR}/pytest.log" || warn "Some tests failed — check ${OUTPUT_DIR}/pytest.log"
  ok "Test phase complete"
}

# =============================================================================
# PHASE: embed — Agent pipeline → Vector Data Lake
# Maps the agent pipeline as the data embedding layer for the vector space.
# Agents are Avatars in 4D space; their prompt tokens are encoded as embedding
# vectors and stored in data/vector_lake/ as the stateful data lake.
# =============================================================================
run_embed() {
  log "=== Phase: Agent Embed (Vector Lake) ==="

  python - <<'PYEOF'
import sys, json, pathlib, hashlib, datetime, glob

REPO_ROOT = pathlib.Path(sys.argv[0]).resolve().parents[1] if len(sys.argv) > 0 else pathlib.Path(".")
REPO_ROOT = pathlib.Path(".")
OUT = pathlib.Path("data/vector_lake")
OUT.mkdir(parents=True, exist_ok=True)

# Try to use world_vectors encoder if available
try:
    from world_vectors.encoder import encode_artifacts
    vectors = encode_artifacts(str(REPO_ROOT / "artifacts"))
    snap = {"timestamp": datetime.datetime.utcnow().isoformat(), "vectors": vectors}
    print(f"[embed] Encoded {len(vectors)} artifact vectors via world_vectors.encoder")
except Exception:
    # Fallback: fingerprint all source files as compact token index
    patterns = ["a2a_mcp/**/*.py", "orchestrator/**/*.py", "agents/**/*.py",
                "schemas/**/*.py", "mcp_servers/**/*.py", "telemetry/**/*.py"]
    artifacts = []
    for pat in patterns:
        for f in glob.glob(pat, recursive=True):
            try:
                data = pathlib.Path(f).read_bytes()
                fp = hashlib.sha256(data).hexdigest()[:16]
                # Encode fingerprint hex as a 16-dim float vector (each byte → [0,1])
                vec = [int(fp[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]
                artifacts.append({"path": f, "fingerprint": fp, "vector": vec})
            except Exception:
                pass
    snap = {"timestamp": datetime.datetime.utcnow().isoformat(),
            "commit": "local", "artifacts": artifacts}
    print(f"[embed] Fallback: indexed {len(artifacts)} source files as token vectors")

(OUT / "snapshot.json").write_text(json.dumps(snap, indent=2))
print(f"[embed] Snapshot written → {OUT}/snapshot.json")
PYEOF

  ok "Embed phase complete — vectors in ${VECTOR_LAKE_DIR}"
}

# =============================================================================
# PHASE: telemetry — Sentry sink
# Compacts loose vectors into geodesics and reports to Sentry.
# =============================================================================
run_telemetry() {
  log "=== Phase: Telemetry Flush (Sentry Sink) ==="
  if [[ -f "telemetry/sentry_sink.py" ]]; then
    python telemetry/sentry_sink.py \
      --vector-lake "${VECTOR_LAKE_DIR}" \
      --snapshot "${OUTPUT_DIR}/telemetry_snapshot.json" \
      2>&1 | tee "${OUTPUT_DIR}/telemetry.log"
  else
    warn "telemetry/sentry_sink.py not found — skipping Sentry flush"
  fi
  ok "Telemetry phase complete"
}

# =============================================================================
# PHASE: drift — Invariant / governance check
# =============================================================================
run_drift() {
  log "=== Phase: Drift Guard ==="
  python - <<'PYEOF'
import sys, pathlib
root = pathlib.Path(".")
failures = []

if list(root.glob("*.patch")):
    failures.append("Found committed .patch files in repo root")
if not (root / "orchestrator").exists():
    failures.append("orchestrator/ directory missing — canonical control plane broken")
if (root / ".venv").exists():
    failures.append(".venv present in repo root — should be gitignored")

if failures:
    for f in failures:
        print(f"DRIFT: {f}", file=sys.stderr)
    sys.exit(1)
else:
    print("Drift guard: all invariants pass ✓")
PYEOF
  ok "Drift check complete"
}

# =============================================================================
# Dispatch
# =============================================================================
case "${PHASE}" in
  all)
    run_lint
    run_test
    run_embed
    run_telemetry
    run_drift
    ;;
  lint)      run_lint ;;
  test)      run_test ;;
  embed)     run_embed ;;
  telemetry) run_telemetry ;;
  drift)     run_drift ;;
  *)
    fail "Unknown phase '${PHASE}'. Valid: all | lint | test | embed | telemetry | drift"
    ;;
esac

log "🏁 ${BOLD}Gemini OS Runner done — phase: ${PHASE}${RESET}"
