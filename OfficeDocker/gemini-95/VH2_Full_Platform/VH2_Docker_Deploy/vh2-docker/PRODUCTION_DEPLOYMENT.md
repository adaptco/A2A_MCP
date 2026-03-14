# VH2 Sovereign Validator — Production Deployment Guide

## Overview

This guide walks you from zero to production in four concrete steps:

1. **Parameterize** — Fill in your registry, domain, GitHub org, and CORS origin
2. **Build** — Docker images → your registry
3. **Deploy** — Kubernetes manifests + ArgoCD sync
4. **Verify** — Health checks, tests, live endpoints

---

## Four Production Parameters

Before you deploy, you need to decide on four values. They're placeholders in the code right now; the `setup-production.sh` script fills them in.

### 1. Docker Registry

Where do you push Docker images? Examples:

- **GitHub Container Registry**: `ghcr.io/my-org` (free, private)
- **Docker Hub**: `docker.io/my-username`
- **GCP Artifact Registry**: `us-central1-docker.pkg.dev/my-project/vh2`
- **AWS ECR**: `123456789.dkr.ecr.us-east-1.amazonaws.com/vh2`
- **Private registry**: `registry.mycompany.com/vh2`

**What you use**: `--registry <your-registry-url>`

### 2. Domain

What hostname will this run at? Examples:

- `vh2.mycompany.com` (corporate domain)
- `validator.myapp.io` (app-specific)
- `vh2-prod.example.com` (dev/staging pattern)
- `localhost:8080` (local testing only)

This goes in:
- Ingress TLS certificate
- Backend CORS `ALLOWED_ORIGIN`
- ArgoCD Application notifications

**What you use**: `--domain <your-domain>`

### 3. GitHub Organization/User

Where will the repository live for ArgoCD to sync from? Examples:

- `github.com/alice` (personal account)
- `github.com/acme-corp` (organization)

This is used in the ArgoCD Application manifest so it can pull manifests from your repo.

**What you use**: `--github-org <your-org-or-username>`

### 4. Allowed Origin (CORS)

What origin can call the backend API? Usually your domain with `https://` prefix.

- Production: `https://vh2.mycompany.com`
- Staging: `https://vh2-staging.mycompany.com`
- Local testing: `http://localhost`

This is set as an environment variable in the backend pod.

**What you use**: `--allowed-origin <https://your-domain>`

---

## Step 1: Parameterize

Run the setup script with your four values:

```bash
cd vh2-docker

chmod +x setup-production.sh  # Make it executable (Unix/Mac)

./setup-production.sh \
  --registry ghcr.io/acme-corp \
  --domain vh2.acme.com \
  --github-org acme-corp \
  --allowed-origin https://vh2.acme.com
```

**On Windows PowerShell:**

```powershell
# Make executable
icacls setup-production.sh /grant Everyone:F

# Run
.\setup-production.sh `
  --registry ghcr.io/acme-corp `
  --domain vh2.acme.com `
  --github-org acme-corp `
  --allowed-origin https://vh2.acme.com
```

**What it does:**

- Finds all `${PLACEHOLDER}` variables in YAML files
- Replaces them with your real values
- Shows you what was patched
- Backs up originals (.bak files)

**Verify the patches:**

```bash
# Check a file to see real values now
cat k8s/ingress.yaml | grep -A 2 "host:"

# You should see your real domain, not ${VH2_DOMAIN}
```

---

## Step 2: Build & Push Images

Build Docker images locally and push to your registry:

```bash
# Build both backend and frontend
docker compose build

# Tag with your registry
docker tag vh2-backend:latest ghcr.io/acme-corp/vh2-backend:1.0.0
docker tag vh2-frontend:latest ghcr.io/acme-corp/vh2-frontend:1.0.0

# Authenticate to registry (varies by provider)
# For GitHub: gh auth login
# For Docker Hub: docker login
# For GCP: gcloud auth configure-docker

# Push
docker push ghcr.io/acme-corp/vh2-backend:1.0.0
docker push ghcr.io/acme-corp/vh2-frontend:1.0.0
```

**Verify images are there:**

```bash
docker pull ghcr.io/acme-corp/vh2-backend:1.0.0
```

---

## Step 3: Deploy to Kubernetes

### 3a. Create namespace and secrets

```bash
# Create namespace
kubectl create namespace vh2-prod

# Create the CORS secret (your domain from step 1)
kubectl create secret generic vh2-secrets \
  --from-literal=allowed-origin=https://vh2.acme.com \
  -n vh2-prod
```

### 3b. Apply Kubernetes manifests

Two options: direct apply or ArgoCD.

**Option 1: Direct apply (fastest for first deploy)**

```bash
# Apply all manifests
kustomize build k8s/ | kubectl apply -f -

# Wait for backend to be ready
kubectl rollout status deployment/vh2-backend -n vh2-prod

# Wait for frontend
kubectl rollout status deployment/vh2-frontend -n vh2-prod

# Check all pods
kubectl get pods -n vh2-prod
```

**Option 2: ArgoCD sync (better for GitOps)**

