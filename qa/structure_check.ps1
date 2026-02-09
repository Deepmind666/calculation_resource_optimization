param()

$ErrorActionPreference = "Stop"

$requiredDirs = @(
    "prior_art",
    "spec",
    "prototype",
    "patent",
    "figures",
    "qa",
    "logs"
)

$requiredFiles = @(
    "AGENTS.md",
    ".claude.md",
    ".gitignore",
    "README.md",
    "RUNBOOK.md",
    "gptdeepsearch2_9.md",
    "logs/work_progress.md",
    "prior_art/README.md",
    "spec/README.md",
    "prototype/README.md",
    "patent/README.md",
    "figures/README.md",
    "qa/README.md",
    "qa/review_checklist.md"
)

$missing = @()

foreach ($d in $requiredDirs) {
    if (-not (Test-Path -Path $d -PathType Container)) {
        $missing += $d
    }
}

foreach ($f in $requiredFiles) {
    if (-not (Test-Path -Path $f -PathType Leaf)) {
        $missing += $f
    }
}

$logPath = "logs/work_progress.md"
$logHasTimestamp = $false
if (Test-Path $logPath) {
    $content = Get-Content -Raw $logPath
    $logHasTimestamp = $content -match "20\d\d-\d\d-\d\d \d\d:\d\d:\d\d"
}

Write-Host "=== Structure Check ==="
Write-Host "Working directory: $(Get-Location)"

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "Missing required paths:"
    $missing | ForEach-Object { Write-Host " - $_" }
    exit 1
}

if (-not $logHasTimestamp) {
    Write-Host ""
    Write-Host "Log file exists but no timestamp entry found in logs/work_progress.md"
    exit 1
}

Write-Host ""
Write-Host "All required directories/files exist."
Write-Host "Progress log includes timestamp entries."
Write-Host "Status: PASS"
exit 0
