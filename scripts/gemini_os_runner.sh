#!/usr/bin/env bash
# =============================================================================
# gemini_os_runner.sh — Gemini OS Pipeline Shell Runner
# =============================================================================
# Usage:  bash scripts/gemini_os_runner.sh [phase]
# Phases: all | lint | test | embed | telemetry | drift
#
<<<<<<< HEAD
# This script is the single entrypoint for the Gemini OS CI pipeline.
# It drives: lint → test → agent embed (vector lake) → telemetry flush
=======
# Single entrypoint for the Gemini OS CI pipeline.
# Drives: lint → test → agent embed (vector lake) → telemetry flush → drift guard
>>>>>>> origin/main
# =============================================================================

set -euo pipefail

PHASE="${1:-all}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${REPO_ROOT}/output"
VECTOR_LAKE_DIR="${REPO_ROOT}/data/vector_lake"

<<<<<<< HEAD
# ANSI colors
=======
>>>>>>> origin/main
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
<<<<<<< HEAD
    ruff check "${REPO_ROOT}" --output-format=text || warn "Ruff found issues (non-blocking)"
=======
    ruff check "${REPO_ROOT}" --output-format=text --exclude worktrees || warn "Ruff found issues (non-blocking)"
>>>>>>> origin/main
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
  if ! pytest "${REPO_ROOT}/tests" \
    -v \
    --tb=short \
    --junit-xml="${OUTPUT_DIR}/test-report.xml" \
    --ignore="${REPO_ROOT}/worktrees" \
<<<<<<< HEAD
    2>&1 | tee "${OUTPUT_DIR}/pytest.log"; then
    warn "Some tests failed — check ${OUTPUT_DIR}/pytest.log"
    return 1
=======
    --ignore="${REPO_ROOT}/OfficeDocker" \
    2>&1 | tee "${OUTPUT_DIR}/pytest.log"; then
    fail "Some tests failed — check ${OUTPUT_DIR}/pytest.log"
>>>>>>> origin/main
  fi
  ok "Test phase complete"
}

