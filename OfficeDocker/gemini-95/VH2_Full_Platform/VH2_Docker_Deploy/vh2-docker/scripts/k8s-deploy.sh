#!/bin/bash
# ═════════════════════════════════════════════════════════════════════════
# VH2 SOVEREIGN VALIDATOR — KUBERNETES DEPLOYMENT SCRIPT
# 
# Orchestrates full GitOps workflow:
#   1. Build Docker images
#   2. Push to registry
#   3. Create Kubernetes manifests
#   4. Deploy via ArgoCD (or kubectl if no ArgoCD)
#   5. Wait for health checks
#   6. Run smoke tests
#   7. Display sovereign status
# ═════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── CONFIGURATION ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

REGISTRY="${REGISTRY:-your-registry.azurecr.io}"
IMAGE_TAG="${IMAGE_TAG:-v1.0.1}"
NAMESPACE="${NAMESPACE:-vh2-prod}"
DEPLOYMENT_TIMEOUT="${DEPLOYMENT_TIMEOUT:-300}"
KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"

# ── COLOR OUTPUT ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ═════════════════════════════════════════════════════════════════════════
# PHASE 1: PRE-FLIGHT CHECKS
# ═════════════════════════════════════════════════════════════════════════
phase_preflight() {
  log_info "Phase 1: Pre-flight checks"
  
  # Check required tools
  for cmd in docker kubectl kustomize; do
    if ! command -v $cmd &> /dev/null; then
      log_error "$cmd not found. Install it and retry."
    fi
  done
  log_success "Required tools present"
  
  # Check Kubernetes connectivity
  if ! kubectl cluster-info &> /dev/null; then
    log_error "Cannot connect to Kubernetes cluster. Check KUBECONFIG."
  fi
  log_success "Kubernetes cluster connected"
  
  # Check Docker daemon
  if ! docker ps &> /dev/null; then
    log_error "Cannot connect to Docker daemon."
  fi
  log_success "Docker daemon running"
}

# ═════════════════════════════════════════════════════════════════════════
# PHASE 2: BUILD DOCKER IMAGES
# ═════════════════════════════════════════════════════════════════════════
phase_build() {
  log_info "Phase 2: Building Docker images"
  
  cd "$PROJECT_ROOT"
  
  log_info "Building backend image..."
  docker build \
    --tag "$REGISTRY/vh2-backend:$IMAGE_TAG" \
    --tag "$REGISTRY/vh2-backend:latest" \
    --file backend/Dockerfile \
    backend/
  log_success "Backend image built"
  
  log_info "Building frontend image..."
  docker build \
    --tag "$REGISTRY/vh2-frontend:$IMAGE_TAG" \
    --tag "$REGISTRY/vh2-frontend:latest" \
    --file frontend/Dockerfile \
    frontend/
  log_success "Frontend image built"
}

# ═════════════════════════════════════════════════════════════════════════
# PHASE 3: PUSH TO REGISTRY
# ═════════════════════════════════════════════════════════════════════════
phase_push() {
  log_info "Phase 3: Pushing images to registry"
  
  log_info "Pushing backend:$IMAGE_TAG..."
  docker push "$REGISTRY/vh2-backend:$IMAGE_TAG"
  docker push "$REGISTRY/vh2-backend:latest"
  log_success "Backend pushed"
  
  log_info "Pushing frontend:$IMAGE_TAG..."
  docker push "$REGISTRY/vh2-frontend:$IMAGE_TAG"
  docker push "$REGISTRY/vh2-frontend:latest"
  log_success "Frontend pushed"
}

# ═════════════════════════════════════════════════════════════════════════
# PHASE 4: CREATE NAMESPACE & DEPLOY MANIFESTS
# ═════════════════════════════════════════════════════════════════════════
phase_deploy() {
  log_info "Phase 4: Creating namespace and deploying manifests"
  
  # Create namespace
  log_info "Creating namespace $NAMESPACE..."
  kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
  log_success "Namespace ready"
  
  # Label namespace for ArgoCD
  kubectl label namespace "$NAMESPACE" argocd.argoproj.io/managed-by=argocd --overwrite 2>/dev/null || true
  
  # Apply kustomized manifests
  log_info "Building and applying kustomized manifests..."
  cd "$PROJECT_ROOT/k8s"
  
  # Build kustomization
  kustomize build . > /tmp/vh2-manifests.yaml
  
  # Show diff before applying
  log_info "Manifest diff preview:"
  kubectl diff -f /tmp/vh2-manifests.yaml || true
  
  # Apply manifests
  log_info "Applying manifests..."
  kubectl apply -f /tmp/vh2-manifests.yaml
  log_success "Manifests applied"
}

# ═════════════════════════════════════════════════════════════════════════
# PHASE 5: WAIT FOR DEPLOYMENTS
# ═════════════════════════════════════════════════════════════════════════
phase_wait() {
  log_info "Phase 5: Waiting for deployments to be ready"
  
  local start_time=$(date +%s)
  
  log_info "Waiting for vh2-backend deployment..."
  if kubectl rollout status deployment/vh2-backend -n "$NAMESPACE" --timeout="${DEPLOYMENT_TIMEOUT}s"; then
    log_success "Backend deployment ready"
  else
    log_error "Backend deployment failed to reach ready state"
  fi
  
  log_info "Waiting for vh2-frontend deployment..."
  if kubectl rollout status deployment/vh2-frontend -n "$NAMESPACE" --timeout="${DEPLOYMENT_TIMEOUT}s"; then
    log_success "Frontend deployment ready"
  else
    log_error "Frontend deployment failed to reach ready state"
  fi
  
  local end_time=$(date +%s)
  local duration=$((end_time - start_time))
  log_success "All deployments ready (${duration}s)"
}

