param(
    [string]$BaseBranch = "main",
    [string]$Remote = "upstream",
    [string]$Repo = "adaptco-main/A2A_MCP",
    [string]$Title = "",
    [string]$Body = "",
    [string]$BodyFile = "",
    [string[]]$Labels = @(),
    [string[]]$Reviewers = @(),
    [string[]]$Assignees = @(),
    [string]$Milestone = "",
    [switch]$Draft,
    [switch]$ManualMergeOnly,
    [ValidateSet("merge", "squash", "rebase")]
    [string]$MergeMethod = "squash",
    [switch]$SkipPreflight,
    [switch]$SkipTests,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Command,
        [switch]$CaptureOutput
    )

    if ($CaptureOutput) {
        $result = & $Command[0] $Command[1..($Command.Count - 1)] 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $($Command -join ' ')`n$result"
        }
        return ($result | Out-String).Trim()
    }

    & $Command[0] $Command[1..($Command.Count - 1)]
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $($Command -join ' ')"
    }
    return $null
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message"
}

function Write-WarnLine {
    param([string]$Message)
    Write-Host "[WARN] $Message"
}

function Normalize-RemoteUrl {
    param([string]$RemoteUrl)

    $url = $RemoteUrl.Trim().ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($url)) {
        return ""
    }

    if ($url.StartsWith("git@github.com:")) {
        $url = $url.Replace("git@github.com:", "https://github.com/")
    }
    if ($url.StartsWith("ssh://git@github.com/")) {
        $url = $url.Replace("ssh://git@github.com/", "https://github.com/")
    }
    if ($url.EndsWith(".git")) {
        $url = $url.Substring(0, $url.Length - 4)
    }
    return $url.TrimEnd("/")
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

Write-Info "Repo root: $repoRoot"

if (-not (Test-Path ".git")) {
    throw "Current directory is not a git repository root: $repoRoot"
}

$branch = (Invoke-Checked -Command @("git", "branch", "--show-current") -CaptureOutput).Trim()
if ([string]::IsNullOrWhiteSpace($branch)) {
    throw "Unable to determine current git branch."
}
if ($branch -eq $BaseBranch) {
    throw "Current branch '$branch' matches base branch '$BaseBranch'. Create/use a feature branch before opening PR."
}

$status = (Invoke-Checked -Command @("git", "status", "--porcelain") -CaptureOutput)
if (-not [string]::IsNullOrWhiteSpace($status)) {
    throw "Working tree has uncommitted changes. Commit/stash before running this script."
}

$remoteNames = (Invoke-Checked -Command @("git", "remote") -CaptureOutput) -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }
if ($remoteNames -notcontains $Remote) {
    throw "Remote '$Remote' does not exist. Available remotes: $($remoteNames -join ', ')"
}

$expectedUpstream = "https://github.com/adaptco-main/a2a_mcp"
if ($remoteNames -notcontains "upstream") {
    throw "Required remote 'upstream' is missing. Expected GitHub target: adaptco-main/A2A_MCP"
}
$upstreamRawUrl = (Invoke-Checked -Command @("git", "remote", "get-url", "upstream") -CaptureOutput).Trim()
$upstreamUrl = Normalize-RemoteUrl -RemoteUrl $upstreamRawUrl
if ($upstreamUrl -ne $expectedUpstream) {
    throw "Remote 'upstream' must point to adaptco-main/A2A_MCP. Found '$upstreamRawUrl'."
}

Write-Info "Verifying connectivity to '$Remote'..."
Invoke-Checked -Command @("git", "ls-remote", "--exit-code", $Remote) | Out-Null

Write-Info "Fetching $Remote/$BaseBranch..."
Invoke-Checked -Command @("git", "fetch", $Remote, $BaseBranch) | Out-Null

if (-not $SkipPreflight) {
    $preflightScript = Join-Path $repoRoot "scripts\pre_pr_check.ps1"
    if (Test-Path $preflightScript) {
        Write-Info "Running preflight checks..."
        if ($SkipTests) {
            & $preflightScript -SkipTests
        } else {
            & $preflightScript
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Preflight checks failed."
        }
    } else {
        Write-WarnLine "Preflight script not found at '$preflightScript'. Continuing."
    }
}

Write-Info "Checking GitHub CLI authentication..."
Invoke-Checked -Command @("gh", "auth", "status") | Out-Null
Invoke-Checked -Command @("gh", "repo", "view", $Repo, "--json", "nameWithOwner") | Out-Null

$pushCommand = @("git", "push", "--set-upstream", $Remote, $branch)
if ($DryRun) {
    $pushCommand = @("git", "push", "--dry-run", "--set-upstream", $Remote, $branch)
}

Write-Info "Pushing branch '$branch' to '$Remote'..."
Invoke-Checked -Command $pushCommand | Out-Null

$existingJson = Invoke-Checked -Command @(
    "gh", "pr", "list",
    "--repo", $Repo,
    "--head", $branch,
    "--base", $BaseBranch,
    "--state", "open",
    "--json", "number,url,title"
) -CaptureOutput

$existing = @()
if (-not [string]::IsNullOrWhiteSpace($existingJson)) {
    $existing = $existingJson | ConvertFrom-Json
}

$prUrl = ""
$prNumber = ""

if ($existing.Count -gt 0) {
    $prUrl = $existing[0].url
    $prNumber = [string]$existing[0].number
    Write-Info "Open PR already exists: #$prNumber $prUrl"
} else {
    if ([string]::IsNullOrWhiteSpace($Title)) {
        $Title = (Invoke-Checked -Command @("git", "log", "-1", "--pretty=%s") -CaptureOutput).Trim()
    }
    if ([string]::IsNullOrWhiteSpace($Title)) {
        throw "PR title is empty. Provide -Title or ensure latest commit has a subject."
    }

    $bodyFilePath = ""
    if (-not [string]::IsNullOrWhiteSpace($BodyFile)) {
        $resolved = Resolve-Path $BodyFile -ErrorAction SilentlyContinue
        if (-not $resolved) {
            throw "Body file not found: $BodyFile"
        }
        $bodyFilePath = $resolved.Path
    } elseif (-not [string]::IsNullOrWhiteSpace($Body)) {
        $tempBody = Join-Path $env:TEMP ("pr_body_" + [Guid]::NewGuid().ToString("N") + ".md")
        $Body | Set-Content -Path $tempBody -Encoding UTF8
        $bodyFilePath = $tempBody
    } elseif (Test-Path (Join-Path $repoRoot "PR_BODY.md")) {
        $bodyFilePath = (Resolve-Path (Join-Path $repoRoot "PR_BODY.md")).Path
    }

    $createArgs = @("gh", "pr", "create", "--repo", $Repo, "--base", $BaseBranch, "--head", $branch, "--title", $Title)
    if ($Draft) {
        $createArgs += "--draft"
    }
    if (-not [string]::IsNullOrWhiteSpace($bodyFilePath)) {
        $createArgs += @("--body-file", $bodyFilePath)
    } else {
        $createArgs += "--fill"
    }
    foreach ($label in $Labels) {
        if (-not [string]::IsNullOrWhiteSpace($label)) {
            $createArgs += @("--label", $label)
        }
    }
    foreach ($reviewer in $Reviewers) {
        if (-not [string]::IsNullOrWhiteSpace($reviewer)) {
            $createArgs += @("--reviewer", $reviewer)
        }
    }
    foreach ($assignee in $Assignees) {
        if (-not [string]::IsNullOrWhiteSpace($assignee)) {
            $createArgs += @("--assignee", $assignee)
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($Milestone)) {
        $createArgs += @("--milestone", $Milestone)
    }

    if ($DryRun) {
        Write-Info ("Dry run enabled. Skipping PR creation. Command: " + ($createArgs -join " "))
    } else {
        Write-Info "Creating pull request against '$BaseBranch'..."
        $prUrl = (Invoke-Checked -Command $createArgs -CaptureOutput).Trim()
        if ([string]::IsNullOrWhiteSpace($prUrl)) {
            throw "Failed to capture PR URL from gh pr create."
        }
        $prNumber = (Invoke-Checked -Command @("gh", "pr", "view", $prUrl, "--repo", $Repo, "--json", "number", "-q", ".number") -CaptureOutput).Trim()
    }
}

$autoMergeEnabled = -not $ManualMergeOnly
if ($autoMergeEnabled -and -not $DryRun) {
    if ([string]::IsNullOrWhiteSpace($prNumber)) {
        throw "Cannot enable auto-merge without a PR number."
    }
    Write-Info "Enabling auto-merge ($MergeMethod) on PR #$prNumber..."
    Invoke-Checked -Command @("gh", "pr", "merge", $prNumber, "--repo", $Repo, "--auto", "--$MergeMethod")
} elseif ($ManualMergeOnly) {
    Write-Info "Manual merge mode enabled; auto-merge step skipped."
}

if ($DryRun) {
    Write-Host "[RESULT] Dry run completed for branch '$branch' -> ${Repo}:$BaseBranch."
    exit 0
}

if (-not [string]::IsNullOrWhiteSpace($prUrl)) {
    Write-Host "[RESULT] PR ready: $prUrl"
} else {
    Write-Host "[RESULT] Push completed. PR creation skipped."
}

exit 0
