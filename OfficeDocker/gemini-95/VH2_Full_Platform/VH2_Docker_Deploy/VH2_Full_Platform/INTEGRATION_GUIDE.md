# VH2 Deployment Integration Guide

> Step-by-step instructions for merging VH2 Sovereign Validator with existing projects

---

## 📋 Pre-Integration Checklist

- [ ] VH2 Docker files extracted and verified
- [ ] Existing project structure documented
- [ ] Git repository ready for merge
- [ ] Docker registry configured
- [ ] Kubernetes cluster access confirmed
- [ ] ArgoCD installation planned

---

## 🔀 Step 1: Merge Project Structure

### Option A: Keep VH2 in Separate Directory (Recommended)

```bash
# If you have existing Docker files, move them to a separate folder
mkdir -p deploy/legacy
mv Dockerfile docker-compose.yml deploy/legacy/

# Keep vh2-docker/ at root level (already done)
ls -la
# vh2-docker/                  ← New production-ready stack
# deploy/legacy/               ← Your existing Docker configs (if any)
# wham_engine/                 ← Your existing code
# agents/                      ← Your existing agents
```

### Option B: Merge into Existing Docker Directory

```bash
# If you have a single docker/ directory, merge like this:
cp -r vh2-docker/* docker/
# This combines VH2 manifests with your existing configs
```

### Recommended Structure for Large Projects

```
your_project/
├── README.md                 ← Start here
├── Makefile                  ← Make commands (already created)
├── vh2-docker/              ← Production stack (29 files)
│   ├── backend/
│   ├── frontend/
│   ├── k8s/
│   ├── argocd/
│   └── scripts/
├── wham_engine/             ← Your existing engine code
│   ├── engine.py
│   ├── tests/
│   └── Dockerfile           ← (if you have one)
├── agents/                  ← Your existing agents
├── docs/                    ← Documentation
└── deploy/
    ├── integration/         ← Integration configs
    └── scripts/             ← Custom deployment scripts
```

---

## 🔗 Step 2: Integration Points

### 2.1 Backend API Integration

If you have custom validation logic, wire it into `vh2-docker/backend/server.js`:

**Before:**
```javascript
// server.js - Basic API
app.post('/validate', (req, res) => {
    res.json({ status: 'SOVEREIGN_PASS' });
});
```

**After (with engine integration):**
```javascript
// Require your validation engine
const { validateSpec } = require('../wham_engine/engine');

app.post('/validate', async (req, res) => {
    try {
        // Call your engine
        const result = await validateSpec(req.body);
        res.json({
            status: result.valid ? 'SOVEREIGN_PASS' : 'SOVEREIGN_FAIL',
            violations: result.violations || [],
            timestamp: new Date().toISOString()
        });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});
```

### 2.2 Docker Compose with External Services

Extend `vh2-docker/docker-compose.yml` to include your engine:

**Original:**
```yaml
services:
  backend:
    build: ./vh2-docker/backend
    ports: ['3001:3001']
  frontend:
    build: ./vh2-docker/frontend
    ports: ['3000:3000']
```

**Enhanced (with your engine):**
```yaml
services:
  backend:
    build: ./vh2-docker/backend
    ports: ['3001:3001']
    volumes:
      - ./wham_engine:/app/wham_engine  # Mount your engine
    environment:
      - ENGINE_PATH=/app/wham_engine
      - NODE_ENV=development

  frontend:
    build: ./vh2-docker/frontend
    ports: ['3000:3000']
    depends_on:
      - backend

  wham_engine:  # Optional: if containerized separately
    build: ./wham_engine
    ports: ['5000:5000']
    volumes:
      - ./wham_engine:/app

  nginx:
    build: ./vh2-docker/nginx
    ports: ['80:80']
    depends_on:
      - backend
      - frontend
```

### 2.3 Update Dockerfile to Include Your Code

Edit `vh2-docker/backend/Dockerfile`:

**Before:**
```dockerfile
# Copy source (tests excluded)
COPY server.js ./
```

**After:**
```dockerfile
# Copy application files
COPY server.js ./
COPY ../wham_engine ./wham_engine

# OR mount at runtime (see docker-compose above)
```

### 2.4 Update Tests to Validate Integration

Edit `vh2-docker/backend/tests/validator.test.js`:

