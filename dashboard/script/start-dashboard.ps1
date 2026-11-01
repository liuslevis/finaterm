# 一键启动金融仪表盘（Windows），桌面和开机启动快捷方式都指向本脚本：
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File <本脚本>
# 让快捷方式指向已签名的 powershell.exe，可避开 Explorer 双击 .cmd 时的“打开文件 - 安全警告”。
# 流程：检查 uv/npm → uv sync → 按需 npm install → 按需启动 Futu OpenD → 隐藏窗口 npm start。
# Futu / usdata 环境缺失只记警告，相关面板不可用，其余照常。日志：%LOCALAPPDATA%\FinanceDashboard\launcher.log
# 在终端里调试时加 -Visible，不隐藏当前控制台。

param([switch]$Visible)

$ErrorActionPreference = 'Stop'

$dashboardRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$financeRoot = Split-Path -Parent $dashboardRoot
$logDir = Join-Path $env:LOCALAPPDATA 'FinanceDashboard'
$logPath = Join-Path $logDir 'launcher.log'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
try { Set-Content -LiteralPath $logPath -Value "[$(Get-Date -Format s)] dashboard: $dashboardRoot" -Encoding UTF8 }
catch {
    # 旧实例可能仍占用日志文件
    $logPath = Join-Path $logDir "launcher-$PID.log"
    Set-Content -LiteralPath $logPath -Value "[$(Get-Date -Format s)] dashboard: $dashboardRoot" -Encoding UTF8
}

function Write-Log([string]$message) {
    Add-Content -LiteralPath $logPath -Value $message -Encoding UTF8
    Write-Host $message
}

function Stop-Launch([string]$message) {
    Write-Log "[错误] $message"
    try {
        $shell = New-Object -ComObject WScript.Shell
        [void]$shell.Popup("$message`r`n`r`n日志：$logPath", 0, '金融数据终端启动失败', 16)
    }
    catch { }
    exit 1
}

function Invoke-Logged([string]$command) {
    # 经 cmd 调用以兼容 npm.cmd，并把输出追加到日志
    & $env:ComSpec /d /c "$command >>`"$logPath`" 2>&1"
    return $LASTEXITCODE
}

function Test-OpenDReady {
    $client = [Net.Sockets.TcpClient]::new()
    try { return $client.ConnectAsync('127.0.0.1', 11111).Wait(500) -and $client.Connected }
    catch { return $false }
    finally { $client.Dispose() }
}

if (-not $Visible) {
    try {
        if (-not ('FinanceConsoleWindow' -as [type])) {
            Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class FinanceConsoleWindow
{
    [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
        }
        [FinanceConsoleWindow]::ShowWindow([FinanceConsoleWindow]::GetConsoleWindow(), 0) | Out-Null
    }
    catch { }
}

Set-Location -LiteralPath $dashboardRoot

foreach ($tool in 'uv', 'npm') {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Stop-Launch "未找到 $tool，请先安装（npm 随 Node.js 安装）并确保它已加入 PATH。"
    }
}

Write-Log '正在检查仪表盘 Python 依赖...'
if ((Invoke-Logged "uv sync --project `"$dashboardRoot`" --quiet") -ne 0) {
    Stop-Launch '仪表盘 Python 依赖安装失败。'
}

if (-not (Test-Path -LiteralPath (Join-Path $dashboardRoot 'node_modules\electron\package.json'))) {
    Write-Log '正在安装 Electron...'
    if ((Invoke-Logged 'npm install --no-audit --no-fund') -ne 0) {
        Stop-Launch 'Electron 安装失败。'
    }
}

$futuRoot = Join-Path $financeRoot 'FutuOpenD'
foreach ($required in (Join-Path $futuRoot '.venv\Scripts\python.exe'),
                      (Join-Path $futuRoot 'skills\futuapi\scripts\quote\get_kline.py'),
                      (Join-Path $financeRoot 'usdata\.venv\Scripts\python.exe')) {
    if (-not (Test-Path -LiteralPath $required)) {
        Write-Log "[警告] 未找到 $required，对应数据面板将不可用。"
    }
}

$openD = @("$env:APPDATA\Futu_OpenD\Futu_OpenD.exe", "$env:LOCALAPPDATA\Futu_OpenD\Futu_OpenD.exe") |
    Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $openD) {
    Write-Log '[警告] 未找到 Futu OpenD（%APPDATA%\Futu_OpenD\Futu_OpenD.exe），富途行情将不可用。'
}
elseif (Test-OpenDReady) {
    Write-Log 'Futu OpenD API 已就绪。'
}
else {
    if (-not (Get-Process -Name 'Futu_OpenD' -ErrorAction SilentlyContinue)) {
        Write-Log '正在启动 Futu OpenD...'
        Start-Process -FilePath $openD
    }
    $ready = $false
    for ($i = 0; $i -lt 30 -and -not $ready; $i++) {
        Start-Sleep -Seconds 1
        $ready = Test-OpenDReady
    }
    if ($ready) { Write-Log 'Futu OpenD API 已就绪。' }
    else { Write-Log '[警告] Futu OpenD 尚未开放 127.0.0.1:11111，请在 OpenD 窗口完成登录；仪表盘继续启动。' }
}

$env:FINANCE_DATA_ROOT = $financeRoot
Write-Log '正在启动金融数据终端...'
Start-Process -FilePath $env:ComSpec -ArgumentList '/d', '/c', 'npm start' -WorkingDirectory $dashboardRoot -WindowStyle Hidden
exit 0