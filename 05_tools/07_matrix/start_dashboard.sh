#!/bin/bash
# Matrix Dashboard 启动/重启脚本
# 用法: bash start_dashboard.sh [start|stop|restart]

ACTION="${1:-start}"

# 自动检测 Python
PYTHON=""
if [ -f "$HOME/.workbuddy/binaries/python/versions/3.13.12/bin/python3" ]; then
    PYTHON="$HOME/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    echo "❌ 找不到 Python 3"
    exit 1
fi

DASHBOARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../10_dashboard"
PORT="${PORT:-9988}"

start() {
    echo "🚀 启动 Dashboard (端口 $PORT)..."
    cd "$DASHBOARD_DIR"
    nohup "$PYTHON" -m uvicorn app:app --host 0.0.0.0 --port "$PORT" \
        > /tmp/dashboard.log 2>&1 &
    echo "   PID: $!"
    echo "   日志: /tmp/dashboard.log"
    echo "   访问: http://localhost:$PORT"
}

stop() {
    echo "🛑 停止 Dashboard..."
    PID=$(lsof -ti :$PORT 2>/dev/null)
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null
        sleep 2
        echo "   已停止 (PID $PID)"
    else
        echo "   Dashboard 未运行"
    fi
}

case "$ACTION" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; sleep 1; start ;;
    *)       echo "用法: $0 [start|stop|restart]" ;;
esac
