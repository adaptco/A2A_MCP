# VH2 Sovereign Validator — Command Reference Card

> Quick reference for all deployment and testing commands

---

## 🚀 Getting Started (5 minutes)

```bash
# 1. Test locally
make dev
# Services: backend:3001, frontend:3000, nginx:80

# 2. Test API
curl -X POST http://localhost:3001/validate \
  -H "Content-Type: application/json" \
  -d '{"vehicle":"vh2","wheels":{"front_et":29,"rear_et":22}}'

# 3. Stop services
make dev-stop
```

---

## 🧪 Testing & Validation

```bash
# Run all 42+ tests
make test

# Run integration tests (with docker-compose)
make test-integration

# Run smoke tests against K8s
make test-smoke

# Validate YAML manifests
make lint
```

---

## 🐳 Docker Operations

```bash
# Build images (set REGISTRY variable)
make build-images REGISTRY=gcr.io/my-project TAG=1.0.0

# Build and push to registry
make build-push REGISTRY=gcr.io/my-project TAG=1.0.0

# View local images
docker images | grep vh2

# Clean up images and containers
make clean
```

---

## ☸️ Kubernetes Deployment

```bash
# Deploy to K8s cluster
make deploy-k8s

# Check deployment status
make deploy-status

# View pod details
kubectl get pods -n vh2-prod -o wide

# View deployment history
kubectl rollout history deployment/vh2-backend -n vh2-prod

# Describe specific resource
kubectl describe pod <pod-name> -n vh2-prod

# Stream logs from backend
make deploy-logs

# Stream logs from frontend
make deploy-logs-frontend

# Check HPA status
kubectl get hpa -n vh2-prod --watch
```

---

## 🔄 Rollbacks & Updates

```bash
# Rollback to previous version
make deploy-rollback

# Or manually
kubectl rollout undo deployment/vh2-backend -n vh2-prod

# Check rollout status
kubectl rollout status deployment/vh2-backend -n vh2-prod

# View specific version
kubectl rollout history deployment/vh2-backend -n vh2-prod --revision=2
```

---

## 🔧 ArgoCD Operations

```bash
# Install ArgoCD (first time)
make argocd-install

# Check if ArgoCD is installed
make argocd-check

# Deploy via ArgoCD
make deploy-argocd REPO_URL="https://github.com/org/repo.git"

# Check ArgoCD status
make argocd-status

# View sync logs
make argocd-logs

# Rollback ArgoCD application
make argocd-rollback

# Manually sync
argocd app sync vh2-sovereign-validator --server <argocd-server> --auth-token <token>
```

---

## 📊 Monitoring & Debugging

```bash
# Get all resources in namespace
kubectl get all -n vh2-prod

# Watch resources update in real-time
kubectl get pods -n vh2-prod --watch

# Check events in namespace
kubectl get events -n vh2-prod --sort-by='.lastTimestamp'

# View resource usage
kubectl top pods -n vh2-prod
kubectl top nodes

# Check persistent volumes
kubectl get pvc -n vh2-prod

# Port-forward to service (access locally)
kubectl port-forward svc/vh2-backend 3001:3001 -n vh2-prod

# Execute command in pod
kubectl exec -it <pod-name> -n vh2-prod -- /bin/sh

# Copy files from pod
kubectl cp vh2-prod/<pod-name>:/app/file ./local-file
```

---

## 📝 Logging & Inspection

```bash
# Stream logs (live)
kubectl logs -n vh2-prod -l app=vh2-backend -f

# View previous pod logs (after restart)
kubectl logs -n vh2-prod <pod-name> --previous

# Get logs from init container
kubectl logs -n vh2-prod <pod-name> -c test-validator

# View all logs from deployment
kubectl logs -n vh2-prod -l app=vh2-backend --all-containers=true

# Save logs to file
kubectl logs -n vh2-prod <pod-name> > pod-logs.txt
```

---

## 🕹️ Interactive Debugging

