#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════
# VH2 SOVEREIGN VALIDATOR — Kubernetes / ArgoCD Deploy Script
#
# Usage:
#   ./scripts/k8s-deploy.sh              # full GitOps pipeline
#   ./scripts/k8s-deploy.sh prereqs      # check kubectl/argocd/kustomize
#   ./scripts/k8s-deploy.sh build-push   # build images + push to registry
#   ./scripts/k8s-deploy.sh kustomize    # dry-run kustomize manifests
#   ./scripts/k8s-deploy.sh apply        # kubectl apply (without ArgoCD)
#   ./scripts/k8s-deploy.sh argocd       # register + sync ArgoCD app
#   ./scripts/k8s-deploy.sh smoke        # run live smoke tests
#   ./scripts/k8s-deploy.sh rollback     # rollback to previous ArgoCD revision
#   ./scripts/k8s-deploy.sh status       # show pod + hpa + ingress status
#   ./scripts/k8s-deploy.sh teardown     # delete all k8s resources
#
# Env vars (override as needed):
#   REGISTRY    Image registry prefix (default: local)
#   IMAGE_TAG   Image tag             (default: git short SHA)
#   DOMAIN      Ingress hostname      (default: vh2.yourdomain.com)
#   REPO_URL    Git repo for ArgoCD   (default: prompt)
#   NAMESPACE   K8s namespace         (default: vh2-prod)
#   ARGOCD_NS   ArgoCD namespace      (default: argocd)
# ════════════════════════════════════════════════════════════════════════

set -euo pipefail
IFS=$'\n\t'

# ── COLOUR PALETTE ─────────────────────────────────────────────────────────
G='\033[38;5;178m'   # gold
OK='\033[38;5;114m'  # green
ERR='\033[38;5;160m' # red
CY='\033[38;5;80m'   # cyan
DIM='\033[38;5;239m' # dim
RST='\033[0m'

log()  { echo -e "${DIM}[$(date +%H:%M:%S)]${RST} $*"; }
ok()   { echo -e "${OK}  ✓${RST} $*"; }
err()  { echo -e "${ERR}  ✗ $*${RST}"; }
step() { echo -e "\n${G}══ $* ${RST}"; }
die()  { err "$*"; exit 1; }

# ── CONFIG ─────────────────────────────────────────────────────────────────
REGISTRY="${REGISTRY:-}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')}"
DOMAIN="${DOMAIN:-vh2.yourdomain.com}"
NAMESPACE="${NAMESPACE:-vh2-prod}"
ARGOCD_NS="${ARGOCD_NS:-argocd}"
ARGOCD_APP="vh2-sovereign-validator"
K8S_DIR="$(cd "$(dirname "$0")/../k8s" && pwd)"
ARGOCD_DIR="$(cd "$(dirname "$0")/../argocd" && pwd)"

banner() {
  echo -e "${G}"
  echo "  ╔══════════════════════════════════════════════════════════╗"
  echo "  ║  VH2 · SOVEREIGN VALIDATOR · KUBERNETES DEPLOY          ║"
  echo "  ║  ArgoCD GitOps · Kustomize · Fail-Closed · SHA-256      ║"
  echo "  ╚══════════════════════════════════════════════════════════╝${RST}"
  echo -e "  ${DIM}tag:${RST} ${IMAGE_TAG}  ${DIM}ns:${RST} ${NAMESPACE}  ${DIM}domain:${RST} ${DOMAIN}"
  echo ""
}

# ── PREREQ CHECK ───────────────────────────────────────────────────────────
check_prereqs() {
  step "PREREQUISITE CHECK"
  local ok=true

  for cmd in kubectl kustomize docker; do
    if command -v "$cmd" &>/dev/null; then
      ok "$cmd: $(command -v $cmd)"
    else
      err "$cmd not found"
      ok=false
    fi
  done

  # argocd CLI (optional — needed for argocd subcommand only)
  if command -v argocd &>/dev/null; then
    ok "argocd CLI: $(command -v argocd)"
  else
    log "argocd CLI not found (needed only for 'argocd' subcommand)"
  fi

  # kubectl connectivity
  if kubectl cluster-info &>/dev/null; then
    ok "kubectl cluster reachable: $(kubectl config current-context)"
  else
    err "kubectl cannot reach cluster — check KUBECONFIG"
    ok=false
  fi

  [[ "$ok" == "true" ]] || die "Prerequisites missing"
}

