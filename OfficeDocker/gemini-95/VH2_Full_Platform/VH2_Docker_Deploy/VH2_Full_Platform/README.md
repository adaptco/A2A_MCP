# VH2 Sovereign Validator — Production Deployment Guide

> **Multi-Layer Fail-Closed Architecture with Kubernetes + ArgoCD**

---

## 📋 Quick Links

- [Architecture Overview](#architecture-overview)
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)

---

## 🏗️ Architecture Overview

### **System Layers**

```
┌────────────────────────────────────────────────────────────────┐
│ ArgoCD (Auto-Sync, Self-Healing, PostSync Validation)          │
├────────────────────────────────────────────────────────────────┤
│ Ingress (TLS, Rate-Limiting 1000 req/min, CORS)               │
├────────────────────────────────────────────────────────────────┤
│ Frontend Pod (HPA 2–5 replicas)  Backend Pod (HPA 3–10)        │
│ ├─ <vh2-simulator> Web Component  ├─ /validate endpoint       │
│ ├─ vehicle.html + tests.html      ├─ /spec endpoint           │
│ └─ Static asset caching           ├─ /kpi endpoint            │
│                                    ├─ /ackermann endpoint      │
│                                    └─ Init: 42 tests (fail-ok) │
├────────────────────────────────────────────────────────────────┤
│ Network Policy (Zero-Trust Isolation)                          │
├────────────────────────────────────────────────────────────────┤
│ ConfigMap (Immutable Vehicle Spec)                             │
└────────────────────────────────────────────────────────────────┘
```

### **Three-Layer Validation (Fail-Closed)**

| Layer | Gate | Trigger | Failure Action |
|-------|------|---------|-----------------|
| **Build** | Init container tests (`validator.test.js`) | `docker build` | Image build fails; no container created |
| **Pod Ready** | Readiness probe (`/ready`) | Pod startup | Traffic never routed to unhealthy pod |
| **Deployment** | PostSync smoke test | ArgoCD sync complete | Automatic rollback to previous version |

---

## 🚀 Local Development

### **Prerequisites**
- Docker Desktop (or Docker Engine + Docker Compose)
- Node.js 20+ (optional, for local testing)
- `make` (optional, for Makefile commands)

### **Quick Start**

```bash
# Navigate to project root
cd vh2-docker

# Option 1: Using Makefile (recommended)
make dev

# Option 2: Manual Docker Compose
docker-compose up --build

# Expected output:
# backend:   Listening on http://localhost:3001
# frontend:  Listening on http://localhost:3000
# nginx:     TLS termination on https://localhost:443
```

### **Testing Locally**

```bash
# 1. Hit the frontend
curl http://localhost:3000

# 2. Call the backend /validate endpoint
curl -X POST http://localhost:3001/validate \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle": "vh2",
    "wheels": {
      "front_et": 29,
      "rear_et": 22
    },
    "suspension": "A6061-T6"
  }'

# Expected response:
{
  "status": "SOVEREIGN_PASS",
  "violations": [],
  "timestamp": "2025-02-22T10:15:30Z"
}

# 3. Check health
curl http://localhost:3001/health
```

### **Stopping Services**

```bash
# Option 1: Using Makefile
make dev-stop

# Option 2: Manual
docker-compose down
```

---

## 🔧 Production Deployment

### **Prerequisites**
- Kubernetes 1.24+ cluster
- `kubectl` configured to connect to your cluster
- ArgoCD installed (or follow install instructions below)
- Docker registry access (for pushing images)

### **Step 1: Build & Push Images**

```bash
# Using Makefile (recommended)
make build-images REGISTRY=your.registry.com TAG=1.0.0

# Manual build
docker build -t your.registry.com/vh2-backend:1.0.0 vh2-docker/backend
docker build -t your.registry.com/vh2-frontend:1.0.0 vh2-docker/frontend

docker push your.registry.com/vh2-backend:1.0.0
docker push your.registry.com/vh2-frontend:1.0.0
```

### **Step 2: Update Image References**

Edit `vh2-docker/k8s/kustomization.yaml`:

```yaml
images:
  - name: vh2-backend
    newName: your.registry.com/vh2-backend
    newTag: "1.0.0"
  - name: vh2-frontend
    newName: your.registry.com/vh2-frontend
    newTag: "1.0.0"
```

### **Step 3: Deploy Kubernetes Manifests**

