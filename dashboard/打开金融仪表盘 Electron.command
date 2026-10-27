#!/usr/bin/env bash
set -euo pipefail

# 切换到脚本所在目录
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "未找到 uv，请先安装 uv 并确保它已加入 PATH。"
  read -r -p "按回车键退出..." _
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "未找到 npm，请先安装 Node.js。"
  read -r -p "按回车键退出..." _
  exit 1
fi

if [ ! -f "node_modules/electron/package.json" ]; then
  echo "正在安装 Electron..."
  if ! npm install; then
    echo "Electron 安装失败。"
    read -r -p "按回车键退出..." _
    exit 1
  fi
fi

if ! npm start; then
  echo "金融数据终端启动失败。"
  read -r -p "按回车键退出..." _
  exit 1
fi
