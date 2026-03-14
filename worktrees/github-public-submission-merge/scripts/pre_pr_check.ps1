param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$failed = $false

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "== $Title =="
}

function Mark-Fail {
    param([string]$Message)
    Write-Host "[FAIL] $Message"
    $script:failed = $true
}

function Mark-Pass {
    param([string]$Message)
    Write-Host "[PASS] $Message"
}

Write-Section "Repo"
$branch = (git branch --show-current).Trim()
if ([string]::IsNullOrWhiteSpace($branch)) {
    Mark-Fail "Unable to determine git branch."
} else {
    Mark-Pass "Branch: $branch"
}

$status = git status --short
if ($status) {
    Mark-Fail "Working tree is not clean."
    $status | ForEach-Object { Write-Host "  $_" }
} else {
    Mark-Pass "Working tree is clean."
}

Write-Section "Merge Markers"
$mergeMarkers = rg -n "^(<<<<<<< .+|=======|>>>>>>> .+)$" . 2>$null
if ($LASTEXITCODE -eq 0 -and $mergeMarkers) {
    Mark-Fail "Potential merge markers found."
    $mergeMarkers | ForEach-Object { Write-Host "  $_" }
} else {
    Mark-Pass "No merge markers found."
}

Write-Section "Secret-like Assignments (Tracked Files)"
$secretMatches = git grep -nE "(LLM_API_KEY=|TWILIO_AUTH_TOKEN=|OPENAI_API_KEY=)" -- . 2>$null
if ($LASTEXITCODE -eq 0 -and $secretMatches) {
    Mark-Fail "Tracked files contain secret-like assignments."
    $secretMatches | ForEach-Object {
        $parts = $_ -split ":", 3
        if ($parts.Count -ge 2) {
            Write-Host ("  {0}:{1}" -f $parts[0], $parts[1])
        } else {
            Write-Host "  $_"
        }
    }
} else {
    Mark-Pass "No tracked secret-like assignments found."
}

if (-not $SkipTests) {
    Write-Section "Test Gate"
    & C:\Users\eqhsp\.venv-qe\Scripts\python -m pytest -q `
        tests/test_intent_engine.py `
        tests/test_full_pipeline.py `
        tests/test_stateflow.py `
        tests/test_cicd_pipeline.py
    if ($LASTEXITCODE -ne 0) {
        Mark-Fail "Required test gate failed."
    } else {
        Mark-Pass "Required test gate passed."
    }
}

Write-Section "Summary"
if ($failed) {
    Write-Host "CHECKLIST: FAILED"
    exit 1
}

Write-Host "CHECKLIST: PASSED"
exit 0
