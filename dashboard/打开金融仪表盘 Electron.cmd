@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
  echo 未找到 uv，请先安装 uv 并确保它已加入 PATH。
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo 未找到 npm，请先安装 Node.js。
  pause
  exit /b 1
)

if not exist "%~dp0node_modules\electron\package.json" (
  echo 正在安装 Electron...
  call npm install
  if errorlevel 1 (
    echo Electron 安装失败。
    pause
    exit /b 1
  )
)

call npm start
if errorlevel 1 (
  echo 金融数据终端启动失败。
  pause
  exit /b 1
)
