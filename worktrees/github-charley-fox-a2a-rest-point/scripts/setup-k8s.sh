#!/bin/bash
# Setup Kubernetes cluster for Agent Runner deployment
# Usage: ./scripts/setup-k8s.sh

set -e

echo "🚀 Setting up Kubernetes cluster..."

# Verify kubectl
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed"
    exit 1
fi

# Create namespaces
echo "📍 Creating namespaces..."
kubectl create namespace staging --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace production --dry-run=client -o yaml | kubectl apply -f -

# Create image pull secret for private registry
echo "🔐 Setting up image pull secrets..."
read -p "Enter GitHub Container Registry username: " GH_USERNAME
read -sp "Enter GitHub Personal Access Token (PAT): " GH_TOKEN
echo ""

for NAMESPACE in staging production; do
    kubectl create secret docker-registry ghcr-secret \
        --docker-server=ghcr.io \
        --docker-username=$GH_USERNAME \
        --docker-password=$GH_TOKEN \
        --docker-email=noreply@github.com \
        -n $NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    echo "   ✅ Created image pull secret in $NAMESPACE"
done

# Create database secrets
echo "🔑 Creating database secrets..."
for NAMESPACE in staging production; do
    read -sp "Enter database URL for $NAMESPACE (DATABASE_URL): " DB_URL
    echo ""
    read -sp "Enter Redis URL for $NAMESPACE (REDIS_URL): " REDIS_URL
    echo ""
    read -sp "Enter JWT secret for $NAMESPACE (JWT_SECRET): " JWT_SECRET
    echo ""
    
    kubectl create secret generic agent-runner-secrets \
        --from-literal=DATABASE_URL="$DB_URL" \
        --from-literal=REDIS_URL="$REDIS_URL" \
        --from-literal=JWT_SECRET="$JWT_SECRET" \
        -n $NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    echo "   ✅ Created secrets in $NAMESPACE"
done

# Apply network policies (optional, requires CNI that supports NetworkPolicy)
echo "🔒 Applying network policies..."
cat << 'EOF' | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
  namespace: staging
spec:
  podSelector: {}
  policyTypes:
  - Ingress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-agent-runner-ingress
  namespace: staging
spec:
  podSelector:
    matchLabels:
      app: agent-runner
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 3000
EOF

echo "✅ Network policies applied"

# Setup RBAC (already included in deployment.yaml)
echo "✅ RBAC rules configured in deployment manifests"

# Create resource quotas
echo "📊 Creating resource quotas..."
kubectl apply -f - << 'EOF'
apiVersion: v1
kind: ResourceQuota
metadata:
  name: staging-quota
  namespace: staging
spec:
  hard:
    requests.cpu: "10"
    requests.memory: "20Gi"
    limits.cpu: "20"
    limits.memory: "40Gi"
    pods: "50"
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: production-quota
  namespace: production
spec:
  hard:
    requests.cpu: "20"
    requests.memory: "40Gi"
    limits.cpu: "40"
    limits.memory: "80Gi"
    pods: "100"
EOF

echo "✅ Resource quotas created"

# Setup monitoring (optional)
echo ""
echo "📊 Checking for Prometheus ServiceMonitor support..."
if kubectl api-resources | grep -q servicemonitor; then
    echo "✅ ServiceMonitor CRD found. Monitoring is available."
else
    echo "⚠️  ServiceMonitor not found. Install Prometheus operator to enable metrics collection."
fi

echo ""
echo "✅ Kubernetes cluster setup complete!"
echo ""
echo "📋 Created resources:"
echo "   • Namespaces: staging, production"
echo "   • Image pull secrets: ghcr-secret"
echo "   • Database secrets: agent-runner-secrets"
echo "   • Network policies: deny-all-ingress, allow-agent-runner-ingress"
echo "   • Resource quotas: staging-quota, production-quota"
echo ""
echo "🚀 Ready to deploy! Use:"
echo "   ./scripts/deploy-staging.sh <image-tag>"
echo "   ./scripts/deploy-production.sh <image-tag>"
