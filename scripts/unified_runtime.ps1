[CmdletBinding()]
param(
    [ValidateSet("init", "validate", "up", "down", "restart", "logs", "ps", "health")]
    [string]$Action = "up",
    [string]$ComposeFile = "docker-compose.unified.yml",
    [string]$EnvFile = ".env.unified",
    [string]$ProjectName = "a2a_unified",
    [switch]$Build,
    [switch]$Attach,
    [switch]$NoCache,
    [switch]$Pull,
    [switch]$RemoveVolumes
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "== $Title =="
}

function Resolve-RepoPath {
    param([string]$PathValue, [string]$RepoRoot)
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return $PathValue
    }
    return (Join-Path $RepoRoot $PathValue)
}

function Ensure-DockerCli {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker CLI not found on PATH."
    }
    & docker compose version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose plugin is not available."
    }
}

function Ensure-DockerDaemon {
    & docker version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker daemon is not reachable. Start Docker Desktop and retry."
    }
}

function Ensure-EnvFile {
    param(
        [string]$EnvPath,
        [string]$TemplatePath
    )
    if (Test-Path $EnvPath) {
        return
    }

    if (Test-Path $TemplatePath) {
        Copy-Item $TemplatePath $EnvPath
        Write-Host "[INIT] Created $EnvPath from template."
        return
    }

    @"
COMPOSE_PROJECT_NAME=a2a_unified
POSTGRES_PASSWORD=pass
POSTGRES_DB=mcp_db
RBAC_SECRET=dev-secret-change-me
LLM_API_KEY=
LLM_ENDPOINT=https://api.mistral.ai/v1/chat/completions
LLM_MODEL=gpt-4o-mini
A2A_ORCHESTRATION_MODEL=
A2A_ORCHESTRATION_EMBEDDING_LANGUAGE=code
"@ | Set-Content -Encoding UTF8 $EnvPath
    Write-Host "[INIT] Created $EnvPath with default values."
}

function Import-EnvFile {
    param([string]$EnvPath)
    Get-Content $EnvPath | ForEach-Object {
        $line = $_.Trim()
        if ([string]::IsNullOrWhiteSpace($line)) {
            return
        }
        if ($line.StartsWith("#")) {
            return
        }

        $separatorIndex = $line.IndexOf("=")
        if ($separatorIndex -lt 1) {
            return
        }

        $name = $line.Substring(0, $separatorIndex).Trim()
        $value = $line.Substring($separatorIndex + 1).Trim()

        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            if ($value.Length -ge 2) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }

        [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

function Invoke-Compose {
    param(
        [string]$ComposePath,
        [string]$EnvPath,
        [string]$Project,
        [string[]]$Args
    )

    & docker compose --project-name $Project --env-file $EnvPath -f $ComposePath @Args
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose $($Args -join ' ') failed."
    }
}

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$Attempts = 10,
        [int]$DelaySeconds = 2
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                Write-Host ("[PASS] {0}: {1}" -f $Name, $Url)
                return $true
            }
        } catch {
            # Service may still be starting.
        }
        Start-Sleep -Seconds $DelaySeconds
    }

    Write-Host ("[FAIL] {0}: {1}" -f $Name, $Url)
    return $false
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$composePath = Resolve-RepoPath -PathValue $ComposeFile -RepoRoot $repoRoot
if (-not (Test-Path $composePath)) {
    throw "Compose file not found: $composePath"
}

$envPath = Resolve-RepoPath -PathValue $EnvFile -RepoRoot $repoRoot
$envTemplatePath = Resolve-RepoPath -PathValue ".env.unified.example" -RepoRoot $repoRoot

Write-Section "Prerequisites"
Ensure-EnvFile -EnvPath $envPath -TemplatePath $envTemplatePath
Import-EnvFile -EnvPath $envPath
Ensure-DockerCli

if ($env:COMPOSE_PROJECT_NAME) {
    $ProjectName = $env:COMPOSE_PROJECT_NAME
}

Write-Host ("Project: {0}" -f $ProjectName)
Write-Host ("Compose: {0}" -f $composePath)
Write-Host ("Env: {0}" -f $envPath)

$requiresDaemon = $Action -in @("up", "down", "restart", "logs", "ps", "health")
if ($Action -eq "init" -and $Pull) {
    $requiresDaemon = $true
}
if ($requiresDaemon) {
    Ensure-DockerDaemon
}

switch ($Action) {
    "init" {
        Write-Section "Init"
        if ($Pull) {
            Invoke-Compose -ComposePath $composePath -EnvPath $envPath -Project $ProjectName -Args @("pull")
        }
        Write-Host "[PASS] Unified runtime environment is initialized."
    }

    "validate" {
        Write-Section "Validate"
        & docker compose --project-name $ProjectName --env-file $envPath -f $composePath config | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose config failed."
        }
        Write-Host "[PASS] Compose configuration is valid."
    }

    "up" {
        Write-Section "Up"
        if ($Pull) {
            Invoke-Compose -ComposePath $composePath -EnvPath $envPath -Project $ProjectName -Args @("pull")
        }
        if ($NoCache) {
            $buildArgs = @("build", "--no-cache")
            if ($Pull) {
                $buildArgs += "--pull"
            }
            Invoke-Compose -ComposePath $composePath -EnvPath $envPath -Project $ProjectName -Args $buildArgs
        }

        $upArgs = @("up")
        if ($Build -and -not $NoCache) {
            $upArgs += "--build"
        }
        if (-not $Attach) {
            $upArgs += "-d"
        }
        Invoke-Compose -ComposePath $composePath -EnvPath $envPath -Project $ProjectName -Args $upArgs

        Write-Host ""
        Write-Host "Runtime endpoints:"
        Write-Host "- Orchestrator: http://localhost:8000/health"
        Write-Host "- RBAC Gateway: http://localhost:8001/health"
        Write-Host "- Ingest API:   http://localhost:8002/health"
        Write-Host "- Qdrant:       http://localhost:6333/healthz"
    }

    "down" {
        Write-Section "Down"
        $downArgs = @("down")
        if ($RemoveVolumes) {
            $downArgs += "-v"
        }
        Invoke-Compose -ComposePath $composePath -EnvPath $envPath -Project $ProjectName -Args $downArgs
    }

    "restart" {
        Write-Section "Restart"
        Invoke-Compose -ComposePath $composePath -EnvPath $envPath -Project $ProjectName -Args @("restart")
    }

    "logs" {
        Write-Section "Logs"
        Invoke-Compose -ComposePath $composePath -EnvPath $envPath -Project $ProjectName -Args @("logs", "-f", "--tail", "200")
    }

    "ps" {
        Write-Section "Status"
        Invoke-Compose -ComposePath $composePath -EnvPath $envPath -Project $ProjectName -Args @("ps")
    }

    "health" {
        Write-Section "Health"
        Invoke-Compose -ComposePath $composePath -EnvPath $envPath -Project $ProjectName -Args @("ps")

        $checks = @(
            @{ Name = "orchestrator"; Url = "http://localhost:8000/health" },
            @{ Name = "rbac-gateway"; Url = "http://localhost:8001/health" },
            @{ Name = "ingest-api"; Url = "http://localhost:8002/health" },
            @{ Name = "qdrant"; Url = "http://localhost:6333/healthz" }
        )

        $allHealthy = $true
        foreach ($check in $checks) {
            $healthy = Test-Endpoint -Name $check.Name -Url $check.Url
            if (-not $healthy) {
                $allHealthy = $false
            }
        }

        if (-not $allHealthy) {
            throw "One or more services failed health checks."
        }
    }
}