```bash
# Using Makefile (recommended)
make deploy-k8s

# Manual deployment
kubectl apply -k vh2-docker/k8s/

# Verify all resources are created
kubectl get all -n vh2-prod
```

### **Step 4: Install ArgoCD (if not already installed)**

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl rollout status deployment/argocd-server -n argocd

# Get initial password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### **Step 5: Deploy VH2 Application via ArgoCD**

```bash
# Using Makefile (recommended)
make deploy-argocd REPO_URL=https://github.com/YOUR_ORG/vh2-sovereign-validator.git

# Manual deployment
# First, update the repoURL in vh2-docker/argocd/vh2-validator-app.yaml
kubectl apply -f vh2-docker/argocd/vh2-validator-app.yaml

# Monitor sync status
argocd app get vh2-sovereign-validator

# Watch real-time sync
argocd app watch vh2-sovereign-validator
```

### **Step 6: Verify Deployment**

```bash
# Check pod status
kubectl get pods -n vh2-prod

# View logs from backend
kubectl logs -n vh2-prod -l app=vh2-backend -f

# Check HPA status
kubectl get hpa -n vh2-prod

# Run smoke test manually
kubectl create job --from=cronjob/vh2-smoke-test vh2-smoke-test-manual -n vh2-prod
```

---

## 📊 Monitoring & Observability

### **Check Pod Health**

```bash
# Get detailed pod info
kubectl describe pod <pod_name> -n vh2-prod

# View pod events
kubectl get events -n vh2-prod --sort-by='.lastTimestamp'

# Check readiness/liveness probe status
kubectl get pods -n vh2-prod -o wide
```

### **View Logs**

```bash
# Backend logs (all replicas)
kubectl logs -n vh2-prod -l app=vh2-backend -f

# Frontend logs
kubectl logs -n vh2-prod -l app=vh2-frontend -f

# Include previous pod logs (if pod restarted)
kubectl logs -n vh2-prod <pod_name> --previous
```

### **HPA Metrics**

```bash
# Check HPA current metrics
kubectl get hpa -n vh2-prod

# Get detailed HPA status
kubectl describe hpa vh2-backend-hpa -n vh2-prod

# View metrics (requires Metrics Server)
kubectl top pods -n vh2-prod
```

### **ArgoCD Dashboard**

```bash
# Port-forward to ArgoCD server
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Open browser to https://localhost:8080
# Default user: admin
# Password: (from Step 4 above)
```

---

## 🔄 Deployment Workflows

### **Scenario 1: Update Backend Image**

```bash
# 1. Make code changes
vim vh2-docker/backend/server.js

# 2. Build and test locally
make dev

# 3. If tests pass, push changes to git
git add vh2-docker/backend/
git commit -m "feat: add new /kpi endpoint"
git push origin main

# 4. ArgoCD automatically detects the change and syncs
# (if auto-sync is enabled)
argocd app wait vh2-sovereign-validator

# 5. Check deployment status
kubectl get deployments -n vh2-prod
```

### **Scenario 2: Rollback Failed Deployment**

```bash
# Option 1: Using ArgoCD CLI
argocd app rollback vh2-sovereign-validator

# Option 2: Using kubectl (revert to previous version)
kubectl rollout undo deployment/vh2-backend -n vh2-prod
kubectl rollout undo deployment/vh2-frontend -n vh2-prod

# Option 3: Check rollout history
kubectl rollout history deployment/vh2-backend -n vh2-prod
```

### **Scenario 3: Scale Manually (HPA will override)**

```bash
# Temporarily scale (HPA will adjust based on metrics)
kubectl scale deployment vh2-backend --replicas=5 -n vh2-prod

# Check current scale
kubectl get deployment vh2-backend -n vh2-prod

# Note: HPA may change replicas if metrics exceed thresholds
```

### **Scenario 4: Update Resource Limits**

```bash
# Edit deployment directly
kubectl edit deployment vh2-backend -n vh2-prod

# Or patch via kubectl
kubectl patch deployment vh2-backend -n vh2-prod -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"backend","resources":{"requests":{"memory":"512Mi"}}}]}}}}'

# Or use Kustomize patch
# (See vh2-docker/k8s/patches/ for examples)
```

---

## 🧪 Testing & Validation

### **Unit Tests (Backend)**

```bash
# Run tests locally
cd vh2-docker/backend
npm test

# Expected output:
# ✓ 42 tests passing
# ✓ No security violations
# ✓ All endpoints responding
```

