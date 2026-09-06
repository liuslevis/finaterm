@echo off
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
  echo 未找到 uv，请先安装 uv 并确保它已加入 PATH。
  pause
  exit /b 1
)

start "金融数据终端" /min uv run python "%~dp0dashboard_server.py"

if errorlevel 1 (
  echo 无法启动金融数据终端。
  pause
)
