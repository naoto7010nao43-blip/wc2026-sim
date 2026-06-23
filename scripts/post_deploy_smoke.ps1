param(
    [string]$FrontendBaseUrl = "https://wc2026-sim-ten.vercel.app",
    [string]$BackendBaseUrl = "",
    [int]$TimeoutSec = 20
)

$ErrorActionPreference = "Stop"

function Invoke-UrlCheck {
    param(
        [string]$Name,
        [string]$Url,
        [int[]]$AllowedStatus = @(200)
    )

    Write-Host "==> $Name" -ForegroundColor Cyan
    Write-Host $Url
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec $TimeoutSec
    if ($AllowedStatus -notcontains [int]$response.StatusCode) {
        throw "$Name returned HTTP $($response.StatusCode), expected one of: $($AllowedStatus -join ', ')"
    }
    Write-Host "OK: HTTP $($response.StatusCode)" -ForegroundColor Green
}

$frontend = $FrontendBaseUrl.TrimEnd("/")
$backend = $BackendBaseUrl.TrimEnd("/")

Invoke-UrlCheck "Frontend home" "$frontend/"
Invoke-UrlCheck "Frontend tournament" "$frontend/tournament"
Invoke-UrlCheck "Frontend simulator" "$frontend/simulate"
Invoke-UrlCheck "Frontend teams" "$frontend/teams"
Invoke-UrlCheck "Frontend data review" "$frontend/data-review"

if ($backend -ne "") {
    Invoke-UrlCheck "Backend health" "$backend/api/health"
    Invoke-UrlCheck "Backend teams" "$backend/api/teams"
    Invoke-UrlCheck "Backend data quality" "$backend/api/data-quality/summary"
    Invoke-UrlCheck "Backend team review diagnostics" "$backend/api/model-diagnostics/team-review"
    Invoke-UrlCheck "Backend squad gap diagnostics" "$backend/api/model-diagnostics/squad-gaps"
} else {
    Write-Host ""
    Write-Host "BackendBaseUrl not provided; skipped backend checks." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Post-deploy smoke completed." -ForegroundColor Green

