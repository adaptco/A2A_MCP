# VH2 Production Deployment — Domain Configuration & Advanced Setup

> Complete guide for production deployment including DNS, TLS, Redis integration, and canary deployments

---

## 🌐 Domain Configuration

### Option 1: Production Domain (Recommended)

```bash
# Create DNS A record pointing to your Ingress IP
# Example: vh2.yourdomain.com -> 35.xxx.xxx.xxx

# Get Ingress IP (after initial deployment)
kubectl get ingress -n vh2-prod

# NAME      CLASS   HOSTS                 ADDRESS         PORTS     AGE
# vh2-prod  nginx   vh2.yourdomain.com   35.192.14.20   80, 443   2m
```

### Option 2: Demo Domain (nip.io - No DNS Setup)

```bash
# For development/testing without DNS setup
# nip.io provides wildcard DNS: 35.192.14.20.nip.io resolves to 35.192.14.20

# Update Ingress manifest:
# vh2-docker/k8s/ingress.yaml

host: "vh2-prod.35.192.14.20.nip.io"  # Replace with your IP

# Deploy:
make deploy-k8s

# Access at: https://vh2-prod.35.192.14.20.nip.io
```

### Option 3: Internal K8s DNS (Cluster Only)

```bash
# For internal testing only (no external access)

# Access via Service name:
kubectl port-forward svc/vh2-backend 3001:3001 -n vh2-prod

# Backend available at: http://localhost:3001
```

---

## 🔐 TLS Certificate Configuration

### Automatic TLS via cert-manager (Recommended)

```bash
# 1. Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml

# 2. Create ClusterIssuer for Let's Encrypt
cat > letsencrypt-issuer.yaml << 'EOF'
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@yourdomain.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

kubectl apply -f letsencrypt-issuer.yaml

# 3. Update Ingress to use cert-manager
cat >> vh2-docker/k8s/ingress.yaml << 'EOF'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: vh2-ingress
  namespace: vh2-prod
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - vh2.yourdomain.com
    secretName: vh2-tls-cert
  rules:
  - host: vh2.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: vh2-frontend
            port:
              number: 3000
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: vh2-backend
            port:
              number: 3001
EOF

kubectl apply -f vh2-docker/k8s/ingress.yaml
```

### Manual TLS with Self-Signed Certificate

```bash
# Create self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout tls.key -out tls.crt -days 365 -nodes \
  -subj "/CN=vh2.yourdomain.com"

# Create secret
kubectl create secret tls vh2-tls \
  --cert=tls.crt \
  --key=tls.key \
  -n vh2-prod
```

---

## 💾 Redis Agent State Persistence

### Deploy Redis StatefulSet

```bash
# Deploy Redis (already configured in k8s/redis-statefulset.yaml)
kubectl apply -f vh2-docker/k8s/redis-statefulset.yaml

# Verify Redis is running
kubectl get statefulset redis -n vh2-prod
kubectl logs -n vh2-prod -l app=redis

# Test Redis connectivity
kubectl exec -it redis-0 -n vh2-prod -- redis-cli ping
# Should return: PONG
```

### Persist Agent State

Update backend to use Redis:

```python
# backend/server.js (Node.js example)
const redis = require('redis');

const redisClient = redis.createClient({
  host: process.env.REDIS_HOST || 'redis.vh2-prod.svc.cluster.local',
  port: process.env.REDIS_PORT || 6379
});

// Store agent state
app.post('/agent/state', async (req, res) => {
  const agentId = req.body.agent_id;
  const state = req.body.state;
  
  await redisClient.setex(
    `agent:${agentId}`,
    3600,  // 1 hour TTL
    JSON.stringify(state)
  );
  
  res.json({ stored: true });
});

// Retrieve agent state
app.get('/agent/state/:agentId', async (req, res) => {
  const state = await redisClient.get(`agent:${req.params.agentId}`);
  res.json(state ? JSON.parse(state) : {});
});
```

---

## 🚀 Canary Deployment with Argo Rollouts

### Install Argo Rollouts

```bash
# Install Argo Rollouts controller
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/download/v1.5.1/install.yaml

# Verify installation
kubectl get deployment -n argo-rollouts

# Install Rollouts dashboard (optional)
kubectl apply -f https://github.com/argoproj/argo-rollouts/releases/download/v1.5.1/dashboard-install.yaml
```

### Deploy Canary Rollout

```bash
# Deploy canary rollout (already configured in k8s/canary-rollout.yaml)
kubectl apply -f vh2-docker/k8s/canary-rollout.yaml

# Watch canary progress
kubectl argo rollouts get rollout vh2-backend-canary -n vh2-prod --watch

# Promote canary to stable (when ready for full rollout)
kubectl argo rollouts promote vh2-backend-canary -n vh2-prod
```

### Canary Rollout Workflow

```
Step 1: Route 5% traffic (2 min)
   ├─ Canary pod gets 5% of requests
   ├─ Stable pod gets 95% of requests
   └─ Monitor success/error rates

Step 2: Increase to 10% (3 min)
   ├─ Canary pod gets 10% of requests
   └─ Continue monitoring

Step 3: Increase to 25% (5 min)
   └─ More traffic to canary

Step 4: Manual Approval (50%)
   └─ Wait for operator to review metrics

Step 5: Increase to 75% (5 min)
   └─ Most traffic goes to canary

Step 6: Full Rollout (100%)
   └─ Canary becomes the new stable
```

