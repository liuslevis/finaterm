param(
    [int]$MaxHours = 6,
    [string]$BiliRoot = "C:\Users\david\dev\deepfind-rag\video\bili",
    [string]$AppDir = "C:\Users\david\dev\finance\predictor\bb_qqq"
)

$ErrorActionPreference = 'Continue'
$priority = Get-Content (Join-Path $BiliRoot ".listing\surveillance-priority.json") -Raw -Encoding utf8 | ConvertFrom-Json
$october = @($priority | Where-Object { $_.showDate -like '2026-10-*' })
$deadline = (Get-Date).AddHours($MaxHours)

function Get-DoneCount {
    param($rows)
    ($rows | Where-Object { Test-Path (Join-Path $BiliRoot "$($_.bvid)\text\$($_.bvid).txt") }).Count
}

Write-Host "waiting for $($october.Count) October transcripts, cap $MaxHours h"
while ((Get-Date) -lt $deadline) {
    $done = Get-DoneCount $october
    Write-Host ("[{0}] october transcripts: {1}/{2}" -f (Get-Date -Format 'HH:mm:ss'), $done, $october.Count)
    if ($done -ge $october.Count) { break }
    Start-Sleep -Seconds 300
}

Write-Host "starting pipeline at $(Get-Date -Format 'HH:mm:ss')"
Set-Location $AppDir
& (Join-Path $AppDir "run_pipeline.ps1") *> (Join-Path $AppDir "reports\pipeline.log")
Write-Host "PIPELINE FINISHED"