```javascript
// Add tests for your engine integration
describe('Engine Integration', () => {
    test('Backend calls engine /validate endpoint', async () => {
        const response = await request(app)
            .post('/validate')
            .send({ vehicle: 'vh2', wheels: { front_et: 29 } });
        
        expect(response.status).toBe(200);
        expect(response.body.status).toMatch(/SOVEREIGN_(PASS|FAIL)/);
    });

    test('Engine returns violations on invalid spec', async () => {
        const response = await request(app)
            .post('/validate')
            .send({ vehicle: 'invalid' });
        
        expect(response.body.status).toBe('SOVEREIGN_FAIL');
        expect(response.body.violations.length).toBeGreaterThan(0);
    });
});
```

---

## 3: Kubernetes Integration

### 3.1 Update K8s ConfigMap with Your Specs

Edit `vh2-docker/k8s/configmap-spec.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vh2-spec
  namespace: vh2-prod
data:
  spec.json: |
    {
      "vehicle": "vh2",
      "physics": {
        "et29_22": true,
        "material": "A6061-T6"
      },
      "agents": [
        "OrchestrationAgent",
        "ArchitectureAgent"
      ],
      "wham_engine": {
        "version": "1.0.0",
        "features": ["validation", "simulation", "optimization"]
      }
    }
```

### 3.2 Mount ConfigMap in Backend Deployment

Edit `vh2-docker/k8s/backend-deployment.yaml`:

```yaml
spec:
  containers:
  - name: backend
    volumeMounts:
    - name: spec-volume
      mountPath: /app/spec
      readOnly: true
  volumes:
  - name: spec-volume
    configMap:
      name: vh2-spec
```

### 3.3 Add Custom Init Containers

If you need to initialize data before the backend starts:

```yaml
initContainers:
- name: init-engine
  image: your-engine:latest
  command: ['sh', '-c', 'cp -r /engine /app/engine-data']
  volumeMounts:
  - name: engine-data
    mountPath: /app/engine-data

containers:
- name: backend
  image: vh2-backend:1.0.0
  volumeMounts:
  - name: engine-data
    mountPath: /app/engine-data
    readOnly: true

volumes:
- name: engine-data
  emptyDir: {}
```

---

## 4: GitOps / ArgoCD Integration

### 4.1 Update ArgoCD Application Manifest

Edit `vh2-docker/argocd/vh2-validator-app.yaml`:

```yaml
spec:
  source:
    repoURL: https://github.com/YOUR_ORG/vh2-sovereign-validator.git
    targetRevision: main
    path: vh2-docker/k8s  # Path to K8s manifests
    plugin:
      name: kustomize

  # Add your custom values
  project: default
  
  # Include your engine deployment if separate
  # (You can use Kustomize overlays)
```

### 4.2 Create Kustomize Overlays (Optional)

```bash
mkdir -p vh2-docker/k8s/overlays/prod
cat > vh2-docker/k8s/overlays/prod/kustomization.yaml << EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../

patches:
  - path: replicas-patch.yaml
    target:
      group: apps
      version: v1
      kind: Deployment
      name: vh2-backend
EOF
```

---

## 5: Environment-Specific Configs

### 5.1 Create Environment Overrides

```bash
# Development
cat > vh2-docker/docker-compose.dev.yml << EOF
version: '3'
services:
  backend:
    environment:
      - NODE_ENV=development
      - DEBUG=vh2:*
      - LOG_LEVEL=debug
    volumes:
      - ./vh2-docker/backend:/app
EOF

# Staging
cat > vh2-docker/docker-compose.staging.yml << EOF
version: '3'
services:
  backend:
    environment:
      - NODE_ENV=staging
      - LOG_LEVEL=info
EOF

# Production (already exists as docker-compose.prod.yml)
```

### 5.2 Use Environment-Specific Compose Files

```bash
# Development with hot reload
docker-compose -f vh2-docker/docker-compose.yml \
               -f vh2-docker/docker-compose.dev.yml up

# Staging with resource limits
docker-compose -f vh2-docker/docker-compose.yml \
               -f vh2-docker/docker-compose.staging.yml up

# Production
docker-compose -f vh2-docker/docker-compose.yml \
               -f vh2-docker/docker-compose.prod.yml up
```

