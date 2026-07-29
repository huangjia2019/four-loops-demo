#!/usr/bin/env bash
# 一键：生成真实运行数据 → 起静态服务 → puppeteer 抓大截屏 → 关服务。
# 产出 web/shots/ui-*.png（整页 / 主区 / 代码卡近景）。
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
PORT="${PORT:-8099}"

# chrome 依赖（本机 libasound 需手动挂）
export LD_LIBRARY_PATH="$HOME/.local/lib/chrome-deps:$LD_LIBRARY_PATH"
NPX_PP="$(find "$HOME/.npm/_npx" -maxdepth 3 -name puppeteer -type d 2>/dev/null | head -1)"
export NODE_PATH="$(dirname "$NPX_PP")"

echo "[1/3] 生成真实运行数据 data.json"
( cd "$REPO" && MOCK_LLM=1 python3 web/gen_data.py )

echo "[2/3] 起静态服务 :$PORT"
( cd "$HERE" && python3 -m http.server "$PORT" >/tmp/floop-http.log 2>&1 ) &
HTTP_PID=$!
sleep 1.2

echo "[3/3] 抓截屏"
mkdir -p "$HERE/shots"
node "$HERE/capture.js" "http://127.0.0.1:$PORT" || true

kill "$HTTP_PID" 2>/dev/null || true
echo "shots →"; ls -1 "$HERE/shots/" 2>/dev/null
