[CmdletBinding()]
param(
    [ValidateSet("init", "validate", "up", "down", "restart", "logs", "ps", "health")]
    [string]$Action = "up",
    [switch]$Build,
    [switch]$Attach,
    [switch]$RemoveVolumes
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "== $Title =="
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
COMPOSE_PROJECT_NAME=a2a_automation
AUTOMATION_RUNTIME_API_PORT=8010
AUTOMATION_FRONTEND_PORT=4173
VITE_RUNTIME_API_BASE_URL=http://localhost:8010
A2A_FRONTEND_ALLOWED_ORIGINS=http://localhost:4173,http://127.0.0.1:4173
A2A_FORENSIC_NDJSON=/tmp/a2a_runtime_scenario_audit.ndjson
"@ | Set-Content -Encoding UTF8 $EnvPath
    Write-Host "[INIT] Created $EnvPath with default values."
}

function Import-EnvFile {
    param([string]$EnvPath)

    Get-Content $EnvPath | ForEach-Object {
        $line = $_.Trim()
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith("#")) {
            return
        }

        $separatorIndex = $line.IndexOf("=")
        if ($separatorIndex -lt 1) {
            return
        }

        $name = $line.Substring(0, $separatorIndex).Trim()
        $value = $line.Substring($separatorIndex + 1).Trim()
        [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

function Invoke-Compose {
    param(
        [string]$ComposePath,
        [string]$EnvPath,
        [string]$ProjectName,
        [string[]]$Args
    )

    & docker compose --project-name $ProjectName --env-file $EnvPath -f $ComposePath @Args
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
$composePath = Join-Path $repoRoot "docker-compose.automation.yml"
$envPath = Join-Path $repoRoot ".env.automation"
$envTemplatePath = Join-Path $repoRoot ".env.automation.example"

Set-Location $repoRoot

Write-Section "Prerequisites"
Ensure-EnvFile -EnvPath $envPath -TemplatePath $envTemplatePath
Import-EnvFile -EnvPath $envPath
Ensure-DockerCli

$projectName = if ($env:COMPOSE_PROJECT_NAME) { $env:COMPOSE_PROJECT_NAME } else { "a2a_automation" }
$runtimePort = if ($env:AUTOMATION_RUNTIME_API_PORT) { $env:AUTOMATION_RUNTIME_API_PORT } else { "8010" }
$frontendPort = if ($env:AUTOMATION_FRONTEND_PORT) { $env:AUTOMATION_FRONTEND_PORT } else { "4173" }

Write-Host ("Project: {0}" -f $projectName)
Write-Host ("Compose: {0}" -f $composePath)
Write-Host ("Env: {0}" -f $envPath)

$requiresDaemon = $Action -in @("up", "down", "restart", "logs", "ps", "health")
if ($requiresDaemon) {
    Ensure-DockerDaemon
}

switch ($Action) {
    "init" {
        Write-Section "Init"
        Write-Host "[PASS] Automation environment is initialized."
    }

    "validate" {
        Write-Section "Validate"
        & docker compose --project-name $projectName --env-file $envPath -f $composePath config | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose config failed."
        }
        Write-Host "[PASS] Compose configuration is valid."
    }

    "up" {
        Write-Section "Up"
        $upArgs = @("up")
        if ($Build) {
            $upArgs += "--build"
        }
        if (-not $Attach) {
            $upArgs += "-d"
        }

        Invoke-Compose -ComposePath $composePath -EnvPath $envPath -ProjectName $projectName -Args $upArgs

        Write-Host ""
        Write-Host "Automation environment endpoints:"
        Write-Host ("- Runtime API: http://localhost:{0}/healthz" -f $runtimePort)
        Write-Host ("- Frontend:    http://localhost:{0}" -f $frontendPort)
    }

    "down" {
        Write-Section "Down"
        $downArgs = @("down")
        if ($RemoveVolumes) {
            $downArgs += "-v"
        }
        Invoke-Compose -ComposePath $composePath -EnvPath $envPath -ProjectName $projectName -Args $downArgs
    }

    "restart" {
        Write-Section "Restart"
        Invoke-Compose -ComposePath $composePath -EnvPath $envPath -ProjectName $projectName -Args @("restart")
    }

    "logs" {
        Write-Section "Logs"
        Invoke-Compose -ComposePath $composePath -EnvPath $envPath -ProjectName $projectName -Args @("logs", "-f", "--tail", "200")
    }

    "ps" {
        Write-Section "Status"
        Invoke-Compose -ComposePath $composePath -EnvPath $envPath -ProjectName $projectName -Args @("ps")
    }

    "health" {
        Write-Section "Health"
        Invoke-Compose -ComposePath $composePath -EnvPath $envPath -ProjectName $projectName -Args @("ps")

        $checks = @(
            @{ Name = "automation-runtime"; Url = ("http://localhost:{0}/healthz" -f $runtimePort) },
            @{ Name = "automation-frontend"; Url = ("http://localhost:{0}" -f $frontendPort) }
        )

        $allHealthy = $true
        foreach ($check in $checks) {
            if (-not (Test-Endpoint -Name $check.Name -Url $check.Url)) {
                $allHealthy = $false
            }
        }

        if (-not $allHealthy) {
            throw "One or more services failed health checks."
        }
    }
}