---

## 6: Validation & Testing

### 6.1 Validate All Integration Points

```bash
# 1. Validate YAML
make lint

# 2. Run unit tests
make test

# 3. Run integration tests
make test-integration

# 4. Build images
make build-images

# 5. Deploy locally and validate
make dev

# 6. Run smoke tests against K8s
make deploy-k8s
make test-smoke
```

### 6.2 Test Integration with Your Engine

```bash
# Start stack with your engine
docker-compose -f vh2-docker/docker-compose.yml up -d

# Test the integration
curl -X POST http://localhost:3001/validate \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle": "vh2",
    "wheels": {"front_et": 29, "rear_et": 22},
    "engine_version": "1.0.0"
  }'

# Expected response:
# {
#   "status": "SOVEREIGN_PASS",
#   "violations": [],
#   "engine_result": { ... }
# }
```

---

## 7: Deployment to Production

### 7.1 Build & Push Images

```bash
make build-images REGISTRY=your-registry.com TAG=1.0.0
make build-push REGISTRY=your-registry.com TAG=1.0.0
```

### 7.2 Update Image References

```bash
# Edit kustomization.yaml with your registry
cat > vh2-docker/k8s/kustomization.yaml << EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: vh2-prod

images:
  - name: vh2-backend
    newName: your-registry.com/vh2-backend
    newTag: "1.0.0"
  - name: vh2-frontend
    newName: your-registry.com/vh2-frontend
    newTag: "1.0.0"
EOF
```

### 7.3 Deploy to K8s

```bash
# Using Makefile
make deploy-k8s

# OR manual kubectl
kubectl apply -k vh2-docker/k8s/
```

### 7.4 Deploy via ArgoCD

```bash
# Install ArgoCD (if not already installed)
make argocd-install

# Deploy VH2 app
make deploy-argocd REPO_URL=https://github.com/YOUR_ORG/repo.git

# Monitor sync
make argocd-status
```

---

## 8: Rollback & Troubleshooting

### 8.1 Rollback Failed Deployment

```bash
# Using Makefile
make deploy-rollback

# OR using kubectl
kubectl rollout undo deployment/vh2-backend -n vh2-prod
kubectl rollout undo deployment/vh2-frontend -n vh2-prod

# OR using ArgoCD
make argocd-rollback
```

### 8.2 Check Deployment Status

```bash
# Get all resources
make deploy-status

# Get specific logs
make deploy-logs              # Backend logs
make deploy-logs-frontend    # Frontend logs

# Get pod events
kubectl describe pod <pod-name> -n vh2-prod
```

---

## 9: Continuous Integration/Deployment

### 9.1 GitHub Actions (Optional)

```yaml
name: Deploy VH2

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: make test
      - run: make lint

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: make build-images REGISTRY=gcr.io/${{ secrets.GCP_PROJECT }} TAG=${{ github.sha }}
      - run: make build-push REGISTRY=gcr.io/${{ secrets.GCP_PROJECT }} TAG=${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: make deploy-k8s
      - run: make test-smoke
```

---

## 10: Final Checklist

- [ ] Project structure merged and organized
- [ ] Backend API integrated with your engine
- [ ] Docker Compose extended with your services
- [ ] Tests updated to validate integration
- [ ] K8s ConfigMaps updated with your specs
- [ ] ArgoCD manifest configured
- [ ] Environment-specific configs created
- [ ] All YAML files validated (make lint)
- [ ] Local stack tested (make dev)
- [ ] Images built and tested (make build-images)
- [ ] K8s deployment tested (make deploy-k8s)
- [ ] ArgoCD deployment tested (make deploy-argocd)
- [ ] Rollback procedures documented
- [ ] Team briefed on deployment process
- [ ] Monitoring/alerting configured

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| Start locally | `make dev` |
| Run tests | `make test` |
| Build images | `make build-images` |
| Deploy to K8s | `make deploy-k8s` |
| Deploy via ArgoCD | `make deploy-argocd` |
| Check status | `make deploy-status` |
| View logs | `make deploy-logs` |
| Rollback | `make deploy-rollback` |
| Clean up | `make clean` |
| Show all commands | `make help` |

---

**Last Updated:** 2025-02-22  
**Status:** Integration Guide Complete ✓