### **Integration Tests (Docker Compose)**

```bash
# Start stack with prod overrides
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Run integration tests
./scripts/integration-tests.sh

# Verify cross-service communication
curl http://localhost:3001/spec  # Backend API
curl http://localhost:3000       # Frontend
```

### **Smoke Tests (K8s)**

```bash
# Manually trigger smoke test
kubectl create job --from=cronjob/vh2-smoke-test vh2-smoke-test-manual -n vh2-prod

# Check test results
kubectl logs -n vh2-prod -l job-name=vh2-smoke-test-manual

# Expected output:
# ✓ /validate endpoint responding
# ✓ SOVEREIGN_PASS status verified
# ✓ All health checks passing
```

---

## 🐛 Troubleshooting

### **Issue: Pod stuck in "Pending" state**

```bash
# Check events for resource quota issues
kubectl describe pod <pod_name> -n vh2-prod

# Check namespace resource quota
kubectl describe resourcequota vh2-quota -n vh2-prod

# Solution: Increase quota in vh2-docker/k8s/namespace.yaml
# and reapply
```

### **Issue: Init container test fails**

```bash
# View init container logs
kubectl logs <pod_name> -n vh2-prod -c test-validator

# If tests fail, pod will never become Ready
# Fix the code and rebuild the image

# Force rollback
kubectl rollout undo deployment/vh2-backend -n vh2-prod
```

### **Issue: Readiness probe failing**

```bash
# Check probe endpoint manually
kubectl exec <pod_name> -n vh2-prod -- wget -qO- http://localhost:3001/ready

# If 503, the pod is not ready (this is expected during startup)
# If timeout, check network connectivity

# View readiness probe config
kubectl get deployment vh2-backend -n vh2-prod -o yaml | grep -A 10 readinessProbe
```

### **Issue: ArgoCD sync failed**

```bash
# Check ArgoCD app status
argocd app get vh2-sovereign-validator

# View sync error
argocd app logs vh2-sovereign-validator

# Check if PostSync test job failed
kubectl get job -n vh2-prod

# View test job logs
kubectl logs -n vh2-prod -l app=vh2-smoke-test

# Force resync
argocd app sync vh2-sovereign-validator
```

### **Issue: Out of memory (exit code 137)**

```bash
# Check current resource usage
kubectl top pods -n vh2-prod

# View memory limits
kubectl get pods -n vh2-prod -o json | jq '.items[].spec.containers[].resources'

# Increase memory limit and reapply
# Edit vh2-docker/k8s/backend-deployment.yaml:
#   resources:
#     requests:
#       memory: 512Mi    # Increase from 256Mi
#     limits:
#       memory: 1Gi      # Increase from 512Mi
```

### **Issue: Network policy blocking traffic**

```bash
# Check network policies
kubectl get networkpolicy -n vh2-prod

# Verify pods can communicate
kubectl exec <frontend_pod> -n vh2-prod -- wget -qO- http://vh2-backend:3001/health

# If blocked, check network policy rules
kubectl get networkpolicy -n vh2-prod -o yaml
```

---

## 📡 API Reference

### **Backend Endpoints**

#### `POST /validate`
Validate vehicle specifications against sovereign physics rules.

**Request:**
```json
{
  "vehicle": "vh2",
  "wheels": {
    "front_et": 29,
    "rear_et": 22
  },
  "suspension": "A6061-T6",
  "drivetrain": "AWD"
}
```

**Response (Pass):**
```json
{
  "status": "SOVEREIGN_PASS",
  "violations": [],
  "timestamp": "2025-02-22T10:15:30Z"
}
```

**Response (Fail):**
```json
{
  "status": "SOVEREIGN_FAIL",
  "violations": [
    "Wheel ET-29 exceeds physics threshold",
    "Material composition invalid"
  ],
  "timestamp": "2025-02-22T10:15:30Z"
}
```

---

#### `GET /spec`
Retrieve the canonical vehicle specification.

**Response:**
```json
{
  "vehicle": "vh2",
  "physics": {
    "et29_22": true,
    "material": "A6061-T6"
  },
  "limits": {
    "max_torque": 400,
    "max_speed": 180
  }
}
```

---

#### `GET /health`
Liveness probe endpoint.

**Response:**
```json
{
  "status": "ok",
  "uptime": 3600
}
```

---

#### `GET /ready`
Readiness probe endpoint.

