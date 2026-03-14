# VH2 Sovereign Validator — ArgoCD GitOps Complete Setup

## 🎯 Overview

This guide walks through the complete GitOps deployment of the VH2 Sovereign Validator on Kubernetes using ArgoCD.

**End-to-end workflow:**
```
git push main → ArgoCD sync → Kustomize build → Kubectl apply → 
Init container tests → Deployments ready → Smoke tests → SOVEREIGN_PASS ✓
```

---

## 📋 Prerequisites

- **Kubernetes cluster** (1.24+) with default StorageClass
- **ArgoCD 2.8+** installed (`argocd` namespace)
- **Ingress controller** (nginx recommended)
- **cert-manager** (optional, for TLS)
- **kubectl**, **kustomize**, **helm** CLI tools
- **Docker registry** (Docker Hub, ACR, ECR, etc.)
- **GitHub** repository (fork/clone of vh2-docker)

### Quick Install

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl rollout status deployment/argocd-server -n argocd

# Login to ArgoCD CLI
argocd login argocd-server --grpc
```

---

## 🔧 Setup Steps

### Step 1: Update Configuration

Edit the following files with your values:

**`argocd/vh2-validator-app.yaml`:**
```yaml
spec:
  source:
    repoURL: https://github.com/YOUR-ORG/vh2-docker.git  # ← Your fork
    targetRevision: main
    path: k8s
```

**`helm/values-prod.yaml`:**
```yaml
global:
  domain: yourdomain.com

backend:
  image:
    registry: your-registry.azurecr.io  # ← Your registry

ingress:
  hosts:
  - host: vh2-prod.yourdomain.com  # ← Your domain
    paths:
    - path: /
      backend: frontend
```

**`k8s/ingress.yaml`:**
```yaml
spec:
  rules:
  - host: vh2-prod.yourdomain.com  # ← Your domain
    http:
      paths:
      - path: /
        backend:
          service:
            name: vh2-frontend
```

### Step 2: Push Docker Images to Registry

```bash
# Build images locally
cd vh2-docker
docker compose build

# Tag for registry
docker tag vh2-docker-backend:latest your-registry/vh2-backend:v1.0.1
docker tag vh2-docker-frontend:latest your-registry/vh2-frontend:v1.0.1

# Push to registry
docker push your-registry/vh2-backend:v1.0.1
docker push your-registry/vh2-frontend:v1.0.1
```

Or use the automated script:

```bash
export REGISTRY=your-registry
export IMAGE_TAG=v1.0.1
./scripts/k8s-deploy.sh build
```

### Step 3: Create Docker Registry Secret (if private)

```bash
kubectl create secret docker-registry regcred \
  --docker-server=your-registry \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email> \
  -n argocd

# Reference in values-prod.yaml:
# global.image.pullSecrets[0].name: regcred
```

### Step 4: Deploy ArgoCD Application

```bash
# Create the ArgoCD Application
kubectl apply -f argocd/vh2-validator-app.yaml

# Verify application is created
argocd app get vh2-sovereign-validator

# Sync manually (or wait for auto-sync)
argocd app sync vh2-sovereign-validator

# Watch rollout
argocd app wait vh2-sovereign-validator --sync
```

### Step 5: Verify Deployment

```bash
# Check application status
argocd app get vh2-sovereign-validator

# View pods
kubectl get pods -n vh2-prod

# View services
kubectl get services -n vh2-prod

# View ingress
kubectl get ingress -n vh2-prod

# Check events
kubectl get events -n vh2-prod --sort-by='.lastTimestamp'
```

### Step 6: Access the Application

```bash
# Get ingress IP
kubectl get ingress -n vh2-prod

# Add to /etc/hosts (or use DNS)
# <INGRESS-IP> vh2-prod.yourdomain.com

# Access in browser
# https://vh2-prod.yourdomain.com

# Direct port-forward (if no ingress)
kubectl port-forward -n vh2-prod svc/vh2-backend 3001:3001
kubectl port-forward -n vh2-prod svc/vh2-frontend 3000:3000
```

---

## 🚀 GitOps Workflow

### Automated Deployment (recommended)

```bash
# 1. Make changes to code
git commit -am "Improve KPI validation"

# 2. Build and push new image
export IMAGE_TAG=v1.0.2
docker build -t your-registry/vh2-backend:$IMAGE_TAG backend/
docker push your-registry/vh2-backend:$IMAGE_TAG

# 3. Update Kustomization or values
# Edit k8s/kustomization.yaml or helm/values-prod.yaml

# 4. Commit and push
git add k8s/ helm/
git commit -m "Deploy v1.0.2 to production"
git push origin main

