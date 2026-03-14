#!/bin/bash

# VH2 GitHub Actions — Setup Helper Script
# This script automates GitHub Actions secret and GCP configuration

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}VH2 GitHub Actions Setup Helper${NC}"
echo "=================================="
echo ""

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    command -v gcloud >/dev/null 2>&1 || { echo -e "${RED}✗ gcloud CLI not found${NC}"; exit 1; }
    command -v kubectl >/dev/null 2>&1 || { echo -e "${RED}✗ kubectl not found${NC}"; exit 1; }
    command -v git >/dev/null 2>&1 || { echo -e "${RED}✗ git not found${NC}"; exit 1; }
    
    echo -e "${GREEN}✓ All prerequisites found${NC}"
    echo ""
}

# Get user input
get_user_input() {
    echo -e "${YELLOW}Please provide the following information:${NC}"
    echo ""
    
    read -p "Enter GCP Project ID: " GCP_PROJECT_ID
    read -p "Enter GKE Cluster Name: " GKE_CLUSTER
    read -p "Enter GKE Zone: " GKE_ZONE
    read -p "Enter GitHub Repository (owner/repo): " GITHUB_REPO
    read -p "Enter GitHub Personal Access Token (for CLI): " GITHUB_TOKEN
    read -p "Enter Service Account Name (e.g., vh2-github-actions): " SA_NAME
    
    echo ""
    echo -e "${BLUE}Summary:${NC}"
    echo "  GCP Project ID: $GCP_PROJECT_ID"
    echo "  GKE Cluster: $GKE_CLUSTER"
    echo "  GKE Zone: $GKE_ZONE"
    echo "  GitHub Repo: $GITHUB_REPO"
    echo "  Service Account: $SA_NAME"
    echo ""
    
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    echo ""
}

# Create GCP Service Account
create_service_account() {
    echo -e "${BLUE}Creating GCP Service Account...${NC}"
    
    SA_EMAIL="$SA_NAME@$GCP_PROJECT_ID.iam.gserviceaccount.com"
    
    # Check if already exists
    if gcloud iam service-accounts describe $SA_EMAIL --project=$GCP_PROJECT_ID >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Service Account already exists${NC}"
    else
        gcloud iam service-accounts create $SA_NAME \
            --display-name="VH2 GitHub Actions" \
            --project=$GCP_PROJECT_ID
        echo -e "${GREEN}✓ Service Account created${NC}"
    fi
    
    echo ""
}

# Grant IAM Roles
grant_iam_roles() {
    echo -e "${BLUE}Granting IAM Roles...${NC}"
    
    SA_EMAIL="$SA_NAME@$GCP_PROJECT_ID.iam.gserviceaccount.com"
    
    # GKE cluster access
    gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/container.developer" \
        --condition=None \
        --quiet
    echo -e "${GREEN}✓ Granted container.developer${NC}"
    
    # Container Registry access
    gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/storage.admin" \
        --condition=None \
        --quiet
    echo -e "${GREEN}✓ Granted storage.admin${NC}"
    
    # Service Account User
    gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/iam.serviceAccountUser" \
        --condition=None \
        --quiet
    echo -e "${GREEN}✓ Granted iam.serviceAccountUser${NC}"
    
    echo ""
}

# Create Service Account Key
create_service_account_key() {
    echo -e "${BLUE}Creating Service Account Key...${NC}"
    
    SA_EMAIL="$SA_NAME@$GCP_PROJECT_ID.iam.gserviceaccount.com"
    KEY_FILE="${SA_NAME}-key.json"
    
    gcloud iam service-accounts keys create $KEY_FILE \
        --iam-account=$SA_EMAIL \
        --project=$GCP_PROJECT_ID
    
    echo -e "${GREEN}✓ Key saved to: $KEY_FILE${NC}"
    echo ""
    
    # Read and display key
    GCP_SA_KEY=$(cat $KEY_FILE)
    export GCP_SA_KEY
}

# Add GitHub Secrets
add_github_secrets() {
    echo -e "${BLUE}Adding GitHub Secrets...${NC}"
    
    # Check if gh CLI is installed
    if ! command -v gh &> /dev/null; then
        echo -e "${YELLOW}⚠ GitHub CLI (gh) not installed${NC}"
        echo "   Install from: https://cli.github.com"
        echo "   Then run: gh auth login"
        echo ""
        echo -e "${YELLOW}Manual steps:${NC}"
        echo "1. Go to: https://github.com/$GITHUB_REPO/settings/secrets/actions"
        echo "2. Add the following secrets:"
        echo ""
        echo "   Secret Name: GCP_SA_KEY"
        echo "   Value: (contents of $KEY_FILE)"
        echo ""
        echo "   Secret Name: GCP_PROJECT_ID"
        echo "   Value: $GCP_PROJECT_ID"
        echo ""
        return
    fi
    
    # Authenticate with GitHub
    echo "Authenticating with GitHub..."
    gh auth login --with-token <<< "$GITHUB_TOKEN"
    
    # Add secrets using gh CLI
    echo "Adding GCP_SA_KEY..."
    gh secret set GCP_SA_KEY --repo $GITHUB_REPO --body "$GCP_SA_KEY"
    echo -e "${GREEN}✓ GCP_SA_KEY added${NC}"
    
    echo "Adding GCP_PROJECT_ID..."
    gh secret set GCP_PROJECT_ID --repo $GITHUB_REPO --body "$GCP_PROJECT_ID"
    echo -e "${GREEN}✓ GCP_PROJECT_ID added${NC}"
    
    echo ""
}

