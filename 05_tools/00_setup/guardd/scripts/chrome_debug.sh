#!/bin/bash
# chrome_debug.sh — 启动 Chrome 远程调试（供 launchd 调用）
# 确保 Chrome 以 --remote-debugging-port=9222 运行

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_DATA_DIR="/tmp/chrome-douyin-profile"
PIDFILE="/tmp/chrome-debug.pid"

# 检查 9222 是否已监听
if curl -s http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
    # 已经 OK，保持进程不退出
    while true; do sleep 60; done
    exit 0
fi

# 检查是否有遗留的 Chrome 进程（没有 9222 但 Chrome 在跑）
if pgrep -x "Google Chrome" >/dev/null 2>&1; then
    # Chrome 在跑但没有调试端口，可能是普通模式
    # 不关它，我们另外开一个
    :
fi

# 启动 Chrome（用 setsid 完全脱离）
nohup "$CHROME" \
    --remote-debugging-port=9222 \
    --user-data-dir="$USER_DATA_DIR" \
    --no-first-run \
    --no-default-browser-check \
    --disable-features=ChromeWhatsNewUI \
    about:blank \
    > /tmp/chrome_debug_launchd.log 2>&1 &

echo $! > "$PIDFILE"

# 等待启动
for i in 1 2 3 4 5 6 7 8 9 10; do
    sleep 1
    if curl -s http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
        echo "Chrome debug 启动成功"
        # 保持进程不退出，避免 launchd KeepAlive 无限重启
        while true; do sleep 60; done
        exit 0
    fi
done

echo "Chrome debug 启动超时"
exit 1
