# 无窗口启动金融仪表盘。
# 存在的原因：Explorer 双击 .cmd 时会先做“发布者验证”，弹出
# “打开文件 - 安全警告 / 无法验证发布者 / 运行(R)”。
# 这里让快捷方式指向已签名的 powershell.exe，再由 PowerShell 去调用 .cmd，
# Explorer 就不会再校验那个 .cmd；控制台窗口同时被隐藏。
# 与 skip-xhs.lnk 的做法一致（PowerShell 隐藏控制台）。

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$cmdPath = Join-Path $root '打开金融仪表盘.cmd'
$logDir = Join-Path $env:LOCALAPPDATA 'FinanceDashboard'
$logPath = Join-Path $logDir 'launcher.log'

function Show-Failure([string]$message) {
    try {
        $shell = New-Object -ComObject WScript.Shell
        [void]$shell.Popup($message, 0, '金融数据终端启动失败', 16)
    }
    catch { }
}

if (-not (Test-Path -LiteralPath $cmdPath)) {
    Show-Failure "找不到启动脚本：`r`n$cmdPath"
    exit 1
}

# 隐藏属于自己的控制台窗口（第一次调用会编译一小段 P/Invoke）。
try {
    if (-not ('FinanceConsoleWindow' -as [type])) {
        Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class FinanceConsoleWindow
{
    [DllImport("kernel32.dll")]
    public static extern IntPtr GetConsoleWindow();

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
'@
    }
    [FinanceConsoleWindow]::ShowWindow([FinanceConsoleWindow]::GetConsoleWindow(), 0) | Out-Null
}
catch { }

try {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}
catch { }

# <nul 让批处理里的 pause 立即返回，避免隐藏窗口后永久挂起。
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = Join-Path $env:SystemRoot 'System32\cmd.exe'
$psi.Arguments = '/d /c ""{0}" <nul >"{1}" 2>&1"' -f $cmdPath, $logPath
$psi.WorkingDirectory = $root
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden

$process = [System.Diagnostics.Process]::Start($psi)
$process.WaitForExit()

if ($process.ExitCode -ne 0) {
    $tail = ''
    if (Test-Path -LiteralPath $logPath) {
        $tail = (Get-Content -LiteralPath $logPath -Encoding UTF8 -Tail 25) -join "`r`n"
    }
    Show-Failure ("启动失败（退出码 {0}）。`r`n`r`n日志：{1}`r`n`r`n{2}" -f $process.ExitCode, $logPath, $tail)
    exit $process.ExitCode
}

exit 0
