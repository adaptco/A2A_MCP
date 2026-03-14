#!/bin/bash
# Deploy to Kubernetes Production Environment
# Usage: ./scripts/deploy-production.sh <image-tag>
# WARNING: This deploys to production. Use with caution!

set -e

CLUSTER_CONTEXT="production"
NAMESPACE="production"
IMAGE_TAG=${1:-latest}
REGISTRY="ghcr.io/your-org"
IMAGE_NAME="agent-runner"

echo "⚠️  PRODUCTION DEPLOYMENT"
echo "================================"
echo "Context:  $CLUSTER_CONTEXT"
echo "Image:    $REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
echo "Namespace: $NAMESPACE"
echo ""

# Confirmation prompt
read -p "Are you sure you want to deploy to PRODUCTION? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

# Verify kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed"
    exit 1
fi

# Set context
echo "📍 Setting Kubernetes context..."
kubectl config use-context $CLUSTER_CONTEXT || {
    echo "❌ Context '$CLUSTER_CONTEXT' not found"
    exit 1
}

# Verify we're in production namespace
CURRENT_NS=$(kubectl config view --minify --output 'jsonpath={..namespace}')
if [ "$CURRENT_NS" != "$NAMESPACE" ]; then
    echo "⚠️  Switching to namespace: $NAMESPACE"
    kubectl config set-context --current --namespace=$NAMESPACE
fi

# Pre-deployment checks
echo "🔍 Running pre-deployment checks..."

# Check current deployment exists
kubectl get deployment agent-runner -n $NAMESPACE > /dev/null || {
    echo "❌ Deployment 'agent-runner' not found in namespace '$NAMESPACE'"
    exit 1
}

# Get current replicas for rollback
CURRENT_REPLICAS=$(kubectl get deployment agent-runner -n $NAMESPACE -o jsonpath='{.spec.replicas}')
CURRENT_IMAGE=$(kubectl get deployment agent-runner -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}')

echo "   Current replicas: $CURRENT_REPLICAS"
echo "   Current image:    $CURRENT_IMAGE"

# Create backup of current deployment
echo "💾 Creating backup of current deployment..."
kubectl get deployment agent-runner -n $NAMESPACE -o yaml > /tmp/agent-runner-backup-$(date +%s).yaml

# Update image reference
echo "🖼️  Updating deployment image..."
kubectl set image deployment/agent-runner \
    agent-runner=$REGISTRY/$IMAGE_NAME:$IMAGE_TAG \
    -n $NAMESPACE

# Monitor rollout
echo "⏳ Monitoring rollout (timeout: 15 minutes)..."
if kubectl rollout status deployment/agent-runner -n $NAMESPACE --timeout=15m; then
    echo "✅ Rollout completed successfully!"
else
    echo "❌ Rollout failed or timed out"
    echo "🔄 Rolling back to previous version..."
    kubectl rollout undo deployment/agent-runner -n $NAMESPACE
    kubectl rollout status deployment/agent-runner -n $NAMESPACE --timeout=5m
    exit 1
fi

# Post-deployment verification
echo ""
echo "🔍 Verifying deployment..."
echo ""
echo "Pods status:"
kubectl get pods -n $NAMESPACE -l app=agent-runner -o wide
echo ""
echo "Service status:"
kubectl get service agent-runner -n $NAMESPACE -o wide
echo ""
echo "Recent logs:"
POD=$(kubectl get pod -n $NAMESPACE -l app=agent-runner -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n $NAMESPACE $POD --tail=20

# Health check
echo ""
echo "🏥 Running health checks..."
sleep 5
kubectl exec -n $NAMESPACE $POD -- curl -s http://localhost:3000/health || {
    echo "⚠️  Health check failed. Review logs above."
    exit 1
}

echo ""
echo "✅ Production deployment successful!"
echo ""
echo "📊 Deployment Summary:"
echo "   • Image deployed: $REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
echo "   • Namespace: $NAMESPACE"
echo "   • Replicas: $CURRENT_REPLICAS"
echo "   • Timestamp: $(date)"
echo ""
echo "💡 Next steps:"
echo "   • Monitor logs: kubectl logs -f -n $NAMESPACE deployment/agent-runner"
echo "   • Check metrics: kubectl top pods -n $NAMESPACE"
echo "   • Rollback if needed: kubectl rollout undo deployment/agent-runner -n $NAMESPACE"
echo ""
echo "📝 Backup location: /tmp/agent-runner-backup-*.yaml"
