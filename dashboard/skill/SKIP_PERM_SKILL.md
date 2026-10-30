---
name: skip-perm
description: 让 Windows 桌面快捷方式做到“双击直接运行、不再弹权限提示”。用户说打开还要点“允许 / 运行 / 是”，或遇到“打开文件 - 安全警告”“无法验证发布者”“Windows 已保护你的电脑”，或要求静默启动、别弹黑窗口时使用。
---

# 跳过快捷方式的权限 / 安全提示

目标：双击桌面 `.lnk` → 程序直接起来，不弹确认框、不闪黑窗口。

## 1. 先判型，别直接改

三种弹窗长得像，根因完全不同，改错方向会白折腾：

| 弹窗 | 关键特征 | 根因 | 处理 |
|---|---|---|---|
| 「打开文件 - 安全警告」 | 按钮 **运行(R)**，正文列「名称 / 发行商 / 类型 / 发送方」 | Explorer 执行**脚本文件**前的发布者校验 | §2 |
| UAC | 蓝底「你要允许此应用对你的设备进行更改吗?」，按钮 **是 / 否** | 目标要求提权 | §3.1 |
| SmartScreen | 「Windows 已保护你的电脑」，要先点「更多信息」再「仍要运行」 | exe 带 MOTW 且无信誉 | §3.2 |

**判型方法**：弹窗出现时**不要关**，直接读窗口，别靠截图猜。

```powershell
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices;
public class DlgProbe {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc cb, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
  public static string T(IntPtr h){ var s=new StringBuilder(1024); GetWindowTextW(h,s,1024); return s.ToString(); }
  public static string C(IntPtr h){ var s=new StringBuilder(256); GetClassNameW(h,s,256); return s.ToString(); }
}
'@
$cb = [DlgProbe+EnumProc]{
  param($h,$l)
  if ([DlgProbe]::IsWindowVisible($h) -and [DlgProbe]::C($h) -eq '#32770') {
    $procId = 0
    [void][DlgProbe]::GetWindowThreadProcessId($h,[ref]$procId)
    $pname = (Get-Process -Id $procId -ErrorAction SilentlyContinue).ProcessName
    # 回调里不能用管道输出，必须 Write-Host
    Write-Host ("DIALOG pid={0} ({1}) title='{2}'" -f $procId, $pname, [DlgProbe]::T($h))
    $child = [DlgProbe+EnumProc]{
      param($c,$x)
      $text = [DlgProbe]::T($c)
      if ($text) { Write-Host ("   [{0}] {1}" -f [DlgProbe]::C($c), $text) }
      return $true
    }
    [void][DlgProbe]::EnumChildWindows($h,$child,[IntPtr]::Zero)
  }
  return $true
}
[void][DlgProbe]::EnumWindows($cb,[IntPtr]::Zero)
```

读出来能同时看到三件事：弹窗由谁托管、说的是哪个文件、按钮是「运行」还是「是」——据此对照上表选分支。

## 2. 「无法验证发布者」型：让 Explorer 别直接执行脚本

### 2.1 原理

`.lnk` 指向 `.cmd` / `.bat` / `.ps1` 时，双击是 **Explorer 自己**去 `ShellExecute` 那个脚本文件，
Shell 会对无签名的脚本做一次发布者校验，于是弹「运行(R)」。

只要让 Explorer 执行的是**微软已签名**的 `powershell.exe`（或 `cmd.exe`），把原脚本降级成它的
参数/子进程，校验就不会发生。这就是 `skip-xhs.lnk` 不弹、而 `打开金融仪表盘.lnk` 弹的原因。

### 2.2 三步落地

1. 写一个隐藏控制台的启动器（模板见 2.3）。
2. 把 `.lnk` 的目标从脚本改成 `powershell.exe`，参数传启动器。
3. 先备份旧 `.lnk`，再改。

```powershell
$lnk   = 'C:\Users\<user>\Desktop\某快捷方式.lnk'
$launcher = 'C:\path\to\start-xxx.ps1'

Copy-Item -LiteralPath $lnk -Destination "$launcher.bak.lnk" -Force   # 先备份

$sh = New-Object -ComObject WScript.Shell
$s  = $sh.CreateShortcut($lnk)
$s.TargetPath       = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$s.Arguments        = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $launcher + '"'
$s.WorkingDirectory = Split-Path -Parent $launcher
$s.Save()

$check = $sh.CreateShortcut($lnk)
$check.TargetPath; $check.Arguments       # 读回确认
```

### 2.3 启动器模板

