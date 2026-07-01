param(
    [string]$FrontendBaseUrl = "https://wc2026-sim-ten.vercel.app",
    [string]$BackendBaseUrl = "https://wc2026-backend-tdih.onrender.com",
    [int]$TimeoutSec = 45
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Net.Http

function Get-Utf8Text {
    param([string]$Url)

    $lastError = $null
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $client = [System.Net.Http.HttpClient]::new()
        try {
            $client.Timeout = [TimeSpan]::FromSeconds($TimeoutSec)
            $bytes = $client.GetByteArrayAsync($Url).GetAwaiter().GetResult()
            return [System.Text.Encoding]::UTF8.GetString($bytes)
        } catch {
            $lastError = $_
            if ($attempt -eq 3) {
                throw
            }
            Start-Sleep -Seconds (2 * $attempt)
        } finally {
            $client.Dispose()
        }
    }

    throw $lastError
}

function Resolve-Url {
    param([string]$BaseUrl, [string]$Path)
    return ([System.Uri]::new([System.Uri]::new($BaseUrl.TrimEnd("/") + "/"), $Path)).AbsoluteUri
}

function Assert-Contains {
    param([string]$Name, [string]$Text, [string]$Needle)
    if (-not $Text.Contains($Needle)) {
        throw "$Name did not contain expected marker: $Needle"
    }
}

function Assert-NoMojibakeMarkers {
    param([string]$Name, [string]$Text)
    $markers = @(
        [char]0x00C3, # common UTF-8-as-Latin-1 marker
        [char]0x00E3, # common Japanese UTF-8-as-Latin-1 marker
        [char]0x7E67, # common Shift_JIS mojibake marker
        [char]0x7E3A, # common Shift_JIS mojibake marker
        [char]0x8B41, # common Shift_JIS mojibake marker
        [char]0xFFFD  # Unicode replacement character
    )
    foreach ($marker in $markers) {
        if ($Text.Contains([string]$marker)) {
            throw "$Name contains a likely mojibake marker: $marker"
        }
    }
}

function Assert-HasJapanese {
    param([string]$Name, [string]$Text)
    if ($Text -notmatch "[\u3040-\u30ff\u3400-\u9fff]") {
        throw "$Name does not contain Japanese text"
    }
}

$frontend = $FrontendBaseUrl.TrimEnd("/")
$backend = $BackendBaseUrl.TrimEnd("/")

Write-Host "==> Frontend bundle content" -ForegroundColor Cyan
$html = Get-Utf8Text "$frontend/"
$scriptMatches = [regex]::Matches($html, 'src="([^"]+\.js)"')
if ($scriptMatches.Count -lt 1) {
    throw "Frontend HTML did not reference a JavaScript bundle"
}

$bundleText = ""
foreach ($match in $scriptMatches) {
    $scriptUrl = Resolve-Url $frontend $match.Groups[1].Value
    $bundleText += "`n" + (Get-Utf8Text $scriptUrl)
}

Assert-Contains "frontend bundle" $bundleText "poisson-model"
Assert-Contains "frontend bundle" $bundleText "home_possession_pct"
Assert-Contains "frontend bundle" $bundleText "manager_name"
Assert-Contains "frontend bundle" $bundleText "data_source"
Assert-Contains "frontend bundle" $bundleText "nonBlockingWarnings"
Assert-Contains "frontend bundle" $bundleText "substitution-profile-candidates"
Assert-Contains "frontend bundle" $bundleText "player-rating-diff"
Assert-Contains "frontend bundle" $bundleText "formation-position-fit"
Write-Host "OK: frontend bundle includes latest match-detail/data markers" -ForegroundColor Green

Write-Host "==> Backend UTF-8 JSON content" -ForegroundColor Cyan
$teamJson = Get-Utf8Text "$backend/api/teams/BRA"
Assert-NoMojibakeMarkers "BRA team JSON" $teamJson
$team = $teamJson | ConvertFrom-Json
if ($team.players.Count -lt 11) {
    throw "BRA team JSON returned fewer than 11 players"
}
if (-not $team.tactical_profile.manager_name) {
    throw "BRA team JSON is missing tactical_profile.manager_name"
}
Assert-HasJapanese "BRA player names" (($team.players | Select-Object -First 8 | ForEach-Object { $_.name_ja }) -join " ")

$predictionJson = Get-Utf8Text "$backend/api/predictions/BRA/ARG"
Assert-NoMojibakeMarkers "BRA/ARG prediction JSON" $predictionJson
$prediction = $predictionJson | ConvertFrom-Json
if ($prediction.model_version -notmatch "^poisson-v") {
    throw "Prediction model_version is unexpected: $($prediction.model_version)"
}
Assert-HasJapanese "BRA/ARG prediction explanation" (($prediction.explanation | ForEach-Object { $_ }) -join " ")

