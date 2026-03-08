# Free CI Alternatives to GitHub Actions

This document provides solutions to avoid GitHub Actions billing issues.

## Problem
GitHub Actions requires paid minutes for private repositories. When billing fails, all CI checks fail with:
```
The job was not started because recent account payments have failed
```

## Solutions (Ranked by Ease)

### 1. 🎯 Local Pre-commit Hooks (Recommended)
**Cost:** Free  
**Setup Time:** 5 minutes  
**Pros:** Catches issues before commit, no remote CI needed  

#### Setup
```bash
pip install pre-commit
pre-commit install
```

Checks run automatically before each commit. To run manually:
```bash
pre-commit run --all-files
```

Configuration: `.pre-commit-config.yaml`

---

### 2. 🛠️ Local Validation Script
**Cost:** Free  
**Setup Time:** 0 minutes (already created)  
**Pros:** Simple, no external dependencies  

#### Usage
```bash
./scripts/local_ci_check.sh
```

Or with Make:
```bash
make -f Makefile.ci test
```

---

### 3. 📦 Self-Hosted GitHub Runners
**Cost:** Free (requires own server)  
**Setup Time:** 30 minutes  
**Pros:** Still uses GitHub Actions, full control  

#### Setup
1. Navigate to: Settings → Actions → Runners → New self-hosted runner
2. Follow instructions to install on your server
3. Update workflows:
   ```yaml
   jobs:
     test:
       runs-on: self-hosted  # Changed from ubuntu-latest
   ```

See: `docs/SELF_HOSTED_RUNNER_SETUP.md`

---

### 4. 🔄 CircleCI (Free Tier)
**Cost:** Free (6,000 build minutes/month)  
**Setup Time:** 10 minutes  
**Pros:** Generous free tier, good for open source  

#### Setup
1. Sign up at https://circleci.com
2. Connect GitHub repository
3. Configuration: `.circleci/config.yml` (already created)

---

### 5. 🚀 Travis CI (Free for Open Source)
**Cost:** Free (if repo is public)  
**Setup Time:** 10 minutes  
**Pros:** Well-established, simple setup  

#### Setup
1. Sign up at https://travis-ci.com
2. Sync GitHub repository
3. Configuration: `.travis.yml` (already created)

---

### 6. ⚡ Manual GitHub Actions (On-Demand)
**Cost:** Minimal (only when manually triggered)  
**Setup Time:** 0 minutes (already created)  
**Pros:** Uses existing GitHub Actions, controlled usage  

#### Usage
1. Go to Actions tab
2. Select "Manual CI (Free - On Demand)"
3. Click "Run workflow"

Configuration: `.github/workflows/manual-ci.yml`

---

### 7. 🧠 Smart Conditional CI
**Cost:** Reduced (selective execution)  
**Setup Time:** 0 minutes (already created)  
**Pros:** Automatic but selective  

Skips runs for:
- Draft PRs
- Commits with `[skip ci]` message
- Non-main branches

Configuration: `.github/workflows/smart-ci.yml`

---

## Comparison Table

| Solution | Cost | Automatic | Setup Complexity | Best For |
|----------|------|-----------|------------------|----------|
| Pre-commit Hooks | Free | Yes (local) | Low | Individual developers |
| Local Script | Free | No | None | Quick validation |
| Self-Hosted Runner | Free* | Yes | Medium | Teams with servers |
| CircleCI | Free | Yes | Low | Small-medium projects |
| Travis CI | Free** | Yes | Low | Open source |
| Manual Actions | Minimal | No | None | Occasional checks |
| Smart CI | Reduced | Conditional | None | Reducing costs |

\* Requires server costs  
\*\* Only for public repos

---

## Recommended Approach

### For This Repository
Use a **combination**:

1. **Pre-commit hooks** for developers (catches 90% of issues)
2. **Manual CI** for PR validation when needed
3. **Self-hosted runner** if you have a spare server

### Migration Steps

#### Step 1: Enable Pre-commit
```bash
pip install pre-commit
pre-commit install
```

#### Step 2: Update Existing Workflows
Add condition to skip when not needed:
```yaml
on:
  workflow_dispatch:  # Manual only
  # Remove automatic triggers (push, pull_request)
```

#### Step 3: Update README
Add badge for manual CI status:
```markdown
[![Manual CI](https://github.com/Q-Enterprises/core-orchestrator/workflows/Manual%20CI/badge.svg)](https://github.com/Q-Enterprises/core-orchestrator/actions)
```

---

## Current Files Created

✅ `.pre-commit-config.yaml` - Pre-commit hooks  
✅ `.circleci/config.yml` - CircleCI configuration  
✅ `.travis.yml` - Travis CI configuration  
✅ `.github/workflows/manual-ci.yml` - Manual trigger workflow  
✅ `.github/workflows/smart-ci.yml` - Conditional workflow  
✅ `Makefile.ci` - Make-based local testing  
✅ `scripts/local_ci_check.sh` - Bash validation script  

---

## Converting Existing Workflows

### Current (Uses GitHub-hosted runners)
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
```

### Option A: Self-hosted
```yaml
jobs:
  build:
    runs-on: self-hosted
```

### Option B: Manual only
```yaml
on:
  workflow_dispatch:
```

### Option C: Disable entirely
Rename `.github/workflows/ci.yml` to `.github/workflows/ci.yml.disabled`

---

## Testing Your Setup

### Test Pre-commit
```bash
pre-commit run --all-files
```

### Test Local Script
```bash
./scripts/local_ci_check.sh
```

### Test Make
```bash
make -f Makefile.ci test
```

All should output:
```
✅ ALL CRITICAL CHECKS PASSED
```

---

## Questions?

- Pre-commit not working? Ensure hooks are installed: `pre-commit install`
- Self-hosted runner offline? Check service: `sudo ./svc.sh status`
- CircleCI not detecting config? Ensure `.circleci/config.yml` is in root
