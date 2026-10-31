param(
    [int]$MaxHours = 8,
    [string]$BiliRoot = "C:\Users\david\dev\deepfind-rag\video\bili",
    [string]$AppDir = "C:\Users\david\dev\finance\predictor\bb_qqq"
)

$ErrorActionPreference = 'Continue'
$priority = Get-Content (Join-Path $BiliRoot ".listing\surveillance-priority.json") -Raw -Encoding utf8 | ConvertFrom-Json
$target = @($priority).Count
$deadline = (Get-Date).AddHours($MaxHours)

function Get-DoneCount {
    param($rows)
    ($rows | Where-Object { Test-Path (Join-Path $BiliRoot "$($_.bvid)\text\$($_.bvid).txt") }).Count
}

Write-Host "waiting for all $target transcripts, cap $MaxHours h"
while ((Get-Date) -lt $deadline) {
    $done = Get-DoneCount $priority
    Write-Host ("[{0}] transcripts: {1}/{2}" -f (Get-Date -Format 'HH:mm:ss'), $done, $target)
    if ($done -ge $target) { break }
    Start-Sleep -Seconds 600
}

Write-Host "starting full pipeline at $(Get-Date -Format 'HH:mm:ss')"
Set-Location $AppDir
& (Join-Path $AppDir "run_pipeline.ps1") *> (Join-Path $AppDir "reports\pipeline_all.log")
Write-Host "pipeline done, running quality checks"

python selftest.py --panel data/panel_brief.csv --reps 200 *> reports\selftest.log
python llm_noise_test.py --episodes 6 *> reports\noise.log
Write-Host "ALL DONE at $(Get-Date -Format 'HH:mm:ss')"
