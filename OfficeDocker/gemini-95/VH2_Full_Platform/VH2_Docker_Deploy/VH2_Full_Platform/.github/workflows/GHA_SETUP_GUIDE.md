# GitHub Actions — VH2 GKE Deployment Setup

> Configure GitHub Actions CI/CD workflow for automated testing, building, and deploying to Google Kubernetes Engine (GKE)

---

## 📋 Prerequisites

- ✅ GitHub repository with VH2 code
- ✅ Google Cloud Project with GKE cluster
- ✅ Service Account with appropriate IAM roles
- ✅ Docker images pushed to Google Container Registry (GCR)
- ✅ (Optional) ArgoCD instance running in K8s

---

## 🔑 Step 1: Create Google Cloud Service Account

### 1.1 Create Service Account

```bash
export PROJECT_ID="your-gcp-project-id"
export SA_NAME="vh2-github-actions"

# Create service account
gcloud iam service-accounts create $SA_NAME \
  --display-name="VH2 GitHub Actions" \
  --project=$PROJECT_ID
```

### 1.2 Grant Required IAM Roles

```bash
export SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

# GKE cluster access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/container.developer"

# Container Registry (push images)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.admin"

# Service Account User
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/iam.serviceAccountUser"
```

### 1.3 Create Service Account Key

```bash
# Create JSON key
gcloud iam service-accounts keys create ~/vh2-gha-key.json \
  --iam-account=$SA_EMAIL

# Copy the key (you'll need this in Step 2)
cat ~/vh2-gha-key.json
```

---

## 🔐 Step 2: Configure GitHub Secrets

### 2.1 Access Repository Settings

```bash
# In GitHub:
1. Go to Settings → Secrets and Variables → Actions
2. Click "New repository secret"
```

### 2.2 Add Required Secrets

| Secret Name | Value | Notes |
|-------------|-------|-------|
| `GCP_SA_KEY` | JSON key from 1.3 | Full JSON key content |
| `GCP_PROJECT_ID` | `your-gcp-project-id` | Your GCP project ID |
| `ARGOCD_SERVER` | `argocd.example.com` | ArgoCD server URL (optional) |
| `ARGOCD_TOKEN` | ArgoCD token | Generated in ArgoCD (optional) |
| `SLACK_WEBHOOK_URL` | Slack webhook URL | For notifications (optional) |

### 2.3 Add Secret Step-by-Step

```bash
# Example: Adding GCP_SA_KEY
1. Go to GitHub Repo → Settings → Secrets and Variables → Actions
2. Click "New repository secret"
3. Name: GCP_SA_KEY
4. Value: (paste entire contents of vh2-gha-key.json)
5. Click "Add secret"

# Repeat for other secrets:
- GCP_PROJECT_ID
- ARGOCD_SERVER (if using)
- ARGOCD_TOKEN (if using)
- SLACK_WEBHOOK_URL (if using)
```

---

## 🔧 Step 3: Configure Workflow Variables

Edit `.github/workflows/release-gke-deploy.yml` to match your setup:

```yaml
env:
  REGISTRY: gcr.io                          # Google Container Registry
  GKE_CLUSTER: vh2-sovereign-validator      # ← YOUR CLUSTER NAME
  GKE_ZONE: us-central1-a                   # ← YOUR GKE ZONE
  DEPLOYMENT_NAME: vh2-backend
  IMAGE_BACKEND: vh2-backend
  IMAGE_FRONTEND: vh2-frontend
```

---

## 🚀 Step 4: Workflow Overview

The workflow runs the following jobs in sequence:

### Job 1: Test & Validate
```
✓ Checkout code
✓ Setup Node.js 20
✓ Run 42 unit tests
✓ Validate K8s YAML manifests
✓ Check Docker files exist
→ Continues only if all tests pass
```

### Job 2: Build & Push Images
```
✓ Build backend Docker image
✓ Build frontend Docker image
✓ Push to GCR with git SHA tag
✓ Tag as :latest
→ Outputs image URLs for deployment
```

### Job 3: Deploy to GKE
```
✓ Get GKE cluster credentials
✓ Update image references in kustomization.yaml
✓ Apply K8s manifests via kubectl
✓ Wait for deployments to be ready
✓ Verify pods are running
→ Continues only if deployment succeeds
```

### Job 4: Smoke Tests
```
✓ Port-forward to backend service
✓ Test /health endpoint
✓ Test /ready endpoint
✓ Test /validate endpoint
✓ Verify SOVEREIGN_PASS response
✓ Run PostSync job
→ Continues only if all tests pass
```

