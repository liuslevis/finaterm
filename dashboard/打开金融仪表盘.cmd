@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

for %%I in ("%~dp0..") do set "FINANCE_ROOT=%%~fI"
set "FUTU_OPEND_ROOT=%FINANCE_ROOT%\FutuOpenD"
set "USDATA_ROOT=%FINANCE_ROOT%\usdata"
set "FUTU_PYTHON=%FUTU_OPEND_ROOT%\.venv\Scripts\python.exe"
set "FUTU_KLINE=%FUTU_OPEND_ROOT%\skills\futuapi\scripts\quote\get_kline.py"
set "USDATA_PYTHON=%USDATA_ROOT%\.venv\Scripts\python.exe"

where uv >nul 2>nul
if errorlevel 1 (
  echo 未找到 uv，请先安装 uv 并确保它已加入 PATH。
  pause
  exit /b 1
)

if not exist "%FUTU_PYTHON%" (
  echo 未找到富途 Python 环境：%FUTU_PYTHON%
  echo 请在 FutuOpenD 目录运行 uv sync。
  pause
  exit /b 1
)

if not exist "%FUTU_KLINE%" (
  echo 未找到富途行情脚本：%FUTU_KLINE%
  pause
  exit /b 1
)

if not exist "%USDATA_PYTHON%" (
  echo 未找到宏观数据 Python 环境：%USDATA_PYTHON%
  echo 请先完成 usdata 的依赖安装。
  pause
  exit /b 1
)

if not exist "%~dp0usdata_mcp_bridge.py" (
  echo 未找到宏观数据桥接程序：%~dp0usdata_mcp_bridge.py
  pause
  exit /b 1
)

if not exist "%~dp0index.html" (
  echo 未找到仪表盘页面：%~dp0index.html
  pause
  exit /b 1
)

echo 正在检查仪表盘 Python 依赖...
uv sync --project "%~dp0." --quiet
if errorlevel 1 (
  echo 仪表盘 Python 依赖安装失败。
  pause
  exit /b 1
)

set "OPEND_EXE="
if exist "%APPDATA%\Futu_OpenD\Futu_OpenD.exe" set "OPEND_EXE=%APPDATA%\Futu_OpenD\Futu_OpenD.exe"
if not defined OPEND_EXE if exist "%LOCALAPPDATA%\Futu_OpenD\Futu_OpenD.exe" set "OPEND_EXE=%LOCALAPPDATA%\Futu_OpenD\Futu_OpenD.exe"

if not defined OPEND_EXE (
  echo 未找到 Futu OpenD GUI，请先安装官方 OpenD。
  echo 默认查找位置：%%APPDATA%%\Futu_OpenD\Futu_OpenD.exe
  pause
  exit /b 1
)

call :is_opend_ready
if not errorlevel 1 goto :opend_ready

powershell -NoProfile -Command "if (Get-Process -Name 'Futu_OpenD' -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo 正在启动 Futu OpenD...
  start "Futu OpenD" "%OPEND_EXE%"
) else (
  echo Futu OpenD 已运行，正在等待 API 服务...
)

for /L %%I in (1,1,30) do (
  call :is_opend_ready
  if not errorlevel 1 goto :opend_ready
  powershell -NoProfile -Command "Start-Sleep -Seconds 1"
)

echo [警告] Futu OpenD 尚未开放 127.0.0.1:11111。
echo 请在 OpenD 窗口完成登录并确认 API 端口已启用；仪表盘仍会继续启动。
goto :start_dashboard

:opend_ready
echo Futu OpenD API 已就绪。

:start_dashboard
set "FINANCE_DATA_ROOT=%FINANCE_ROOT%"
start "金融数据终端" /min uv run --project "%~dp0." python "%~dp0dashboard_server.py"

if errorlevel 1 (
  echo 无法启动金融数据终端。
  pause
  exit /b 1
)

exit /b 0

:is_opend_ready
powershell -NoProfile -Command "$client = [Net.Sockets.TcpClient]::new(); try { $task = $client.ConnectAsync('127.0.0.1', 11111); if (-not $task.Wait(500)) { exit 1 }; if ($client.Connected) { exit 0 }; exit 1 } catch { exit 1 } finally { $client.Dispose() }" >nul 2>&1
exit /b %errorlevel%
