# Self-Hosted Runner Setup (Free Alternative)

## Overview
Use self-hosted runners instead of GitHub-hosted runners to avoid billing issues.

## Setup Steps

### 1. Install Self-Hosted Runner
```bash
# On your server/local machine
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# Configure (get token from repo Settings > Actions > Runners)
./config.sh --url https://github.com/Q-Enterprises/core-orchestrator --token YOUR_TOKEN

# Run as service
sudo ./svc.sh install
sudo ./svc.sh start
```

### 2. Update Workflows to Use Self-Hosted Runner
Change `runs-on: ubuntu-latest` to `runs-on: self-hosted`

## Advantages
- ✅ No GitHub Actions billing
- ✅ Faster (local network)
- ✅ Full control over environment

## Disadvantages
- ⚠️ Requires maintaining a server
- ⚠️ Security considerations for public repos
