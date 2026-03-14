#!/bin/bash
# Deploy to Kubernetes Staging Environment
# Usage: ./scripts/deploy-staging.sh <image-tag>

set -e

CLUSTER_CONTEXT="staging"
NAMESPACE="staging"
IMAGE_TAG=${1:-latest}
REGISTRY="ghcr.io/your-org"
IMAGE_NAME="agent-runner"

echo "🚀 Deploying to Staging Kubernetes cluster..."
echo "   Context:  $CLUSTER_CONTEXT"
echo "   Image:    $REGISTRY/$IMAGE_NAME:$IMAGE_TAG"

# Verify kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed"
    exit 1
fi

# Set context
echo "📍 Setting Kubernetes context..."
kubectl config use-context $CLUSTER_CONTEXT || {
    echo "❌ Context '$CLUSTER_CONTEXT' not found. Available contexts:"
    kubectl config get-contexts
    exit 1
}

# Verify namespace exists
echo "🔍 Verifying namespace '$NAMESPACE'..."
kubectl get namespace $NAMESPACE > /dev/null || {
    echo "📝 Creating namespace..."
    kubectl create namespace $NAMESPACE
}

# Update image reference in deployment manifests
echo "📝 Updating image reference..."
sed "s|IMAGE_TAG|$IMAGE_TAG|g" k8s/staging/deployment.yaml > /tmp/staging-deployment.yaml

# Apply manifests
echo "📋 Applying Kubernetes manifests..."
kubectl apply -f /tmp/staging-deployment.yaml

# Wait for rollout
echo "⏳ Waiting for rollout to complete..."
kubectl rollout status deployment/agent-runner -n $NAMESPACE --timeout=10m

# Get service info
echo ""
echo "✅ Staging deployment complete!"
echo ""
echo "📋 Deployment Info:"
kubectl get deployment -n $NAMESPACE -o wide
echo ""
echo "🔗 Service URLs:"
kubectl get service agent-runner -n $NAMESPACE -o wide

# Show pod logs
echo ""
echo "📜 Recent logs:"
POD=$(kubectl get pod -n $NAMESPACE -l app=agent-runner -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n $NAMESPACE $POD --tail=20

# Cleanup
rm /tmp/staging-deployment.yaml

echo ""
echo "💡 Next steps:"
echo "   • Monitor: kubectl logs -f -n $NAMESPACE deployment/agent-runner"
echo "   • Rollback: kubectl rollout undo deployment/agent-runner -n $NAMESPACE"
echo "   • Scale: kubectl scale deployment agent-runner --replicas=5 -n $NAMESPACE"