# 5. ArgoCD automatically syncs (if auto-sync is enabled)
# Monitor with:
argocd app watch vh2-sovereign-validator
```

### Using the Deployment Script

```bash
# One-command deploy (build, push, deploy, test)
export REGISTRY=your-registry
export IMAGE_TAG=v1.0.2
./scripts/k8s-deploy.sh

# Or individual phases:
./scripts/k8s-deploy.sh build          # Build images only
./scripts/k8s-deploy.sh build push     # Build and push
```

### Manual Sync

```bash
# If auto-sync is disabled
argocd app sync vh2-sovereign-validator

# With specific manifest
kubectl apply -f k8s/
```

---

## 🔄 ArgoCD Features

### Auto-Sync (Recommended)

The ArgoCD Application manifest includes:

```yaml
syncPolicy:
  automated:
    prune: true      # Delete resources not in Git
    selfHeal: true   # Sync if cluster differs from Git
  syncOptions:
  - CreateNamespace=true
  - PruneLast=true
```

This means:
- Every commit to main → automatic sync
- Cluster drift → automatic correction
- Deletion in Git → resource pruned from cluster

### Manual Approval

To require approval before sync:

```yaml
syncPolicy:
  automated: null  # Disable auto-sync
  manual: true
```

Then approve sync:
```bash
argocd app sync vh2-sovereign-validator --prune
```

### Rollback

```bash
# Get revision history
argocd app history vh2-sovereign-validator

# Rollback to previous revision
argocd app rollback vh2-sovereign-validator 1

# Rollback to specific commit
argocd app sync vh2-sovereign-validator --revision abc123def456
```

---

## 📊 Monitoring & Observability

### ArgoCD Dashboard

```bash
# Port-forward to ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Open browser to https://localhost:8080
# Login with admin / <argocd-initial-password>
```

### Application Status

```bash
# Real-time watch
argocd app watch vh2-sovereign-validator

# JSON output (for parsing)
argocd app get vh2-sovereign-validator -o json

# Live sync status
argocd app wait vh2-sovereign-validator --sync
```

### Kubernetes Metrics

```bash
# Pod resource usage
kubectl top pods -n vh2-prod

# Deployment status
kubectl get deployment -n vh2-prod -o wide

# HPA status (autoscaling)
kubectl get hpa -n vh2-prod

# Events
kubectl get events -n vh2-prod --sort-by='.lastTimestamp'
```

### Logs

```bash
# Backend logs
kubectl logs -f -n vh2-prod deployment/vh2-backend

# Frontend logs
kubectl logs -f -n vh2-prod deployment/vh2-frontend

# Init container (test gating)
kubectl logs -n vh2-prod -l app=vh2-validator,component=backend -c test-validator

# Smoke test logs
kubectl logs -f -n vh2-prod job/vh2-smoke-tests
```

---

## 🛡️ Security Best Practices

### 1. RBAC

ArgoCD service accounts have minimal permissions:

```yaml
serviceAccountName: vh2-backend
```

Permissions defined in RBAC manifests:

```bash
kubectl get rolebinding -n vh2-prod
kubectl get roles -n vh2-prod
```

### 2. Network Policies

Zero-trust networking by default:

```bash
# Check policies
kubectl get networkpolicy -n vh2-prod

# All ingress/egress explicitly defined
kubectl describe networkpolicy vh2-network-policy -n vh2-prod
```

### 3. Pod Security

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1001
    readOnlyRootFilesystem: true
    allowPrivilegeEscalation: false
```

### 4. Image Scanning

```bash
# Use Trivy to scan images
trivy image your-registry/vh2-backend:v1.0.1
trivy image your-registry/vh2-frontend:v1.0.1
```

### 5. Secrets Management

For database credentials, API keys, etc.:

```bash
# Create secret
kubectl create secret generic vh2-secrets \
  --from-literal=api_key=xxx \
  -n vh2-prod

# Reference in deployment
env:
- name: API_KEY
  valueFrom:
    secretKeyRef:
      name: vh2-secrets
      key: api_key
```

---

## 🧪 Testing & Validation

### Smoke Tests (Automatic)

The ArgoCD Application includes a Job that runs after deployment:

```bash
# Check smoke test status
kubectl get job -n vh2-prod

# View results
kubectl logs -f job/vh2-smoke-tests -n vh2-prod
```

### Unit Tests (Init Container)

Backend deployment includes init container that runs tests before pod starts:

```bash
# View test logs
kubectl logs -n vh2-prod -l app=vh2-validator,component=backend -c test-validator

# If tests fail, pod won't start (fail-closed)
kubectl describe pod <backend-pod> -n vh2-prod | grep -A 10 "Init Containers"
```

### Manual Testing