### Job 5: ArgoCD Sync (Optional)
```
✓ Sync vh2-sovereign-validator app
✓ Wait for sync to complete
→ Only runs if on main branch
```

### Job 6: Notification
```
✓ Determine overall status
✓ Send Slack notification
✓ Comment on PR
→ Always runs (success or failure)
```

---

## 📊 Trigger Conditions

The workflow runs automatically on:

```yaml
on:
  push:
    branches:
      - main                    # Triggered on main branch push
    paths:
      - 'vh2-docker/**'         # Only if VH2 files changed
      - '.github/workflows/release-gke-deploy.yml'

  workflow_dispatch:            # Manual trigger from GitHub UI
    with:
      environment:
        options:
          - staging
          - production
```

---

## 🎯 Manual Workflow Trigger

To manually trigger the workflow from GitHub:

```
1. Go to Actions tab
2. Select "Release & Deploy to GKE"
3. Click "Run workflow"
4. Select environment: staging or production
5. Click "Run workflow"
```

---

## 📈 Monitoring Workflow

### View Workflow Runs

```bash
# In GitHub:
1. Go to Actions tab
2. Click "Release & Deploy to GKE"
3. See list of all workflow runs
4. Click a run to view details
```

### Check Job Status

```bash
# In GitHub UI:
1. Click on a workflow run
2. Expand each job to see logs
3. Green checkmark = passed
4. Red X = failed
```

### View Logs

```bash
# View logs of specific job:
1. Click workflow run
2. Click job name (e.g., "Build & Push Docker Images")
3. Expand step to see full output
4. Look for ✓ or ✗ indicators
```

---

## 🔍 Debugging Failed Workflows

### Common Failures & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `invalid key for GCP_SA_KEY` | Malformed JSON | Re-paste full JSON key from 1.3 |
| `unable to connect to GKE` | Invalid credentials | Verify GCP_SA_KEY and GCP_PROJECT_ID |
| `image push failed` | GCR permissions | Ensure SA has `roles/storage.admin` |
| `pod failed to start` | Image not found | Check GCR image URL in logs |
| `test failures` | Code issues | Check test job logs for details |

### View Detailed Logs

```bash
# In GitHub UI:
1. Go to Actions → Release & Deploy to GKE
2. Click failed workflow run
3. Scroll to failed job
4. Expand each step to see output
5. Look for error messages

# Example: Build job logs
# Shows: docker build output
# Shows: GCR push confirmation
# Shows: Image digest (SHA256)
```

---

## 🔒 Security Best Practices

### Secret Management

✅ **DO:**
- Store all credentials in GitHub Secrets
- Rotate service account keys regularly
- Use least-privilege IAM roles
- Review access logs in GCP

❌ **DON'T:**
- Commit secrets to git
- Hardcode credentials in YAML
- Share service account keys
- Use production creds for testing

### Restrict Deployment

```yaml
# Add environment protection in GitHub:
1. Go to Environments
2. Create new environment: "production"
3. Add required reviewers
4. Add protection rules
→ Deployment requires approval
```

---

## 📬 Notifications

### Configure Slack Notifications

```bash
# 1. Create Slack Webhook URL
#    Slack Workspace → Apps → Incoming Webhooks
#    → Create New Webhook → Copy URL

# 2. Add to GitHub Secrets
#    Settings → Secrets → SLACK_WEBHOOK_URL

# 3. Workflow will notify on:
#    - Deployment success
#    - Deployment failure
#    - Test failures
```

### Example Slack Message

```
VH2 Deployment Report
✅ Deployment Successful

Commit: abc123def456
Ref: refs/heads/main
Author: github-user

- Test: success
- Build: success
- Deploy: success
- Smoke Tests: success
```

---

## 🔄 Deployment Flow

```
Git Push (main branch)
         ↓
GitHub Actions Triggered
         ↓
┌─────────────────────┐
│ 1. Test & Validate  │ ← Run 42 unit tests, validate YAML
└─────────────────────┘
         ↓
┌─────────────────────┐
│ 2. Build & Push     │ ← docker build, push to GCR
└─────────────────────┘
         ↓
┌─────────────────────┐
│ 3. Deploy to GKE    │ ← kubectl apply -k vh2-docker/k8s/
└─────────────────────┘
         ↓
┌─────────────────────┐
│ 4. Smoke Tests      │ ← curl /health, /validate, verify response
└─────────────────────┘
         ↓
┌─────────────────────┐
│ 5. ArgoCD Sync      │ ← (optional) sync application
└─────────────────────┘
         ↓
┌─────────────────────┐
│ 6. Notification     │ ← Slack + GitHub comment
└─────────────────────┘
         ↓
    Deployment Complete ✓
```

