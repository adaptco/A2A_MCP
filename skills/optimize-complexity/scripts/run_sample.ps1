param(
    [string]$OutputDir = ""
)

$skillDir = Split-Path -Parent $PSScriptRoot
$sampleCsv = Join-Path $skillDir "assets\sample_orchestration_checkpoint.csv"
$scriptPath = Join-Path $PSScriptRoot "optimize_complexity.py"

if (-not (Test-Path $sampleCsv)) {
    throw "Sample CSV not found: $sampleCsv"
}

$cmd = @(
    "python",
    $scriptPath,
    "--checkpoint-path", $sampleCsv,
    "--report-format", "both"
)

if ($OutputDir -ne "") {
    $cmd += @("--out-dir", $OutputDir)
}

Write-Host "Running sample optimization..."
& $cmd[0] $cmd[1..($cmd.Length - 1)]
exit $LASTEXITCODE