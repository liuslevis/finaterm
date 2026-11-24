$ErrorActionPreference = "Stop"

$dashboardRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $dashboardRoot ".venv\Scripts\python.exe"
$port = if ($env:FINANCE_DASHBOARD_PORT) { $env:FINANCE_DASHBOARD_PORT } else { "63000" }
$stateDir = Join-Path $env:LOCALAPPDATA "FinanceDashboard"
$logDir = Join-Path $stateDir "logs"
$pidFile = Join-Path $stateDir "dashboard.pid"
$stdoutLog = Join-Path $logDir "dashboard.log"
$stderrLog = Join-Path $logDir "dashboard-error.log"
$healthUrl = "http://127.0.0.1:$port/__finance_dashboard_health"

if (-not (Test-Path $python -PathType Leaf)) {
    throw "Dashboard virtual environment not found. Run 'uv sync' in $dashboardRoot first."
}

New-Item -ItemType Directory -Force -Path $stateDir, $logDir | Out-Null

if (Test-Path $pidFile -PathType Leaf) {
    $existingPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($existingPid -match "^\d+$" -and (Get-Process -Id $existingPid -ErrorAction SilentlyContinue)) {
        Write-Host "Finance dashboard is already running with PID $existingPid."
        exit 0
    }
    Remove-Item $pidFile -Force
}

try {
    $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
    if ($health -eq "finance-dashboard-uv-v2") {
        Write-Host "Finance dashboard is already responding at http://127.0.0.1:$port/."
        exit 0
    }
}
catch {
    $health = $null
}

$portInUse = $false
$portCheck = [Net.Sockets.TcpClient]::new()
try {
    $portCheck.Connect("127.0.0.1", [int]$port)
    $portInUse = $true
}
catch [Net.Sockets.SocketException] {
}
finally {
    $portCheck.Dispose()
}
if ($portInUse) {
    throw "Port $port is already in use by another service."
}

$dashboard = Start-Process `
    -FilePath $python `
    -ArgumentList "dashboard_server.py", "--port", $port, "--no-browser" `
    -WorkingDirectory $dashboardRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WindowStyle Hidden `
    -PassThru
$dashboard.Id | Set-Content $pidFile

for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
        if ($health -eq "finance-dashboard-uv-v2") {
            Write-Host "Finance dashboard started with PID $($dashboard.Id) at http://127.0.0.1:$port/."
            Write-Host "Logs: $stdoutLog and $stderrLog"
            exit 0
        }
    }
    catch {
        $dashboard.Refresh()
        if ($dashboard.HasExited) {
            break
        }
    }
    Start-Sleep -Seconds 1
}

Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
throw "Finance dashboard failed to start. Check $stdoutLog and $stderrLog."
