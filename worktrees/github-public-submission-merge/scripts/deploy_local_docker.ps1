param(
  [string]$ImageName = "core-orchestrator:local",
  [string]$ContainerName = "core-orchestrator-local",
  [int]$Port = 8000,
  [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/3] Building $ImageName"
docker build -t $ImageName .

Write-Host "[2/3] Replacing container $ContainerName (if present)"
try { docker rm -f $ContainerName | Out-Null } catch { }

Write-Host "[3/3] Starting container on port $Port"
docker run -d `
  --name $ContainerName `
  -p "$Port`:8000" `
  --env-file $EnvFile `
  --restart unless-stopped `
  $ImageName

Write-Host "Container started: $ContainerName"
Write-Host "Logs: docker logs -f $ContainerName"
