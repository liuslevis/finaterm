param(
    [switch]$SkipLLM
)

$ErrorActionPreference = 'Continue'
$here = "C:\Users\david\dev\finance\predictor\bb_qqq"
Set-Location $here

Write-Host "=== 1/7 universe ==="
python build_universe.py

if (-not $SkipLLM) {
    Write-Host "=== 2/7 briefs ==="
    python make_brief.py

    Write-Host "=== 3/7 llm score: brief ==="
    python llm_score.py --input brief --repeats 2
    Write-Host "=== 4/7 llm score: brief blind ==="
    python llm_score.py --input brief --blind --repeats 2
    Write-Host "=== 5/7 llm score: full ==="
    python llm_score.py --input full
    Write-Host "=== 6/7 llm score: full blind ==="
    python llm_score.py --input full --blind
}

Write-Host "=== 7/7 lexicon baseline ==="
python baseline.py

$variants = @(
    @{ name = 'brief';       scores = 'data/llm_scores_deepseek_brief_r2.csv' },
    @{ name = 'brief_blind'; scores = 'data/llm_scores_deepseek_brief_blind_r2.csv' },
    @{ name = 'full';        scores = 'data/llm_scores_deepseek_full.csv' },
    @{ name = 'full_blind';  scores = 'data/llm_scores_deepseek_full_blind.csv' }
)

foreach ($v in $variants) {
    if (-not (Test-Path $v.scores)) { Write-Host "skip $($v.name) (no scores)"; continue }
    Write-Host "=== panel/eval: $($v.name) ==="
    python build_panel.py --scores $v.scores --out "data/panel_$($v.name).csv"
    python evaluate.py --panel "data/panel_$($v.name).csv" --out "reports/metrics_$($v.name).json"
}

python report.py
Write-Host "=== PIPELINE DONE ==="

