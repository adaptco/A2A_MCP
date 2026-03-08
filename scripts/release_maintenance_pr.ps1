param(
    [string]$Title = "",
    [string]$Body = "",
    [string]$BodyFile = "",
    [string[]]$Labels = @(),
    [string[]]$Reviewers = @(),
    [string[]]$Assignees = @(),
    [string]$Milestone = "",
    [switch]$Draft,
    [switch]$ManualMergeOnly,
    [switch]$SkipPreflight,
    [switch]$SkipTests,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptPath = Join-Path $PSScriptRoot "push_branch_and_create_pr.ps1"
if (-not (Test-Path $scriptPath)) {
    throw "Required script not found: $scriptPath"
}

$argsList = @(
    "-BaseBranch", "main",
    "-Remote", "upstream",
    "-Repo", "adaptco-main/A2A_MCP",
    "-MergeMethod", "squash"
)

if (-not [string]::IsNullOrWhiteSpace($Title)) { $argsList += @("-Title", $Title) }
if (-not [string]::IsNullOrWhiteSpace($Body)) { $argsList += @("-Body", $Body) }
if (-not [string]::IsNullOrWhiteSpace($BodyFile)) { $argsList += @("-BodyFile", $BodyFile) }
if ($Labels.Count -gt 0) {
    $normalized = $Labels | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    if ($normalized.Count -gt 0) {
        $argsList += "-Labels"
        $argsList += $normalized
    }
}
if ($Reviewers.Count -gt 0) {
    $normalized = $Reviewers | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    if ($normalized.Count -gt 0) {
        $argsList += "-Reviewers"
        $argsList += $normalized
    }
}
if ($Assignees.Count -gt 0) {
    $normalized = $Assignees | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    if ($normalized.Count -gt 0) {
        $argsList += "-Assignees"
        $argsList += $normalized
    }
}
if (-not [string]::IsNullOrWhiteSpace($Milestone)) { $argsList += @("-Milestone", $Milestone) }

if ($Draft) { $argsList += "-Draft" }
if ($ManualMergeOnly) { $argsList += "-ManualMergeOnly" }
if ($SkipPreflight) { $argsList += "-SkipPreflight" }
if ($SkipTests) { $argsList += "-SkipTests" }
if ($DryRun) { $argsList += "-DryRun" }

& $scriptPath @argsList
exit $LASTEXITCODE