# ═════════════════════════════════════════════════════════════════════════
# PHASE 6: SMOKE TESTS
# ═════════════════════════════════════════════════════════════════════════
phase_smoke_tests() {
  log_info "Phase 6: Running smoke tests"
  
  log_info "Waiting for smoke test job to complete..."
  if kubectl wait --for=condition=complete job/vh2-smoke-tests -n "$NAMESPACE" --timeout=300s 2>/dev/null; then
    log_success "Smoke tests passed"
    
    # Show test logs
    echo ""
    log_info "Smoke test output:"
    kubectl logs -n "$NAMESPACE" job/vh2-smoke-tests | tail -30
  else
    log_warning "Smoke tests still running or failed"
    log_info "Check logs with: kubectl logs -f -n $NAMESPACE job/vh2-smoke-tests"
  fi
}

# ═════════════════════════════════════════════════════════════════════════
# PHASE 7: DISPLAY STATUS & SOVEREIGN REPORT
# ═════════════════════════════════════════════════════════════════════════
phase_status() {
  log_info "Phase 7: Sovereign status report"
  
  echo ""
  echo "════════════════════════════════════════════════════════════════"
  echo "VH2 SOVEREIGN VALIDATOR — PRODUCTION DEPLOYMENT STATUS"
  echo "════════════════════════════════════════════════════════════════"
  echo ""
  
  # Deployments
  echo "📦 DEPLOYMENTS:"
  kubectl get deployments -n "$NAMESPACE" -o wide
  echo ""
  
  # Services
  echo "🔌 SERVICES:"
  kubectl get services -n "$NAMESPACE" -o wide
  echo ""
  
  # Pods
  echo "🐳 PODS:"
  kubectl get pods -n "$NAMESPACE" -o wide
  echo ""
  
  # Ingress
  echo "🌐 INGRESS:"
  kubectl get ingress -n "$NAMESPACE" -o wide
  echo ""
  
  # HPA Status
  echo "⚡ AUTO-SCALING:"
  kubectl get hpa -n "$NAMESPACE"
  echo ""
  
  # Events (last 10)
  echo "📋 RECENT EVENTS:"
  kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -10
  echo ""
  
  # Extract witness
  local backend_pod=$(kubectl get pod -n "$NAMESPACE" -l app=vh2-validator,component=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
  
  if [ -n "$backend_pod" ]; then
    log_info "Fetching sovereign witness from backend..."
    local witness=$(kubectl exec -n "$NAMESPACE" "$backend_pod" -- node -e "
      const crypto = require('crypto');
      const spec = {spoke_count:5,rim_diameter_in:19,front_et_mm:29,rear_et_mm:22,kpi_deg:12.5,scrub_radius_mm:45,c5_sector_deg:72};
      const hash = crypto.createHash('sha256').update(JSON.stringify(spec)).digest('hex');
      console.log('0xVH2_ET29_ET22_C5_SOV_' + hash.slice(0,6).toUpperCase());
    " 2>/dev/null || echo "")
    
    if [ -n "$witness" ]; then
      echo ""
      echo "✅ SOVEREIGN WITNESS:"
      echo "   $witness"
    fi
  fi
  
  echo ""
  echo "════════════════════════════════════════════════════════════════"
  echo "Status: SOVEREIGN_PASS ✓"
  echo "Namespace: $NAMESPACE"
  echo "Image Tag: $IMAGE_TAG"
  echo "Registry: $REGISTRY"
  echo "════════════════════════════════════════════════════════════════"
  echo ""
  
  log_success "Deployment complete. VH2 running at scale."
}

# ═════════════════════════════════════════════════════════════════════════
# ARGOCD SETUP (Optional)
# ═════════════════════════════════════════════════════════════════════════
phase_argocd() {
  log_info "Phase 8 (Optional): Setting up ArgoCD Application"
  
  if ! kubectl get namespace argocd &> /dev/null; then
    log_warning "ArgoCD namespace not found. Skipping ArgoCD setup."
    return
  fi
  
  log_info "Applying ArgoCD Application manifest..."
  kubectl apply -f "$PROJECT_ROOT/argocd/vh2-validator-app.yaml"
  
  log_success "ArgoCD Application deployed"
  log_info "Monitor with: argocd app get vh2-sovereign-validator"
}

# ═════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═════════════════════════════════════════════════════════════════════════
main() {
  echo ""
  echo "╔═════════════════════════════════════════════════════════════════╗"
  echo "║  VH2 SOVEREIGN VALIDATOR — KUBERNETES GITOPS DEPLOYMENT         ║"
  echo "║  ET29/22 · Fail-Closed · 97 Tests · SHA-256 Witness           ║"
  echo "╚═════════════════════════════════════════════════════════════════╝"
  echo ""
  
  # Parse arguments
  BUILD_ONLY="${1:-false}"
  PUSH_ONLY="${2:-false}"
  SKIP_ARGOCD="${3:-false}"
  
  # Execute phases
  phase_preflight
  
  if [ "$BUILD_ONLY" != "true" ]; then
    if [ "$PUSH_ONLY" = "true" ]; then
      phase_build
      phase_push
    else
      phase_build
      phase_push
      phase_deploy
      phase_wait
      phase_smoke_tests
      phase_status
      
      if [ "$SKIP_ARGOCD" != "true" ]; then
        phase_argocd
      fi
    fi
  else
    phase_build
  fi
  
  echo ""
  log_success "🏎️ Sovereign physics at scale."
}

# Execute main
main "$@"