# ── IMAGE BUILD + PUSH ─────────────────────────────────────────────────────
build_push_images() {
  step "BUILD & PUSH IMAGES  (tag: ${IMAGE_TAG})"

  local BACKEND_IMG="${REGISTRY}vh2-backend:${IMAGE_TAG}"
  local FRONTEND_IMG="${REGISTRY}vh2-frontend:${IMAGE_TAG}"

  log "Building backend socket…"
  docker build -t "$BACKEND_IMG" ./backend
  ok "Backend: $BACKEND_IMG"

  log "Building frontend socket…"
  docker build -t "$FRONTEND_IMG" ./frontend
  ok "Frontend: $FRONTEND_IMG"

  if [[ -n "$REGISTRY" ]]; then
    log "Pushing to registry…"
    docker push "$BACKEND_IMG"
    docker push "$FRONTEND_IMG"
    ok "Images pushed to ${REGISTRY}"
  else
    log "No REGISTRY set — images built locally only"
    log "For remote cluster: export REGISTRY=ghcr.io/your-org/"
  fi

  # Update kustomization.yaml image tags
  cd "$K8S_DIR"
  kustomize edit set image "vh2-backend=${BACKEND_IMG}"
  kustomize edit set image "vh2-frontend=${FRONTEND_IMG}"
  ok "kustomization.yaml image tags updated"
  cd - > /dev/null
}

# ── KUSTOMIZE DRY-RUN ──────────────────────────────────────────────────────
kustomize_preview() {
  step "KUSTOMIZE DRY-RUN"
  log "Rendering manifests from ${K8S_DIR}…"
  kustomize build "$K8S_DIR" | head -120
  echo "  ${DIM}… (truncated — run: kustomize build k8s/ for full output)${RST}"
  ok "Kustomize render complete"
}

# ── KUBECTL APPLY (without ArgoCD) ─────────────────────────────────────────
kubectl_apply() {
  step "KUBECTL APPLY"
  log "Applying namespace first…"
  kubectl apply -f "$K8S_DIR/namespace.yaml"

  log "Applying all resources via kustomize…"
  kustomize build "$K8S_DIR" | kubectl apply -f -
  ok "Resources applied to cluster"

  log "Waiting for backend rollout…"
  kubectl rollout status deployment/vh2-backend  -n "$NAMESPACE" --timeout=180s
  log "Waiting for frontend rollout…"
  kubectl rollout status deployment/vh2-frontend -n "$NAMESPACE" --timeout=120s
  ok "Rollouts complete"
}

# ── ARGOCD REGISTER + SYNC ─────────────────────────────────────────────────
argocd_deploy() {
  step "ARGOCD GITOPS DEPLOY"
  command -v argocd &>/dev/null || die "argocd CLI required — brew install argocd"

  # Check ArgoCD is running
  kubectl get namespace "$ARGOCD_NS" &>/dev/null || die "ArgoCD namespace '${ARGOCD_NS}' not found"

  log "Applying ArgoCD Application manifest…"
  kubectl apply -f "$ARGOCD_DIR/vh2-validator-app.yaml"
  ok "Application manifest applied"

  log "Triggering sync…"
  argocd app sync "$ARGOCD_APP" --prune --force || true

  log "Waiting for sync + health…"
  argocd app wait "$ARGOCD_APP" \
    --sync \
    --health \
    --timeout 300 \
    --operation \
    && ok "ArgoCD: SYNCED + HEALTHY" \
    || die "ArgoCD sync/health check failed"

  log "App status:"
  argocd app get "$ARGOCD_APP" --grpc-web
}