```bash
# Open shell in running pod
kubectl exec -it <pod-name> -n vh2-prod -- /bin/sh

# Run one-off command in pod
kubectl run debug-pod --rm -i --tty --image=busybox -- sh

# Port-forward and test locally
kubectl port-forward svc/vh2-backend 3001:3001 -n vh2-prod &
curl http://localhost:3001/health
kill %1

# Check DNS resolution
kubectl run -it debug --image=busybox -- nslookup vh2-backend.vh2-prod.svc.cluster.local
```

---

## 🔐 Security & Permissions

```bash
# Check pod security context
kubectl get pods -n vh2-prod -o jsonpath='{.items[0].spec.securityContext}'

# View network policies
kubectl get networkpolicy -n vh2-prod

# Verify RBAC
kubectl describe rolebinding -n vh2-prod

# Check resource quota
kubectl describe resourcequota vh2-quota -n vh2-prod

# Test network connectivity
kubectl exec <pod1> -n vh2-prod -- wget -qO- http://vh2-backend:3001/health
```

---

## 📈 Scaling & Performance

```bash
# Manual pod scaling
kubectl scale deployment vh2-backend --replicas=5 -n vh2-prod

# Watch HPA decisions
kubectl get hpa -n vh2-prod --watch

# Load test (generate traffic)
kubectl run -it load-gen --image=busybox -- sh
# Inside pod:
for i in {1..1000}; do wget -q -O- http://vh2-backend:3001/validate & done
wait

# Check CPU/memory usage
kubectl top pods -n vh2-prod --sort-by=cpu
kubectl top pods -n vh2-prod --sort-by=memory

# View HPA detailed status
kubectl describe hpa vh2-backend-hpa -n vh2-prod
```

---

## 🚀 Canary Deployments (Argo Rollouts)

```bash
# Install Argo Rollouts (if not done)
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/download/v1.5.1/install.yaml

# Deploy canary rollout
kubectl apply -f vh2-docker/k8s/canary-rollout.yaml

# Watch canary progress
kubectl argo rollouts get rollout vh2-backend-canary -n vh2-prod --watch

# Promote canary to stable (after manual approval)
kubectl argo rollouts promote vh2-backend-canary -n vh2-prod

# Abort canary deployment
kubectl argo rollouts abort rollout vh2-backend-canary -n vh2-prod

# View rollout history
kubectl argo rollouts get rollout vh2-backend-canary -n vh2-prod --revisions
```

---

## 🔍 Troubleshooting Quick Fixes

```bash
# Pod stuck in Pending
kubectl describe pod <pod-name> -n vh2-prod
# Check: resource quota, node capacity, storage

# CrashLoopBackOff
kubectl logs -n vh2-prod <pod-name> --previous

# Failed health check
kubectl exec <pod-name> -n vh2-prod -- wget -qO- http://localhost:3001/health

# Network connectivity
kubectl exec <pod1> -n vh2-prod -- ping vh2-backend

# DNS resolution
kubectl exec <pod> -n vh2-prod -- nslookup redis.vh2-prod

# Insufficient memory
kubectl top pods -n vh2-prod --sort-by=memory
# Increase memory limit in deployment

# Storage issues
kubectl get pvc -n vh2-prod
kubectl describe pvc redis-data-redis-0 -n vh2-prod
```

---

## 📊 Makefile Shortcut Reference

```bash
make help                    # Show all available commands

# Development
make dev                     # Start local stack
make dev-stop               # Stop local stack
make dev-logs               # Tail logs
make dev-clean              # Clean everything

# Testing
make test                   # Unit tests
make test-integration       # Integration tests
make test-smoke             # K8s smoke tests

# Building
make build-images           # Build Docker images
make build-push             # Build and push

# Kubernetes
make validate-k8s           # Validate manifests
make deploy-k8s             # Deploy to K8s
make deploy-status          # Check status
make deploy-logs            # View logs
make deploy-rollback        # Rollback

# ArgoCD
make argocd-check           # Check if installed
make argocd-install         # Install ArgoCD
make deploy-argocd          # Deploy via ArgoCD
make argocd-status          # Check status

# Utilities
make lint                   # Validate YAML
make clean                  # Clean up
make info                   # Show project info
```