$dataQualityJson = Get-Utf8Text "$backend/api/data-quality/summary"
Assert-NoMojibakeMarkers "data quality JSON" $dataQualityJson
$dataQuality = $dataQualityJson | ConvertFrom-Json
if ($dataQuality.real_group_match_expected -ne 72) {
    throw "Data quality real_group_match_expected is unexpected: $($dataQuality.real_group_match_expected)"
}
if ($dataQuality.real_group_match_count -ne $dataQuality.real_group_match_expected) {
    throw "Data quality real group coverage is incomplete: $($dataQuality.real_group_match_count)/$($dataQuality.real_group_match_expected)"
}
if ($dataQuality.real_group_match_coverage_pct -ne 100.0) {
    throw "Data quality real_group_match_coverage_pct is unexpected: $($dataQuality.real_group_match_coverage_pct)"
}
if ($dataQuality.real_knockout_match_count -lt 0) {
    throw "Data quality real_knockout_match_count is invalid: $($dataQuality.real_knockout_match_count)"
}
$allowedFreshnessStatus = @("ok", "warning", "critical")
if ($allowedFreshnessStatus -notcontains [string]$dataQuality.freshness_status) {
    throw "Data quality freshness_status is unexpected: $($dataQuality.freshness_status)"
}
if ($null -eq $dataQuality.freshness_critical_count -or $null -eq $dataQuality.freshness_warning_count) {
    throw "Data quality freshness counts are missing"
}

$releaseReadinessJson = Get-Utf8Text "$backend/api/model-diagnostics/release-readiness"
Assert-NoMojibakeMarkers "release readiness JSON" $releaseReadinessJson
$releaseReadiness = $releaseReadinessJson | ConvertFrom-Json
if ($releaseReadiness.readyForManualPush -ne $true) {
    throw "Release readiness is not readyForManualPush=true"
}
if ($releaseReadiness.blockers.Count -ne 0) {
    throw "Release readiness still reports blockers: $($releaseReadiness.blockers -join '; ')"
}
if (($releaseReadiness.PSObject.Properties.Name -notcontains "nonBlockingWarnings")) {
    throw "Release readiness JSON is missing nonBlockingWarnings"
}
if ($releaseReadiness.nonBlockingWarnings.Count -gt 0) {
    Assert-HasJapanese "release readiness warnings" (($releaseReadiness.nonBlockingWarnings | ForEach-Object { $_ }) -join " ")
}

$substitutionQueueJson = Get-Utf8Text "$backend/api/model-diagnostics/substitution-profile-candidates"
Assert-NoMojibakeMarkers "substitution profile candidate JSON" $substitutionQueueJson
$substitutionQueue = $substitutionQueueJson | ConvertFrom-Json
if ($substitutionQueue.candidateCount -lt 1) {
    throw "Substitution profile candidate queue did not expose any candidates"
}
if ($substitutionQueue.readyTeamCount -lt 1) {
    throw "Substitution profile candidate queue did not expose any review-ready teams"
}
Assert-HasJapanese "substitution profile candidate note" $substitutionQueue.note

$playerRatingDiffJson = Get-Utf8Text "$backend/api/model-diagnostics/player-rating-diff"
Assert-NoMojibakeMarkers "player rating diff JSON" $playerRatingDiffJson
$playerRatingDiff = $playerRatingDiffJson | ConvertFrom-Json
if ($playerRatingDiff.totalPlayers -lt 1) {
    throw "Player rating diff did not expose any players"
}
if ($playerRatingDiff.changedByManualOverride -notcontains "JPN_NAKAMURA_K") {
    throw "Player rating diff does not include EA-sourced Keito Nakamura in manual override audit"
}
if ($playerRatingDiff.lowConfidencePlayerCount -ne 0) {
    throw "Player rating diff still has low confidence players: $($playerRatingDiff.lowConfidencePlayerCount)"
}
Assert-HasJapanese "player rating diff note" $playerRatingDiff.note

$formationFitJson = Get-Utf8Text "$backend/api/model-diagnostics/formation-position-fit"
Assert-NoMojibakeMarkers "formation position fit JSON" $formationFitJson
$formationFit = $formationFitJson | ConvertFrom-Json
if ($formationFit.teamCount -ne 48) {
    throw "Formation position fit audit teamCount is unexpected: $($formationFit.teamCount)"
}
if ($formationFit.highSeverityTeamCount -lt 1) {
    throw "Formation position fit audit did not expose any high-severity review teams"
}
if ($formationFit.outOfPositionAssignmentCount -lt 1) {
    throw "Formation position fit audit did not expose any position-fit findings"
}
Assert-HasJapanese "formation position fit note" $formationFit.note

$japanLineupJson = Get-Utf8Text "$backend/api/teams/JPN/likely-lineup"
Assert-NoMojibakeMarkers "Japan likely lineup JSON" $japanLineupJson
$japanLineup = $japanLineupJson | ConvertFrom-Json
$japanLineupIds = @($japanLineup.lineup | ForEach-Object { $_.player_id })
if ($japanLineupIds -notcontains "JPN_NAKAMURA_K") {
    throw "Japan likely lineup does not include EA-sourced Keito Nakamura"
}
Assert-HasJapanese "Japan likely lineup player names" (($japanLineup.lineup | ForEach-Object { $_.name_ja }) -join " ")
Write-Host "OK: backend JSON is UTF-8 and exposes current prediction/team/data-quality fields" -ForegroundColor Green

Write-Host ""
Write-Host "Post-deploy content smoke completed." -ForegroundColor Green
