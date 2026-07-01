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

function Post-Utf8Json {
    param([string]$Url, [string]$JsonBody)

    $lastError = $null
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $client = [System.Net.Http.HttpClient]::new()
        try {
            $client.Timeout = [TimeSpan]::FromSeconds($TimeoutSec)
            $content = [System.Net.Http.StringContent]::new($JsonBody, [System.Text.Encoding]::UTF8, "application/json")
            $response = $client.PostAsync($Url, $content).GetAwaiter().GetResult()
            $bytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
            $text = [System.Text.Encoding]::UTF8.GetString($bytes)
            if (-not $response.IsSuccessStatusCode) {
                throw "POST $Url returned HTTP $([int]$response.StatusCode): $text"
            }
            return $text
        } catch {
            $lastError = $_
            if ($attempt -eq 3) {
                throw
            }
            Start-Sleep -Seconds (2 * $attempt)
        } finally {
            if ($content) {
                $content.Dispose()
            }
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
Assert-Contains "frontend bundle" $bundleText "lineup-engine-parity"
Assert-Contains "frontend bundle" $bundleText "breakdown"
Assert-Contains "frontend bundle" $bundleText "path-projection"
Assert-Contains "frontend bundle" $bundleText "final-matchups"
Assert-Contains "frontend bundle" $bundleText "dark-horses"
Assert-Contains "frontend bundle" $bundleText "group-advancement"
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

$breakdownJson = Get-Utf8Text "$backend/api/predictions/BRA/ARG/breakdown"
Assert-NoMojibakeMarkers "BRA/ARG matchup breakdown JSON" $breakdownJson
$breakdown = $breakdownJson | ConvertFrom-Json
if ($breakdown.factors.Count -lt 4) {
    throw "Matchup breakdown did not expose at least 4 factors"
}
if ($breakdown.lineups.Count -ne 2) {
    throw "Matchup breakdown did not expose two lineup summaries"
}
Assert-HasJapanese "BRA/ARG matchup breakdown summary" $breakdown.summary_ja

$upsetWatchJson = Get-Utf8Text "$backend/api/tournament/upset-watch"
Assert-NoMojibakeMarkers "tournament upset watch JSON" $upsetWatchJson
$upsetWatch = $upsetWatchJson | ConvertFrom-Json
if ($upsetWatch.match_count -ne 72) {
    throw "Tournament upset watch match_count is unexpected: $($upsetWatch.match_count)"
}
if ($upsetWatch.candidates.Count -lt 8) {
    throw "Tournament upset watch returned too few candidates: $($upsetWatch.candidates.Count)"
}
if (-not $upsetWatch.model_version -or $upsetWatch.model_version -notmatch "^poisson-v") {
    throw "Tournament upset watch model_version is unexpected: $($upsetWatch.model_version)"
}
Assert-HasJapanese "tournament upset watch reason" (($upsetWatch.candidates | Select-Object -First 3 | ForEach-Object { $_.reason_ja }) -join " ")

$groupDifficultyJson = Get-Utf8Text "$backend/api/tournament/group-difficulty"
Assert-NoMojibakeMarkers "tournament group difficulty JSON" $groupDifficultyJson
$groupDifficulty = $groupDifficultyJson | ConvertFrom-Json
if ($groupDifficulty.group_count -ne 12) {
    throw "Tournament group difficulty group_count is unexpected: $($groupDifficulty.group_count)"
}
if ($groupDifficulty.groups.Count -ne 12) {
    throw "Tournament group difficulty did not expose all groups: $($groupDifficulty.groups.Count)"
}
if (-not $groupDifficulty.model_version -or $groupDifficulty.model_version -notmatch "^poisson-v") {
    throw "Tournament group difficulty model_version is unexpected: $($groupDifficulty.model_version)"
}
Assert-HasJapanese "tournament group difficulty reason" (($groupDifficulty.groups | Select-Object -First 3 | ForEach-Object { $_.reason_ja }) -join " ")

$pathProjectionJson = Get-Utf8Text "$backend/api/tournament/path-projection?team_id=JPN&iterations=100"
Assert-NoMojibakeMarkers "tournament path projection JSON" $pathProjectionJson
$pathProjection = $pathProjectionJson | ConvertFrom-Json
if ($pathProjection.team_id -ne "JPN") {
    throw "Tournament path projection team_id is unexpected: $($pathProjection.team_id)"
}
if ($pathProjection.stages.Count -ne 5) {
    throw "Tournament path projection did not expose all knockout stages: $($pathProjection.stages.Count)"
}
if (-not $pathProjection.model_version -or $pathProjection.model_version -notmatch "^poisson-v") {
    throw "Tournament path projection model_version is unexpected: $($pathProjection.model_version)"
}
Assert-HasJapanese "tournament path projection note" $pathProjection.note_ja

$finalMatchupsJson = Get-Utf8Text "$backend/api/tournament/final-matchups?iterations=100&limit=4"
Assert-NoMojibakeMarkers "tournament final matchups JSON" $finalMatchupsJson
$finalMatchups = $finalMatchupsJson | ConvertFrom-Json
if ($finalMatchups.candidates.Count -lt 1) {
    throw "Tournament final matchups did not expose any candidates"
}
if (-not $finalMatchups.model_version -or $finalMatchups.model_version -notmatch "^poisson-v") {
    throw "Tournament final matchups model_version is unexpected: $($finalMatchups.model_version)"
}
Assert-HasJapanese "tournament final matchups note" $finalMatchups.note_ja

$darkHorsesJson = Get-Utf8Text "$backend/api/tournament/dark-horses?iterations=100&limit=4"
Assert-NoMojibakeMarkers "tournament dark horses JSON" $darkHorsesJson
$darkHorses = $darkHorsesJson | ConvertFrom-Json
if ($darkHorses.candidates.Count -lt 1) {
    throw "Tournament dark horses did not expose any candidates"
}
if (-not $darkHorses.model_version -or $darkHorses.model_version -notmatch "^poisson-v") {
    throw "Tournament dark horses model_version is unexpected: $($darkHorses.model_version)"
}
Assert-HasJapanese "tournament dark horses note" $darkHorses.note_ja
Assert-HasJapanese "tournament dark horses reason" (($darkHorses.candidates | Select-Object -First 3 | ForEach-Object { $_.reason_ja }) -join " ")

$groupAdvancementJson = Get-Utf8Text "$backend/api/tournament/group-advancement?iterations=100"
Assert-NoMojibakeMarkers "tournament group advancement JSON" $groupAdvancementJson
$groupAdvancement = $groupAdvancementJson | ConvertFrom-Json
if ($groupAdvancement.groups.Count -ne 12) {
    throw "Tournament group advancement did not expose all groups: $($groupAdvancement.groups.Count)"
}
if (-not $groupAdvancement.model_version -or $groupAdvancement.model_version -notmatch "^poisson-v") {
    throw "Tournament group advancement model_version is unexpected: $($groupAdvancement.model_version)"
}
Assert-HasJapanese "tournament group advancement note" $groupAdvancement.note_ja

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

$lineupParityJson = Get-Utf8Text "$backend/api/model-diagnostics/lineup-engine-parity"
Assert-NoMojibakeMarkers "lineup engine parity JSON" $lineupParityJson
$lineupParity = $lineupParityJson | ConvertFrom-Json
if ($lineupParity.teamCount -ne 48) {
    throw "Lineup engine parity audit teamCount is unexpected: $($lineupParity.teamCount)"
}
if ($lineupParity.mismatchTeamCount -ne 0) {
    throw "Lineup engine parity audit still has mismatched teams: $($lineupParity.mismatchTeamCount)"
}
if ($lineupParity.incompleteSimulatedLineupTeamCount -ne 0) {
    throw "Lineup engine parity audit still has incomplete simulated XIs: $($lineupParity.incompleteSimulatedLineupTeamCount)"
}
Assert-HasJapanese "lineup engine parity note" $lineupParity.note

$japanLineupJson = Get-Utf8Text "$backend/api/teams/JPN/likely-lineup"
Assert-NoMojibakeMarkers "Japan likely lineup JSON" $japanLineupJson
$japanLineup = $japanLineupJson | ConvertFrom-Json
$japanLineupIds = @($japanLineup.lineup | ForEach-Object { $_.player_id })
if ($japanLineupIds -notcontains "JPN_NAKAMURA_K") {
    throw "Japan likely lineup does not include EA-sourced Keito Nakamura"
}
Assert-HasJapanese "Japan likely lineup player names" (($japanLineup.lineup | ForEach-Object { $_.name_ja }) -join " ")

$japanBrazilMatchJson = Post-Utf8Json "$backend/api/matches/simulate" '{"home_team_id":"JPN","away_team_id":"BRA","seed":20260701,"allow_draw":true}'
Assert-NoMojibakeMarkers "Japan/Brazil simulated match JSON" $japanBrazilMatchJson
$japanBrazilMatch = $japanBrazilMatchJson | ConvertFrom-Json
$japanBrazilHomeLineupIds = @($japanBrazilMatch.home_lineup | ForEach-Object { $_.player_id })
if ($japanBrazilHomeLineupIds -notcontains "JPN_NAKAMURA_K") {
    throw "Japan/Brazil simulated match did not field Keito Nakamura despite the likely-lineup correction"
}
if ($japanBrazilMatch.home_lineup.Count -ne 11 -or $japanBrazilMatch.away_lineup.Count -ne 11) {
    throw "Japan/Brazil simulated match did not return two full starting XIs"
}
Write-Host "OK: backend JSON is UTF-8 and exposes current prediction/team/data-quality fields" -ForegroundColor Green

Write-Host ""
Write-Host "Post-deploy content smoke completed." -ForegroundColor Green