---

## 🔗 Common kubectl Combinations

```bash
# Health check all pods
for pod in $(kubectl get pods -n vh2-prod -o name); do
  echo "Checking $pod..."
  kubectl logs $pod -n vh2-prod | tail -5
done

# Find failing pods
kubectl get pods -n vh2-prod --field-selector=status.phase!=Running

# Monitor all changes
kubectl get all -n vh2-prod --watch

# Count resource usage
kubectl describe node | grep -A5 "Allocated resources"

# Export current state
kubectl get -o yaml all -n vh2-prod > backup.yaml

# Show resource relationships
kubectl describe deployment vh2-backend -n vh2-prod | grep -A20 "Selector"
```

---

## 🌐 Network Debugging

```bash
# List network policies
kubectl get networkpolicy -n vh2-prod

# Show policy rules
kubectl get networkpolicy -n vh2-prod -o yaml

# Test connectivity between pods
kubectl exec <pod1> -n vh2-prod -- wget -qO- http://<pod2-service>:port

# Check DNS from pod
kubectl exec <pod> -n vh2-prod -- nslookup <service>.vh2-prod

# View Ingress details
kubectl get ingress -n vh2-prod
kubectl describe ingress vh2-ingress -n vh2-prod

# Test from Ingress controller namespace
kubectl exec -n ingress-nginx <controller-pod> -- curl http://vh2-backend:3001/health
```

---

## 📋 Pre-Deployment Checklist

```bash
# Verify all prerequisites
kubectl cluster-info
kubectl get nodes
kubectl auth can-i create deployments --as=system:serviceaccount:vh2-prod:default

# Check resource availability
kubectl describe nodes | grep "Allocatable" -A4

# Verify namespaces
kubectl get namespace vh2-prod

# Check storage classes
kubectl get storageclass

# Verify DNS resolution
kubectl run -it debug --image=busybox -- nslookup kubernetes.default
```

---

## ✅ Post-Deployment Verification

```bash
# Complete status check
make deploy-status

# Detailed health check
kubectl get pods -n vh2-prod -o wide
kubectl get svc -n vh2-prod
kubectl get ingress -n vh2-prod
kubectl get hpa -n vh2-prod

# Test endpoints
curl http://<ingress-ip>/health
curl http://<ingress-ip>/api/validate

# View metrics
kubectl top pods -n vh2-prod
kubectl top nodes

# Verify security
kubectl get networkpolicy -n vh2-prod
kubectl describe psp vh2-restricted

# Check logs for errors
kubectl logs -n vh2-prod -l app=vh2-backend --tail=100
```

---

## 🛠️ Useful Aliases (Add to ~/.bashrc or ~/.zshrc)

```bash
alias k='kubectl'
alias kgp='kubectl get pods'
alias kgs='kubectl get svc'
alias kgd='kubectl get deployment'
alias kl='kubectl logs'
alias kex='kubectl exec -it'
alias kaf='kubectl apply -f'
alias kdel='kubectl delete'
alias kd='kubectl describe'

# VH2-specific
alias kvh='kubectl -n vh2-prod'
alias kvhp='kubectl get pods -n vh2-prod'
alias kvhs='kubectl get svc -n vh2-prod'
alias kvhl='kubectl logs -n vh2-prod'
```

---

## 📞 Emergency Commands

```bash
# Kill and restart a pod (delete forces recreation)
kubectl delete pod <pod-name> -n vh2-prod

# Force delete if stuck
kubectl delete pod <pod-name> -n vh2-prod --grace-period=0 --force

# Restart all pods
kubectl delete pods --all -n vh2-prod

# Clear all resources
kubectl delete all --all -n vh2-prod

# Emergency rollback
kubectl rollout undo deployment/vh2-backend -n vh2-prod

# Pause/resume deployments
kubectl rollout pause deployment/vh2-backend -n vh2-prod
kubectl rollout resume deployment/vh2-backend -n vh2-prod
```

---

**Print this card or bookmark for quick reference during deployments!** 📋

For detailed help: `make help` or see README.md