---

## 🧪 Test the Workflow

### Trigger Workflow

```bash
# 1. Make a change in vh2-docker/
git checkout -b feature/test-workflow
echo "# Test change" >> vh2-docker/README.md

# 2. Commit and push
git add vh2-docker/README.md
git commit -m "test: trigger workflow"
git push origin feature/test-workflow

# 3. Create PR and merge to main
# OR push directly to main if no PR required

git checkout main
git merge feature/test-workflow
git push origin main

# 4. Watch workflow run
# GitHub Actions → Release & Deploy to GKE
```

### Monitor Progress

```bash
# Watch in GitHub UI:
1. Go to Actions tab
2. See "Release & Deploy to GKE" running
3. Click workflow to expand jobs
4. Watch each job complete in sequence
5. Scroll to see logs if interested
```

---

## ⚙️ Advanced Configuration

### Custom Image Registry

If using Docker Hub instead of GCR:

```yaml
# Change in env section:
REGISTRY: docker.io

# In build step:
docker build -t ${{ secrets.DOCKERHUB_USERNAME }}/vh2-backend:${{ tag }} ...
docker login -u ${{ secrets.DOCKERHUB_USERNAME }} -p ${{ secrets.DOCKERHUB_TOKEN }}
docker push ...
```

### Multiple Environments

```yaml
# Add environment-specific deployments:
deploy-staging:
  environment: staging
  if: github.ref == 'refs/heads/develop'

deploy-prod:
  environment: production
  if: github.ref == 'refs/heads/main'
```

### Custom Smoke Tests

Add more comprehensive tests in the `smoke-test` job:

```bash
# Test database connectivity
# Test cache availability
# Load test the API
# Verify metrics collection
# Check log aggregation
```

---

## 📞 Troubleshooting

### Issue: Workflow Not Triggering

```bash
# Check:
1. Changes made to files in 'paths' filter?
   - vh2-docker/**
   - .github/workflows/release-gke-deploy.yml

2. Is branch 'main'?
   - Workflow only triggers on main branch

3. Are all tests passing?
   - Workflow skips build if tests fail

# Solution:
# Push to main branch
# Make changes to vh2-docker/ directory
```

### Issue: GKE Credentials Invalid

```bash
# Debug:
1. Verify GCP_SA_KEY secret is set correctly
2. Verify GCP_PROJECT_ID matches service account
3. Check service account has required IAM roles

# Solution:
gcloud iam service-accounts keys list --iam-account=$SA_EMAIL
# Recreate key if needed
gcloud iam service-accounts keys create ~/new-key.json --iam-account=$SA_EMAIL
```

### Issue: Image Push Failed

```bash
# Check:
1. Service account has storage.admin role
2. GCR is enabled in GCP project
3. Image names are correct

# Enable GCR:
gcloud services enable containerregistry.googleapis.com --project=$PROJECT_ID
```

---

## 📋 Checklist Before Go-Live

- [ ] GitHub repository set up with VH2 code
- [ ] Google Cloud Service Account created
- [ ] IAM roles granted to service account
- [ ] GCP_SA_KEY secret added to GitHub
- [ ] GCP_PROJECT_ID secret added to GitHub
- [ ] GKE cluster name updated in workflow
- [ ] GKE zone updated in workflow
- [ ] Workflow tested with manual trigger
- [ ] Git push to main triggers workflow
- [ ] All jobs complete successfully
- [ ] Images appear in GCR
- [ ] Deployment successful in GKE
- [ ] Pods running in vh2-prod namespace
- [ ] Smoke tests pass
- [ ] Slack notifications working (if configured)
- [ ] Team trained on workflow

---

## 🎯 Next Steps

1. **Create Service Account** → Run commands in Step 1
2. **Add GitHub Secrets** → Follow Step 2
3. **Update Workflow Variables** → Edit `.github/workflows/release-gke-deploy.yml`
4. **Test Workflow** → Push to main branch
5. **Monitor Deployment** → Watch Actions tab
6. **Verify in GKE** → `kubectl get pods -n vh2-prod`

---

**Last Updated:** 2025-02-22  
**Status:** Ready for Production Deployment  
**Automation Level:** Full CI/CD with testing, build, deploy, and smoke tests
