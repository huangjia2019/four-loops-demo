#!/usr/bin/env bash
# 启动「实时 demo」—— 不是截屏。
# 做两件事：1) 用真实循环运行生成 data.json  2) 起一个静态服务并打印网址。
# 然后你在浏览器打开那个网址，点左边四种循环，就是活的演示台。
#
#   bash web/serve.sh            # 默认 http://127.0.0.1:8099
#   PORT=9000 bash web/serve.sh  # 换端口
#
# 注意：必须通过这个服务打开，不能直接双击 index.html —— 页面要 fetch data.json，
# file:// 会被浏览器拦掉（白屏）。这个脚本就是为了解决这一点。
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
PORT="${PORT:-8099}"

echo "[1/2] 用真实循环运行生成演示数据 data.json"
( cd "$REPO" && MOCK_LLM=1 python3 web/gen_data.py )

echo "[2/2] 启动演示台"
echo "──────────────────────────────────────────────"
echo "  浏览器打开：  http://127.0.0.1:${PORT}"
echo "  左边点四种循环；每种里可以「▶ 重放」看一圈圈推进；"
echo "  ④ 流水线式那页，例外队列的按钮能点，模拟人工裁决。"
echo "  停止：Ctrl-C"
echo "──────────────────────────────────────────────"
cd "$HERE"
exec python3 -m http.server "$PORT"