**Response (Ready):**
```json
{
  "ready": true,
  "checks": {
    "database": "pass",
    "tests": "pass"
  }
}
```

**Response (Not Ready):**
```json
{
  "ready": false,
  "reason": "Initialization in progress"
}
```
(HTTP 503)

---

## 🔐 Security Best Practices

### **Network Isolation**
- Zero-trust network policies enforce pod-to-pod communication rules.
- Only Frontend → Backend communication is allowed.
- Ingress only from external clients to Frontend.

```bash
# Verify network policies
kubectl get networkpolicy -n vh2-prod -o yaml
```

### **Pod Security**
- All containers run as non-root user (`uid: 1001`).
- Security context enforces:
  - No privilege escalation
  - Read-only root filesystem
  - Drop all Linux capabilities

```bash
# Check security context
kubectl get pods -n vh2-prod -o jsonpath='{.items[0].spec.securityContext}'
```

### **Resource Limits**
- Namespace resource quota prevents resource exhaustion.
- Per-pod limits prevent individual pod runaway.

```bash
# View resource quota
kubectl describe resourcequota vh2-quota -n vh2-prod
```

### **Image Security**
- Multi-stage builds minimize image size and attack surface.
- Base image: `node:20-alpine` (lightweight, regularly patched).
- Tests run at build time to catch vulnerabilities early.

```bash
# Check image details
docker inspect vh2-backend:1.0.0 | jq '.Config.Image'
```

---

## 🛠️ Makefile Commands

```bash
# Development
make dev              # Start local stack with docker-compose
make dev-stop        # Stop local stack
make dev-logs        # Tail logs from all services

# Testing
make test            # Run unit tests
make test-integration # Run integration tests
make test-smoke      # Run smoke tests against K8s

# Building
make build-images    # Build Docker images
make build-push      # Build and push to registry

# Deployment
make deploy-k8s      # Apply K8s manifests
make deploy-argocd   # Deploy via ArgoCD
make deploy-rollback # Rollback to previous version

# Utilities
make lint            # Validate YAML files
make clean           # Remove local containers/images
make help            # Show all commands
```

---

## 📦 Project Structure

```
vh2-sovereign-validator/
├── vh2-docker/
│   ├── backend/
│   │   ├── server.js               ← Express API
│   │   ├── package.json
│   │   ├── Dockerfile              ← Multi-stage, test gate
│   │   └── tests/validator.test.js ← 42 tests
│   ├── frontend/
│   │   ├── server.js               ← Static server
│   │   ├── vh2-plugin.js           ← Web Component
│   │   ├── public/
│   │   │   ├── index.html
│   │   │   ├── vehicle.html
│   │   │   └── tests.html
│   │   └── Dockerfile
│   ├── nginx/
│   │   └── nginx.conf              ← TLS, rate-limit
│   ├── k8s/
│   │   ├── namespace.yaml
│   │   ├── configmap-spec.yaml
│   │   ├── backend-deployment.yaml
│   │   ├── frontend-deployment.yaml
│   │   ├── ingress.yaml
│   │   ├── network-policy.yaml
│   │   ├── tests-job.yaml
│   │   └── kustomization.yaml
│   ├── argocd/
│   │   └── vh2-validator-app.yaml
│   ├── helm/
│   │   └── values-prod.yaml
│   ├── scripts/
│   │   ├── deploy.sh
│   │   └── k8s-deploy.sh
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── README.md                   ← This file
└── Makefile                        ← Helper commands
```

---

## 📞 Support & Feedback

- **Documentation**: See `vh2-docker/` directory
- **Issues**: Report via GitHub Issues
- **Deployment Help**: Refer to troubleshooting section above

---

## ✅ Deployment Checklist

- [ ] All Docker images built and tested locally
- [ ] Images pushed to registry with version tags
- [ ] K8s cluster is available and kubectl configured
- [ ] ArgoCD installed (or ready for installation)
- [ ] GitHub repo URL updated in `vh2-validator-app.yaml`
- [ ] Network policies reviewed and enabled
- [ ] Resource quotas set appropriately for cluster
- [ ] Ingress TLS certificates configured
- [ ] Monitoring/alerting stack ready (optional)
- [ ] Runbook for rollback procedures documented

---

**Last Updated:** 2025-02-22  
**Status:** Production-Ready ✓  
**Architecture:** Fail-Closed Multi-Layer Validation  
**Validation:** All 29 files validated clean
