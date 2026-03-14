#!/usr/bin/env bash
# VH2 Sovereign Validator — Production Setup Script
# 
# Parameterizes the deployment with your registry, domain, GitHub org, and CORS origin.
# Usage: ./setup-production.sh --registry ghcr.io/myorg --domain vh2.example.com \
#          --github-org myorg --allowed-origin https://vh2.example.com

set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 --registry REGISTRY_ORG --domain VH2_DOMAIN --github-org GITHUB_ORG --allowed-origin ALLOWED_ORIGIN

Parameters:
  --registry REGISTRY_ORG         Docker registry (e.g., ghcr.io/myorg, docker.io/username)
  --domain VH2_DOMAIN            Your domain (e.g., vh2.example.com)
  --github-org GITHUB_ORG        GitHub org/user for repo (e.g., myorg, alice)
  --allowed-origin ALLOWED_ORIGIN CORS origin (e.g., https://vh2.example.com or http://localhost)

Example:
  ./setup-production.sh \\
    --registry ghcr.io/acme-corp \\
    --domain vh2.acme.com \\
    --github-org acme-corp \\
    --allowed-origin https://vh2.acme.com

EOF
  exit 1
}

REGISTRY_ORG=""
VH2_DOMAIN=""
GITHUB_ORG=""
ALLOWED_ORIGIN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --registry) REGISTRY_ORG="$2"; shift 2 ;;
    --domain) VH2_DOMAIN="$2"; shift 2 ;;
    --github-org) GITHUB_ORG="$2"; shift 2 ;;
    --allowed-origin) ALLOWED_ORIGIN="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) 
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

# Validate all parameters provided
if [[ -z "$REGISTRY_ORG" || -z "$VH2_DOMAIN" || -z "$GITHUB_ORG" || -z "$ALLOWED_ORIGIN" ]]; then
  echo "Error: All four parameters are required."
  usage
fi

echo "════════════════════════════════════════════════════════════"
echo "VH2 Production Setup"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Configuration:"
echo "  Registry:         $REGISTRY_ORG"
echo "  Domain:           $VH2_DOMAIN"
echo "  GitHub Org:       $GITHUB_ORG"
echo "  Allowed Origin:   $ALLOWED_ORIGIN"
echo ""

# Find and patch Kubernetes manifests
echo "Patching Kubernetes manifests..."
if command -v find &> /dev/null; then
  find k8s -type f -name '*.yaml' 2>/dev/null | while read -r file; do
    if [[ -w "$file" ]]; then
      sed -i.bak \
        -e "s|\${REGISTRY_ORG}|${REGISTRY_ORG}|g" \
        -e "s|\${VH2_DOMAIN}|${VH2_DOMAIN}|g" \
        -e "s|\${ALLOWED_ORIGIN}|${ALLOWED_ORIGIN}|g" \
        "$file"
      rm -f "$file.bak"
      echo "  ✓ $file"
    fi
  done
fi

# Patch ArgoCD manifest
echo "Patching ArgoCD Application..."
if [[ -f argocd/vh2-validator-app.yaml ]]; then
  sed -i.bak \
    -e "s|https://github.com/YOUR_ORG/vh2-sovereign-validator.git|https://github.com/${GITHUB_ORG}/vh2-sovereign-validator.git|g" \
    -e "s|\${REGISTRY_ORG}|${REGISTRY_ORG}|g" \
    argocd/vh2-validator-app.yaml
  rm -f argocd/vh2-validator-app.yaml.bak
  echo "  ✓ argocd/vh2-validator-app.yaml"
fi

# Patch Helm values
echo "Patching Helm values..."
if [[ -f helm/values-prod.yaml ]]; then
  sed -i.bak \
    -e "s|\${VH2_DOMAIN}|${VH2_DOMAIN}|g" \
    -e "s|\${REGISTRY_ORG}|${REGISTRY_ORG}|g" \
    -e "s|\${ALLOWED_ORIGIN}|${ALLOWED_ORIGIN}|g" \
    helm/values-prod.yaml
  rm -f helm/values-prod.yaml.bak
  echo "  ✓ helm/values-prod.yaml"
fi

# Patch GitHub Actions workflows if they exist
echo "Patching GitHub Actions workflows..."
if [[ -d .github/workflows ]]; then
  find .github/workflows -type f -name '*.yml' -o -name '*.yaml' | while read -r file; do
    if [[ -w "$file" ]]; then
      sed -i.bak \
        -e "s|\${GITHUB_ORG}|${GITHUB_ORG}|g" \
        -e "s|\${REGISTRY_ORG}|${REGISTRY_ORG}|g" \
        "$file"
      rm -f "$file.bak"
      echo "  ✓ $file"
    fi
  done
else
  echo "  (no .github/workflows directory found)"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✓ Production parameterization complete"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Review the patched files to verify values are correct"
echo "  2. Commit changes: git add k8s/ argocd/ helm/ && git commit -m 'config: parameterize production'"
echo "  3. Push to GitHub: git push origin main"
echo "  4. Build & push images:"
echo "       docker compose build"
echo "       docker tag vh2-backend:latest ${REGISTRY_ORG}/vh2-backend:1.0.0"
echo "       docker push ${REGISTRY_ORG}/vh2-backend:1.0.0"
echo "  5. Deploy: kubectl apply -f argocd/vh2-validator-app.yaml"
echo "  6. Monitor: argocd app watch vh2-sovereign-validator"
echo ""
