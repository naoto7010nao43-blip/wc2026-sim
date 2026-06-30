param(
    [switch]$SkipBackendTests,
    [switch]$SkipFrontendChecks,
    [switch]$SkipEncodingAudit,
    [switch]$SkipRealResultsAudit,
    [switch]$SkipReleaseReadiness,
    [switch]$SkipGitStatus
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$backendPython = Join-Path $backendDir "venv\Scripts\python.exe"

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Command
    Write-Host "OK: $Name" -ForegroundColor Green
}

Push-Location $repoRoot
try {
    if (-not $SkipGitStatus) {
        Invoke-Step "Git working tree status" {
            $status = git status --short
            if ($status) {
                $status | ForEach-Object { Write-Host $_ }
                throw "Git working tree is not clean."
            }
        }
    }

    if (-not $SkipBackendTests) {
        Invoke-Step "Backend pytest" {
            Push-Location $backendDir
            try {
                & $backendPython -m pytest
            } finally {
                Pop-Location
            }
        }
    }

    if (-not $SkipFrontendChecks) {
        Invoke-Step "Frontend lint" {
            Push-Location $frontendDir
            try {
                npm run lint
            } finally {
                Pop-Location
            }
        }

        Invoke-Step "Frontend build" {
            Push-Location $frontendDir
            try {
                npm run build
            } finally {
                Pop-Location
            }
        }
    }

    if (-not $SkipEncodingAudit) {
        Invoke-Step "Text encoding audit" {
            & $backendPython "backend\scripts\audit_text_encoding.py"
        }
    }

    if (-not $SkipRealResultsAudit) {
        Invoke-Step "Real results integrity audit" {
            & $backendPython "backend\scripts\audit_real_results_integrity.py"
        }
    }

    if (-not $SkipReleaseReadiness) {
        Invoke-Step "Release readiness structural check" {
            & $backendPython "backend\scripts\build_release_readiness_report.py" --check-only --fail-on-blockers
        }
    }

    Write-Host ""
    Write-Host "Pre-release check completed." -ForegroundColor Green
} finally {
    Pop-Location
}