```powershell
$ErrorActionPreference = 'Stop'
$root    = Split-Path -Parent $MyInvocation.MyCommand.Path
$payload = Join-Path $root '原来的脚本.cmd'          # 改成真正的目标
$logDir  = Join-Path $env:LOCALAPPDATA 'MyLauncher'
$logPath = Join-Path $logDir 'launcher.log'

function Show-Failure([string]$m) {
    try { [void](New-Object -ComObject WScript.Shell).Popup($m, 0, '启动失败', 16) } catch { }
}

if (-not (Test-Path -LiteralPath $payload)) { Show-Failure "找不到：$payload"; exit 1 }

# 隐藏自己的控制台（第一次会编译一小段 P/Invoke）
try {
    if (-not ('MyConsole' -as [type])) {
        Add-Type @'
using System; using System.Runtime.InteropServices;
public static class MyConsole {
  [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
}
'@
    }
    [MyConsole]::ShowWindow([MyConsole]::GetConsoleWindow(), 0) | Out-Null
} catch { }

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# <nul 让脚本里的 pause 立即返回，否则隐藏窗口后会永久挂起
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName        = Join-Path $env:SystemRoot 'System32\cmd.exe'
$psi.Arguments       = '/d /c ""{0}" <nul >"{1}" 2>&1"' -f $payload, $logPath
$psi.WorkingDirectory = $root
$psi.UseShellExecute  = $false
$psi.CreateNoWindow   = $true
$psi.WindowStyle      = [System.Diagnostics.ProcessWindowStyle]::Hidden

$p = [System.Diagnostics.Process]::Start($psi)
$p.WaitForExit()

if ($p.ExitCode -ne 0) {
    $tail = if (Test-Path -LiteralPath $logPath) {
        (Get-Content -LiteralPath $logPath -Encoding UTF8 -Tail 25) -join "`r`n"
    } else { '' }
    Show-Failure ("启动失败（退出码 {0}）。`r`n`r`n日志：{1}`r`n`r`n{2}" -f $p.ExitCode, $logPath, $tail)
    exit $p.ExitCode
}
```

### 2.4 五个必须的细节

1. `-ExecutionPolicy Bypass`：否则策略是 `RemoteSigned` / `AllSigned` 时会拦 `.ps1`。
2. `-WindowStyle Hidden` **+** `ShowWindow(GetConsoleWindow(),0)`：双保险，前者挡启动瞬间的闪窗。
3. `<nul`：脚本里的 `pause` 从 stdin 读到 EOF 立即返回，不会把隐藏窗口挂死。
4. 启动器 `.ps1` 存成 **UTF-8 with BOM**。Windows PowerShell 5.1 无 BOM 时按 ANSI 解码，
   含中文路径的脚本会变成乱码路径、直接报“找不到”。
5. `cmd /c` 的三层引号要写对：`/d /c ""{0}" <nul >"{1}" 2>&1"`（外层一对、路径各一对）。

**更简单的替代**：快捷方式直接指 `cmd.exe`、参数 `/c "脚本路径"`。一样能绕过校验，但会闪一下黑窗，
且脚本里的 `pause` 会把黑窗挂住 —— 所以优先 PowerShell 方案。

## 3. 另外两型

### 3.1 UAC（要“是/否”）

先确认是不是真提权，别乱关安全设置：

```powershell
# lnk 的 RunAsUser 标志（0x2000）
$b = [IO.File]::ReadAllBytes($lnk); 'flags=0x{0:X8}' -f [BitConverter]::ToUInt32($b,20)

# 兼容性里勾了“以管理员身份运行”会落在 Layers
Get-ItemProperty 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers'
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers'
```

处理：取消「以管理员身份运行」；若确实需要提权又要免 UAC，只能改成**任务计划程序**
（创建一次任务、勾“使用最高权限运行”，再用快捷方式 `schtasks /run /tn 名称` 触发）。

### 3.2 MOTW / SmartScreen（exe 来自网络）

```powershell
cmd /c dir /r "路径\程序.exe"            # 有 Zone.Identifier:$DATA 就是被标记了
Get-Item -LiteralPath '路径\程序.exe' -Stream * | Select-Object Stream,Length
Unblock-File -LiteralPath '路径\程序.exe'          # 或：
Remove-Item -LiteralPath '路径\程序.exe' -Stream Zone.Identifier
```

顺带：判型时**先排除假的 MOTW** —— 如果 `dir /r` 干净，就不是“文件来自 Internet”，
再怎么 `Unblock-File` 都没用。

## 4. 验证

```powershell
# 1) 快捷方式确实指向签名程序
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$s.TargetPath; $s.Arguments

# 2) 目标 exe 的签名
Get-AuthenticodeSignature 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' |
    Select-Object Status, @{n='Signer';e={$_.SignerCertificate.Subject}}

# 3) 双击测试；失败看日志
Get-Content "$env:LOCALAPPDATA\MyLauncher\launcher.log" -Encoding UTF8
```

## 5. 坑

- **沙箱 / 低完整性进程里测不出来**：低 IL 写不了 `%LOCALAPPDATA%`、起不了 `sh.exe`（信号管道被拒）、
  schannel 拿不到凭据。这些都会伪装成“启动器坏了”，实际换到用户桌面双击就正常。
- 弹窗的 **pid 是 `explorer.exe`** 很正常：双击本来就在 Explorer 里执行，不代表是资源管理器出问题。
- 别用 `.vbs` 包装：Win11 24H2+ 默认把 VBScript 当可选功能，`wscript` 可能直接没有。
- 只去掉“发布者校验”这一层；目标真的要求提权，UAC 该弹还是弹。
- 改完 `.lnk` 记得保留备份，回滚就是 `Copy-Item 备份.lnk 原路径 -Force`。

## 6. 本次落地（finaterm）

| 文件 | 作用 |
|---|---|
| `dashboard/start-dashboard.ps1` | 隐藏控制台启动器，调用原 `打开金融仪表盘.cmd`，日志写 `%LOCALAPPDATA%\FinanceDashboard\launcher.log` |
| 桌面 `打开金融仪表盘.lnk` | 目标改为 `powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File …` |
| `dashboard/.launcher-backup/` | 旧 `.lnk` 备份（已 gitignore） |

对应 commit：`529b8a6 dashboard: 快捷方式改用 PowerShell 启动器，跳过 .cmd 的发布者校验提示`