# ── SMOKE TESTS ────────────────────────────────────────────────────────────
run_smoke() {
  step "LIVE SMOKE TESTS"
  log "Launching smoke test Job…"

  # Delete old job if exists
  kubectl delete job vh2-smoke-test -n "$NAMESPACE" --ignore-not-found

  # Apply job
  kubectl apply -f "$K8S_DIR/tests-job.yaml"

  log "Waiting for Job completion (timeout: 120s)…"
  kubectl wait job/vh2-smoke-test \
    -n "$NAMESPACE" \
    --for=condition=complete \
    --timeout=120s \
    && ok "Smoke tests PASSED" \
    || {
      err "Smoke tests FAILED"
      kubectl logs -n "$NAMESPACE" \
        "$(kubectl get pods -n "$NAMESPACE" -l app=vh2-smoke-test -o name | head -1)"
      die "Smoke test failure — check logs above"
    }

  kubectl logs -n "$NAMESPACE" \
    "$(kubectl get pods -n "$NAMESPACE" -l app=vh2-smoke-test -o name | head -1)" 2>/dev/null || true
}

# ── ROLLBACK ───────────────────────────────────────────────────────────────
rollback() {
  step "ROLLBACK"
  if command -v argocd &>/dev/null; then
    log "Rolling back via ArgoCD…"
    argocd app rollback "$ARGOCD_APP" --timeout 120
    ok "ArgoCD rollback initiated"
  else
    log "Rolling back via kubectl…"
    kubectl rollout undo deployment/vh2-backend  -n "$NAMESPACE"
    kubectl rollout undo deployment/vh2-frontend -n "$NAMESPACE"
    ok "kubectl rollback complete"
  fi
}

# ── STATUS ─────────────────────────────────────────────────────────────────
show_status() {
  step "CLUSTER STATUS"
  echo -e "${DIM}── Pods ───────────────────────────────────────${RST}"
  kubectl get pods -n "$NAMESPACE" -o wide 2>/dev/null || echo "  (namespace not found)"

  echo -e "\n${DIM}── Services ───────────────────────────────────${RST}"
  kubectl get svc -n "$NAMESPACE" 2>/dev/null || true

  echo -e "\n${DIM}── HPA ─────────────────────────────────────────${RST}"
  kubectl get hpa -n "$NAMESPACE" 2>/dev/null || true

  echo -e "\n${DIM}── Ingress ──────────────────────────────────────${RST}"
  kubectl get ingress -n "$NAMESPACE" 2>/dev/null || true

  if command -v argocd &>/dev/null; then
    echo -e "\n${DIM}── ArgoCD ────────────────────────────────────────${RST}"
    argocd app get "$ARGOCD_APP" --grpc-web 2>/dev/null || true
  fi

  echo ""
  echo -e "  ${CY}https://${DOMAIN}${RST}          — Plugin demo"
  echo -e "  ${CY}https://${DOMAIN}/api/spec${RST}  — Canonical spec"
  echo -e "  ${CY}https://${DOMAIN}/health${RST}    — Health probe"
}

# ── TEARDOWN ───────────────────────────────────────────────────────────────
teardown() {
  step "TEARDOWN"
  read -p "  This will DELETE all VH2 resources. Confirm [y/N]: " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || { log "Cancelled"; return; }

  if command -v argocd &>/dev/null; then
    argocd app delete "$ARGOCD_APP" --yes 2>/dev/null || true
  fi
  kubectl delete namespace "$NAMESPACE" --ignore-not-found
  ok "All VH2 resources removed"
}

# ── COMMAND ROUTER ─────────────────────────────────────────────────────────
CMD="${1:-deploy}"
banner

case "$CMD" in
  prereqs)    check_prereqs ;;
  build-push) check_prereqs; build_push_images ;;
  kustomize)  kustomize_preview ;;
  apply)      check_prereqs; kubectl_apply ;;
  argocd)     check_prereqs; argocd_deploy ;;
  smoke)      run_smoke ;;
  rollback)   rollback ;;
  status)     show_status ;;
  teardown)   teardown ;;
  deploy|*)
    check_prereqs
    build_push_images
    kubectl_apply
    run_smoke
    show_status
    echo ""
    echo -e "${OK}  ══ VH2 SOVEREIGN VALIDATOR — DEPLOYED ══${RST}"
    echo -e "  ${G}https://${DOMAIN}${RST}"
    ;;
esac