# Update Workflow Variables
update_workflow_variables() {
    echo -e "${BLUE}Updating Workflow Variables...${NC}"
    
    WORKFLOW_FILE=".github/workflows/release-gke-deploy.yml"
    
    if [ ! -f "$WORKFLOW_FILE" ]; then
        echo -e "${YELLOW}⚠ Workflow file not found: $WORKFLOW_FILE${NC}"
        return
    fi
    
    # Update environment variables (macOS compatible)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/GKE_CLUSTER: .*/GKE_CLUSTER: $GKE_CLUSTER/" "$WORKFLOW_FILE"
        sed -i '' "s/GKE_ZONE: .*/GKE_ZONE: $GKE_ZONE/" "$WORKFLOW_FILE"
    else
        sed -i "s/GKE_CLUSTER: .*/GKE_CLUSTER: $GKE_CLUSTER/" "$WORKFLOW_FILE"
        sed -i "s/GKE_ZONE: .*/GKE_ZONE: $GKE_ZONE/" "$WORKFLOW_FILE"
    fi
    
    echo -e "${GREEN}✓ Updated GKE_CLUSTER: $GKE_CLUSTER${NC}"
    echo -e "${GREEN}✓ Updated GKE_ZONE: $GKE_ZONE${NC}"
    echo ""
}

# Verify GKE Cluster
verify_gke_cluster() {
    echo -e "${BLUE}Verifying GKE Cluster...${NC}"
    
    gcloud container clusters describe $GKE_CLUSTER \
        --zone $GKE_ZONE \
        --project $GCP_PROJECT_ID > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ GKE Cluster exists and is accessible${NC}"
    else
        echo -e "${RED}✗ GKE Cluster not found or not accessible${NC}"
        exit 1
    fi
    
    echo ""
}

# Test Service Account
test_service_account() {
    echo -e "${BLUE}Testing Service Account Access...${NC}"
    
    # Create temporary kubeconfig
    TEMP_KUBECONFIG=$(mktemp)
    export KUBECONFIG=$TEMP_KUBECONFIG
    
    # Get credentials using the key
    SA_EMAIL="$SA_NAME@$GCP_PROJECT_ID.iam.gserviceaccount.com"
    
    gcloud container clusters get-credentials $GKE_CLUSTER \
        --zone $GKE_ZONE \
        --project $GCP_PROJECT_ID \
        --impersonate-service-account=$SA_EMAIL
    
    if kubectl get nodes > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Service Account can access GKE cluster${NC}"
    else
        echo -e "${RED}✗ Service Account cannot access GKE cluster${NC}"
        exit 1
    fi
    
    # Cleanup
    rm -f $TEMP_KUBECONFIG
    unset KUBECONFIG
    echo ""
}

# Final summary
print_summary() {
    echo -e "${GREEN}========== SETUP COMPLETE ==========${NC}"
    echo ""
    echo -e "${BLUE}GitHub Actions Configuration:${NC}"
    echo "  Repository: $GITHUB_REPO"
    echo "  Workflow: .github/workflows/release-gke-deploy.yml"
    echo ""
    echo -e "${BLUE}GCP Configuration:${NC}"
    echo "  Project: $GCP_PROJECT_ID"
    echo "  Service Account: $SA_EMAIL"
    echo "  Key File: $KEY_FILE"
    echo ""
    echo -e "${BLUE}GKE Configuration:${NC}"
    echo "  Cluster: $GKE_CLUSTER"
    echo "  Zone: $GKE_ZONE"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Commit and push workflow changes:"
    echo "   git add .github/workflows/release-gke-deploy.yml"
    echo "   git commit -m 'chore: update GKE cluster configuration'"
    echo "   git push origin main"
    echo ""
    echo "2. Test the workflow:"
    echo "   Go to: https://github.com/$GITHUB_REPO/actions"
    echo "   Click: Release & Deploy to GKE"
    echo "   Click: Run workflow"
    echo ""
    echo "3. Monitor deployment:"
    echo "   kubectl get pods -n vh2-prod"
    echo "   kubectl logs -n vh2-prod -l app=vh2-backend"
    echo ""
    echo -e "${GREEN}Setup helper complete!${NC}"
    echo ""
}

# Main execution
main() {
    check_prerequisites
    get_user_input
    create_service_account
    grant_iam_roles
    create_service_account_key
    add_github_secrets
    update_workflow_variables
    verify_gke_cluster
    test_service_account
    print_summary
}

# Run main
main
