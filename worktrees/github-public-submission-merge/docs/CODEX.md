# CODEX

PowerShell bootstrap for Codex CLI:

```powershell
wsl --install -d Ubuntu
cd /mnt/c/Projects/agent/GPT-Sandbox
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs git
npm i -g @openai/codex
$env:OPENAI_API_KEY="<YOUR_OPENAI_API_KEY>"
codex --help
```