# =============================================================================
<<<<<<< HEAD
# PHASE: embed — Agent pipeline → Vector Data Lake
# Maps the pipeline structure as the data embedding layer for the vector space.
# Agents are treated as Avatars operating in 4D space, processing prompt tokens
# and mapping them into embedding vectors stored in data/vector_lake/.
# =============================================================================
run_embed() {
  log "=== Phase: Agent Embed (Vector Lake) ==="
  EMBED_SCRIPT="${REPO_ROOT}/scripts/embed_agents.py"

  if [[ -f "${EMBED_SCRIPT}" ]]; then
    python "${EMBED_SCRIPT}" \
      --output-dir "${VECTOR_LAKE_DIR}" \
      --model "${GEMINI_MODEL:-gemini-2.0-flash}" \
      2>&1 | tee "${OUTPUT_DIR}/embed.log"
  else
    # Inline minimal embedding using world_vectors module
    python -c "
import sys, json, pathlib, hashlib, datetime
sys.path.insert(0, '${REPO_ROOT}')

try:
    from world_vectors.encoder import encode_artifacts
    vectors = encode_artifacts('${REPO_ROOT}/artifacts')
    out = pathlib.Path('${VECTOR_LAKE_DIR}')
    out.mkdir(parents=True, exist_ok=True)
    snap = {
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'commit': '${GITHUB_SHA:-local}',
        'vectors': vectors
    }
    (out / 'snapshot.json').write_text(json.dumps(snap, indent=2))
    print(f'[embed] Wrote {len(vectors)} vectors to ${VECTOR_LAKE_DIR}/snapshot.json')
except ImportError:
    # Fallback: write a manifest of all artifact files as compact token index
    import glob
    artifacts = glob.glob('${REPO_ROOT}/artifacts/**/*', recursive=True)
    manifest = [
        {
            'path': a,
            'fingerprint': hashlib.sha256(open(a,'rb').read()).hexdigest()[:16]
              if pathlib.Path(a).is_file() else None
        }
        for a in artifacts
    ]
    out = pathlib.Path('${VECTOR_LAKE_DIR}')
    out.mkdir(parents=True, exist_ok=True)
    snap = {'timestamp': datetime.datetime.utcnow().isoformat(), 'artifacts': manifest}
    (out / 'snapshot.json').write_text(json.dumps(snap, indent=2))
    print(f'[embed] Fallback: indexed {len(manifest)} artifacts')
"
  fi
=======
# PHASE: embed - Agent pipeline -> Vector Data Lake
# Maps the agent pipeline as the data embedding layer for the vector space.
# Agents are Avatars in 4D space; their prompt tokens are encoded as embedding
# vectors and stored in data/vector_lake/ as the stateful data lake.
# =============================================================================
run_embed() {
  log "=== Phase: Agent Embed (Vector Lake) ==="

  python - <<'PYEOF'
import sys, json, pathlib, hashlib, datetime, glob

REPO_ROOT = pathlib.Path(".")
OUT = pathlib.Path("data/vector_lake")
OUT.mkdir(parents=True, exist_ok=True)

# Try to use world_vectors encoder if available
try:
    from world_vectors.encoder import encode_artifacts
except ImportError:
    encode_artifacts = None

if encode_artifacts is not None:
    artifacts = encode_artifacts(str(REPO_ROOT / "artifacts"))
    snap = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "commit": "local",
        "artifacts": artifacts,
    }
    print(f"[embed] Encoded {len(artifacts)} artifact vectors via world_vectors.encoder")
else:
    # Fallback: fingerprint all source files as compact token index
    patterns = ["a2a_mcp/**/*.py", "orchestrator/**/*.py", "agents/**/*.py",
                "schemas/**/*.py", "mcp_servers/**/*.py", "telemetry/**/*.py"]
    artifacts = []
    for pat in patterns:
        for f in glob.glob(pat, recursive=True):
            try:
                data = pathlib.Path(f).read_bytes()
                fp = hashlib.sha256(data).hexdigest()[:16]
                # Encode fingerprint hex as a 16-dim float vector (each byte -> [0,1])
                vec = [int(fp[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]
                artifacts.append({"path": f, "fingerprint": fp, "vector": vec})
            except Exception:
                pass
    snap = {"timestamp": datetime.datetime.utcnow().isoformat(),
            "commit": "local", "artifacts": artifacts}
    print(f"[embed] Fallback: indexed {len(artifacts)} source files as token vectors")

(OUT / "snapshot.json").write_text(json.dumps(snap, indent=2))
print(f"[embed] Snapshot written -> {OUT}/snapshot.json")
PYEOF

>>>>>>> origin/main
  ok "Embed phase complete — vectors in ${VECTOR_LAKE_DIR}"
}

# =============================================================================
<<<<<<< HEAD
# PHASE: telemetry — Sentry sink (compact loose vectors into geodesics)
# Consumes loose artifact vectors, computes geodesic centroids (cosine means),
# and reports the compacted stateful runtime embedding to Sentry.
# =============================================================================
run_telemetry() {
  log "=== Phase: Telemetry Flush (Sentry Sink) ==="
  SENTRY_SCRIPT="${REPO_ROOT}/telemetry/sentry_sink.py"

  if [[ -f "${SENTRY_SCRIPT}" ]]; then
    python "${SENTRY_SCRIPT}" \
=======
# PHASE: telemetry — Sentry sink
# Compacts loose vectors into geodesics and reports to Sentry.
# =============================================================================
run_telemetry() {
  log "=== Phase: Telemetry Flush (Sentry Sink) ==="
  if [[ -f "telemetry/sentry_sink.py" ]]; then
    python telemetry/sentry_sink.py \
>>>>>>> origin/main
      --vector-lake "${VECTOR_LAKE_DIR}" \
      --snapshot "${OUTPUT_DIR}/telemetry_snapshot.json" \
      2>&1 | tee "${OUTPUT_DIR}/telemetry.log"
  else
<<<<<<< HEAD
    warn "telemetry/sentry_sink.py not found — skipping flush"
=======
    warn "telemetry/sentry_sink.py not found — skipping Sentry flush"
>>>>>>> origin/main
  fi
  ok "Telemetry phase complete"
}

# =============================================================================
# PHASE: drift — Invariant / governance check
# =============================================================================
run_drift() {
  log "=== Phase: Drift Guard ==="
<<<<<<< HEAD
  DRIFT_SCRIPT="${REPO_ROOT}/scripts/drift_check.py"

  if [[ -f "${DRIFT_SCRIPT}" ]]; then
    python "${DRIFT_SCRIPT}" 2>&1 | tee "${OUTPUT_DIR}/drift.log"
  else
    # Basic invariant checks
    python -c "
import sys, pathlib
root = pathlib.Path('${REPO_ROOT}')
failures = []

# Invariant 1: no committed .patch files
patches = list(root.glob('*.patch'))
if patches:
    failures.append(f'Found committed patch files: {patches}')

# Invariant 2: orchestrator module must exist
if not (root / 'orchestrator' / 'api.py').exists():
    failures.append('orchestrator/api.py missing — canonical control plane broken')

# Invariant 3: no .venv in repo root
if (root / '.venv').exists():
    failures.append('.venv committed to repo root — should be gitignored')

if failures:
    for f in failures:
        print(f'DRIFT: {f}', file=sys.stderr)
    sys.exit(1)
else:
    print('Drift guard: all invariants pass')
"
  fi
=======
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
>>>>>>> origin/main
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

<<<<<<< HEAD
log "🏁 ${BOLD}Gemini OS Runner finished — phase: ${PHASE}${RESET}"
=======
log "🏁 ${BOLD}Gemini OS Runner done — phase: ${PHASE}${RESET}"
>>>>>>> origin/main
