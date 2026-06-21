$ProjectDir = "C:\Users\naoto\Documents\myclaude.ai.project\wc2026-sim"
$LogDir = Join-Path $ProjectDir "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogDir "daily_maintenance_$Timestamp.log"
$PromptFile = Join-Path $ProjectDir "scripts\daily_maintenance_prompt.txt"
$Prompt = Get-Content -Raw $PromptFile

Set-Location $ProjectDir

& claude -p $Prompt --dangerously-skip-permissions --output-format text *> $LogFile

# Keep only the 30 most recent log files.
Get-ChildItem $LogDir -Filter "daily_maintenance_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 30 | Remove-Item -Force
