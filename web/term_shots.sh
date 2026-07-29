#!/usr/bin/env bash
# 生成演示手册引用的终端截屏：真实命令输出 → 终端风格 HTML → PNG。
# 产出 web/shots/shot-*.png（smoke / tree / loop1~4 / delred）。
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(dirname "$HERE")"
export LD_LIBRARY_PATH="$HOME/.local/lib/chrome-deps:$LD_LIBRARY_PATH"
NPX_PP="$(find "$HOME/.npm/_npx" -maxdepth 3 -name puppeteer -type d 2>/dev/null | head -1)"
export NODE_PATH="$(dirname "$NPX_PP")"
mkdir -p "$HERE/shots"
echo "[1/2] 渲染真实终端输出 → HTML"
( cd "$REPO" && MOCK_LLM=1 python3 web/gen_term_shots.py )
echo "[2/2] 截图 → shots/"
node "$HERE/term_capture.js"
ls -1 "$HERE/shots/"/shot-*.png