### Monitor Canary Metrics

```bash
# View rollout status
kubectl describe rollout vh2-backend-canary -n vh2-prod

# Check analysis template
kubectl get analysistemplate -n vh2-prod
kubectl describe analysistemplate vh2-backend-analysis -n vh2-prod

# View Prometheus metrics
# Success rate (should be >95%)
# Error rate (should be <5%)
# Latency p95 (should be <1s)
```

---

## 📊 Horizontal Pod Autoscaler (HPA)

### HPA Behavior

```
CPU Utilization Check (every 15 seconds)
  ├─ If > 70% → Scale UP
  │  └─ Add 1-2 pods (max scale-up: 100% per 30s)
  └─ If < 50% → Scale DOWN
     └─ Remove pods (max scale-down: 50% per 60s)

Memory Utilization Check
  ├─ If > 80% → Scale UP
  └─ If < 60% → Scale DOWN

Custom Metrics (requests/sec)
  ├─ Target: 1000 requests/pod
  └─ Scale accordingly
```

### Manual HPA Testing

```bash
# View HPA status
kubectl get hpa -n vh2-prod

# Get detailed HPA info
kubectl describe hpa vh2-backend-hpa -n vh2-prod

# Watch HPA decisions
kubectl get hpa -n vh2-prod --watch

# Generate load to test scaling
kubectl run -it load-gen --image=busybox /bin/sh
# Inside pod:
while sleep 0.01; do wget -q -O- http://vh2-backend:3001/validate; done
```

---

## 🔍 Monitoring & Observability

### Prometheus Metrics

```bash
# Prometheus queries for VH2 metrics

# Request rate
rate(http_requests_total{job="vh2-backend"}[5m])

# Error rate
sum(rate(http_requests_total{job="vh2-backend",status=~"5.."}[5m])) / sum(rate(http_requests_total{job="vh2-backend"}[5m]))

# Latency p95
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="vh2-backend"}[5m])) by (le))

# Pod count
count(kube_pod_labels{label_app="vh2-backend",namespace="vh2-prod"})
```

### Grafana Dashboard Setup

```bash
# Create ConfigMap with dashboard JSON
kubectl create configmap vh2-dashboard \
  --from-file=dashboard.json \
  -n vh2-prod

# Port-forward to Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Access at: http://localhost:3000
```

---

## 🔐 Production Hardening

### Network Policies

```yaml
# Ingress only from Ingress Controller
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vh2-backend-ingress
  namespace: vh2-prod
spec:
  podSelector:
    matchLabels:
      app: vh2-backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 3001
```

### Pod Security Policy

```yaml
# Enforce non-root, read-only filesystem
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: vh2-restricted
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
  - ALL
  volumes:
  - 'configMap'
  - 'emptyDir'
  - 'projected'
  - 'secret'
  - 'downwardAPI'
  - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  runAsGroup:
    rule: 'MustRunAs'
    ranges:
    - min: 1000
      max: 2000
  readOnlyRootFilesystem: true
```

---

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] Domain/DNS configured
- [ ] TLS certificates ready (automatic or manual)
- [ ] Redis StatefulSet deployed
- [ ] Argo Rollouts controller installed
- [ ] Prometheus/Grafana running (optional)

### Initial Deployment
- [ ] `make deploy-k8s` successful
- [ ] All pods running in vh2-prod namespace
- [ ] Ingress with valid IP address
- [ ] TLS certificate issued

### Canary Deployment
- [ ] Canary rollout created
- [ ] 5% traffic to canary pod
- [ ] Success/error metrics normal
- [ ] Manual promotion when ready
- [ ] 100% traffic to new version

### Verification
- [ ] `kubectl get pods -n vh2-prod` all Running
- [ ] `kubectl get hpa -n vh2-prod` scaling active
- [ ] `kubectl logs -n vh2-prod redis-0` no errors
- [ ] Ingress accessible via domain/nip.io
- [ ] `/health` endpoint responds 200
- [ ] `/validate` endpoint works

---

## 🚀 Complete Deployment Flow

```bash
# 1. Configure domain/DNS
# (Create DNS A record or use nip.io)

# 2. Deploy Redis
kubectl apply -f vh2-docker/k8s/redis-statefulset.yaml

# 3. Install Argo Rollouts
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/download/v1.5.1/install.yaml

# 4. Deploy full stack
make deploy-k8s

# 5. Watch Ingress get IP
kubectl get ingress -n vh2-prod --watch

# 6. Verify all services running
make deploy-status

# 7. Test endpoints
curl https://vh2.yourdomain.com/health
curl -X POST https://vh2.yourdomain.com/api/validate -d '...'

# 8. Monitor scaling
kubectl get hpa -n vh2-prod --watch

# 9. Deploy canary when ready
kubectl apply -f vh2-docker/k8s/canary-rollout.yaml

# 10. Watch canary progress
kubectl argo rollouts get rollout vh2-backend-canary -n vh2-prod --watch
```

---

## ✅ Success Indicators

✓ Domain resolves to Ingress IP  
✓ TLS certificate valid (HTTPS works)  
✓ Redis pod healthy with persistent volume  
✓ HPA auto-scaling working (watch during load test)  
✓ Canary deployment shows traffic shifting (5% → 10% → 25% → 50% → 75% → 100%)  
✓ All Prometheus metrics collected  
✓ Grafana dashboard displays live data  

---

**Production Deployment Status:** ✅ Ready for Enterprise Scale