```bash
# Get service endpoint
kubectl get svc -n vh2-prod

# Test backend health
curl http://<backend-svc>:3001/health

# Test validation endpoint
curl -X POST http://<backend-svc>:3001/api/validate \
  -H "Content-Type: application/json" \
  -d '{"spoke_count":5,"rim_diameter_in":19,"front_et_mm":29,"rear_et_mm":22,"kpi_deg":12.5,"scrub_radius_mm":45,"c5_sector_deg":72}'

# Test frontend
curl http://<frontend-svc>:3000/tests.html
```

---

## 🔧 Troubleshooting

### Application not syncing

```bash
# Check application status
argocd app get vh2-sovereign-validator

# View sync errors
argocd app get vh2-sovereign-validator --refresh

# Check ArgoCD server logs
kubectl logs -f -n argocd deployment/argocd-server

# Manual sync with verbose output
argocd app sync vh2-sovereign-validator --v=debug
```

### Pods not starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n vh2-prod

# Check init container logs
kubectl logs -n vh2-prod -l app=vh2-validator,component=backend -c test-validator

# Check resource requests
kubectl describe nodes | grep -A 5 "Allocated resources"

# Increase resource limits if needed
kubectl edit deployment vh2-backend -n vh2-prod
```

### Init container tests failing

```bash
# View test output
kubectl logs <backend-pod> -n vh2-prod -c test-validator

# Run tests manually
kubectl exec -it <backend-pod> -n vh2-prod -- npm test

# Check spec configuration
kubectl get cm vh2-sovereign-spec -n vh2-prod -o jsonpath='{.data.spec\.json}' | jq .
```

### Ingress not working

```bash
# Check ingress status
kubectl get ingress -n vh2-prod

# Check ingress class
kubectl get ingressclass

# Check ingress events
kubectl describe ingress vh2-ingress -n vh2-prod

# Test backend directly (bypass ingress)
kubectl port-forward svc/vh2-backend 3001:3001 -n vh2-prod
```

---

## 📈 Scaling & Performance

### Manual Scaling

```bash
# Scale backend to 10 replicas
kubectl scale deployment vh2-backend --replicas=10 -n vh2-prod

# View HPA status
kubectl get hpa -n vh2-prod
```

### Autoscaling Configuration

HPA automatically scales based on:
- CPU: 70% threshold (backend), 60% (frontend)
- Memory: 80% threshold (backend), 70% (frontend)

Check HPA metrics:

```bash
# Requires metrics-server installed
kubectl get hpa -n vh2-prod --watch

# View current metrics
kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/vh2-prod/pods | jq .
```

### Load Testing

```bash
# Using Apache Bench
ab -n 10000 -c 100 http://vh2-prod.yourdomain.com/

# Using Hey
hey -n 10000 -c 100 http://vh2-prod.yourdomain.com/

# Watch pods scale
kubectl get hpa -n vh2-prod --watch
```

---

## 🎯 Production Checklist

- [ ] Images built and pushed to registry
- [ ] ArgoCD application created and syncing
- [ ] Namespace `vh2-prod` created
- [ ] ConfigMaps with spec deployed
- [ ] Backend deployment ready (3+ replicas)
- [ ] Frontend deployment ready (2+ replicas)
- [ ] Services created (backend, frontend)
- [ ] Ingress configured with TLS
- [ ] NetworkPolicy enforcing zero-trust
- [ ] Smoke tests passing
- [ ] Init container tests passing
- [ ] HPA configured and monitoring
- [ ] Logging aggregation enabled
- [ ] Monitoring/Prometheus scraping
- [ ] Backup strategy defined
- [ ] Disaster recovery plan documented

---

## 🚀 GitOps Commands Cheat Sheet

```bash
# ArgoCD commands
argocd app list
argocd app get vh2-sovereign-validator
argocd app sync vh2-sovereign-validator
argocd app rollback vh2-sovereign-validator <revision>
argocd app delete vh2-sovereign-validator
argocd app watch vh2-sovereign-validator

# Kubernetes commands
kubectl get all -n vh2-prod
kubectl describe deployment vh2-backend -n vh2-prod
kubectl logs -f deployment/vh2-backend -n vh2-prod
kubectl exec -it deployment/vh2-backend -n vh2-prod -- sh
kubectl rollout status deployment/vh2-backend -n vh2-prod
kubectl rollout history deployment/vh2-backend -n vh2-prod

# Kustomization
kustomize build k8s/
kubectl apply -k k8s/
kubectl diff -k k8s/
```

---

## 📞 Support & Documentation

- **ArgoCD Docs**: https://argo-cd.readthedocs.io/
- **Kustomize Docs**: https://kustomize.io/
- **Kubernetes Docs**: https://kubernetes.io/docs/
- **VH2 Repository**: https://github.com/yourorg/vh2-docker

---

**Status**: Production Ready ✓

🏎️ **Sovereign physics at scale. From git commit to 1000 rps in minutes.**

Sources: https://argo-cd.readthedocs.io/ | https://kubernetes.io/docs/ | https://kustomize.io/