```bash
# First, push your parameterized code to your GitHub repo
git add k8s/ argocd/ helm/
git commit -m "config: parameterize production deployment"
git push origin main

# Then create the ArgoCD Application
kubectl apply -f argocd/vh2-validator-app.yaml

# Watch it sync
argocd app watch vh2-sovereign-validator

# Or check status
kubectl get application -n argocd vh2-sovereign-validator
```

---

## Step 4: Verify

### Health checks

```bash
# All pods should be Running
kubectl get pods -n vh2-prod

# Backend should be Ready
kubectl describe pod -l app=vh2-validator,component=backend -n vh2-prod | grep "Ready"

# Frontend should be Ready
kubectl describe pod -l app=vh2-validator,component=frontend -n vh2-prod | grep "Ready"
```

### Run smoke tests

```bash
# The smoke test Job runs automatically after deployment
kubectl get job -n vh2-prod
kubectl logs job/vh2-smoke-tests -n vh2-prod

# Should see:
# ✓ Backend healthy
# ✓ Frontend healthy
# ✓ API endpoints responding
# ✓ Tests page loads
```

### Access the application

If you have an ingress controller and DNS:

```bash
# Wait for ingress IP
kubectl get ingress -n vh2-prod

# Once DNS resolves:
curl https://vh2.acme.com/tests.html

# Browser:
# https://vh2.acme.com/tests.html         (unit tests)
# https://vh2.acme.com/vehicle.html       (3D simulator)
# https://vh2.acme.com/api/spec           (canonical spec)
```

If you don't have DNS yet, port-forward:

```bash
kubectl port-forward svc/vh2-frontend 3000:3000 -n vh2-prod

# Then open: http://localhost:3000
```

### Test the validator API

```bash
# Forward to backend
kubectl port-forward svc/vh2-backend 3001:3001 -n vh2-prod

# Test validation endpoint
curl -X POST http://localhost:3001/api/validate \
  -H "Content-Type: application/json" \
  -d '{"spoke_count":5,"rim_diameter_in":19,"front_et_mm":29,"rear_et_mm":22,"kpi_deg":12.5,"scrub_radius_mm":45,"c5_sector_deg":72}'

# Should respond:
# {"pass":true,"status":"SOVEREIGN_PASS",...}
```

---

## Troubleshooting

### Pod not starting

```bash
# Check why
kubectl describe pod <pod-name> -n vh2-prod

# Look for init container errors
kubectl logs <pod-name> -n vh2-prod -c test-validator

# If tests failed, see the output
```

### Ingress not working

```bash
# Check ingress status
kubectl describe ingress vh2-ingress -n vh2-prod

# Look for TLS cert issues
kubectl get certificate -n vh2-prod

# Check ingress controller is running
kubectl get pods -n ingress-nginx
```

### Backend can't reach database or external service

Check the `ALLOWED_ORIGIN` environment variable:

```bash
kubectl get pod <backend-pod> -n vh2-prod -o jsonpath='{.spec.containers[0].env[?(@.name=="ALLOWED_ORIGIN")].value}'
```

Should be your domain from step 1.

---

## After Deployment

### Monitor with ArgoCD

```bash
argocd app get vh2-sovereign-validator
argocd app watch vh2-sovereign-validator
```

### Scale if needed

```bash
# Manually scale backend to 5 replicas
kubectl scale deployment vh2-backend --replicas=5 -n vh2-prod

# Or let HPA do it (configured to scale 3-10 replicas based on CPU)
kubectl get hpa -n vh2-prod
```

### View logs

```bash
# Backend logs
kubectl logs -f deployment/vh2-backend -n vh2-prod

# Frontend logs
kubectl logs -f deployment/vh2-frontend -n vh2-prod

# Nginx logs (if using ingress)
kubectl logs -f deployment/ingress-nginx-controller -n ingress-nginx
```

### Update and redeploy

```bash
# Make code changes
git commit -am "feature: improve validator"
git push origin main

# ArgoCD syncs automatically (or manually)
argocd app sync vh2-sovereign-validator

# New pods roll out with zero downtime
```

---

## Checklist

- [ ] Four parameters decided (registry, domain, GitHub org, allowed-origin)
- [ ] `setup-production.sh` run successfully
- [ ] Files patched and verified (spot-check one YAML)
- [ ] Images built and pushed to your registry
- [ ] Kubernetes namespace created
- [ ] `vh2-secrets` secret created with your CORS origin
- [ ] Manifests applied (`kubectl apply` or ArgoCD)
- [ ] All pods running and healthy
- [ ] Smoke tests passed
- [ ] API responding (`/api/spec`, `/api/validate`)
- [ ] Frontend accessible (`/tests.html`, `/vehicle.html`)
- [ ] Ingress TLS certificate issued (or local port-forward working)

---

## Support

If something doesn't work:

1. Check pod logs: `kubectl logs <pod> -n vh2-prod`
2. Check events: `kubectl get events -n vh2-prod`
3. Describe resource: `kubectl describe pod <pod> -n vh2-prod`
4. Verify parameterization: `cat k8s/ingress.yaml | grep ${VH2_DOMAIN}` (should be empty — all replaced)

---

**Status:** Production Ready

**Time to deploy:** 15-30 minutes (first time)  
**Subsequent redeploys:** 2-5 minutes (ArgoCD auto-sync)

🏎️
