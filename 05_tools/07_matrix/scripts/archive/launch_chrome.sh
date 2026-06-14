#!/bin/bash
# Chrome 启动脚本 - 带 CDP 调试端口 + 独立 Profile
# 用法: ./launch_chrome.sh <账号ID> [调试端口]
# 示例: ./launch_chrome.sh account_01 9222

ACCOUNT_ID=${1:-account_01}
DEBUG_PORT=${2:-9222}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILE_DIR="$SCRIPT_DIR/../profiles/$ACCOUNT_ID"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 检查 Chrome 是否安装
if [ ! -f "$CHROME" ]; then
    echo "❌ Chrome 未安装，请先从 https://www.google.com/chrome/ 下载安装"
    exit 1
fi

# 检查端口是否已被占用
if lsof -ti:$DEBUG_PORT > /dev/null 2>&1; then
    echo "⚠️  端口 $DEBUG_PORT 已被占用，尝试连接已有 Chrome..."
    curl -s http://localhost:$DEBUG_PORT/json/version | python3 -m json.tool 2>/dev/null
    exit 0
fi

mkdir -p "$PROFILE_DIR"

echo "🚀 启动 Chrome"
echo "   账号:     $ACCOUNT_ID"
echo "   端口:     $DEBUG_PORT"
echo "   Profile:  $PROFILE_DIR"
echo ""

"$CHROME" \
    --remote-debugging-port="$DEBUG_PORT" \
    --user-data-dir="$PROFILE_DIR" \
    --window-size=1024,768 \
    --window-position=100,100 \
    --no-first-run \
    --no-default-browser-check \
    --disable-extensions \
    --disable-background-networking \
    --disable-sync \
    2>/dev/null &

CHROME_PID=$!
echo "   PID:      $CHROME_PID"
echo ""

# 等待 Chrome 就绪
echo "⏳ 等待 Chrome 就绪..."
for i in {1..10}; do
    sleep 1
    if curl -s http://localhost:$DEBUG_PORT/json/version > /dev/null 2>&1; then
        echo "✅ Chrome 已就绪！"
        echo ""
        echo "CDP 地址: http://localhost:$DEBUG_PORT"
        echo "现在可以在 Chrome 里手动登录各平台，Cookie 将自动保存到:"
        echo "$PROFILE_DIR"
        exit 0
    fi
    echo "   等待中... ($i/10)"
done

echo "❌ Chrome 启动超时，请检查是否有报错"
exit 1
