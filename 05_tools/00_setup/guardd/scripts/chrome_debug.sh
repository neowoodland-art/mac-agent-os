#!/bin/bash
# chrome_debug.sh — 启动 Chrome 远程调试（供 launchd 调用）
# 确保 Chrome 以 --remote-debugging-port=9222 运行
#
# v2 — 增强版
#   - 所有日志带时间戳
#   - 重启次数限制（最多 5 次，超出后退出等待手动处理）
#   - 重启间隔递增（5s → 15s → 30s）
#   - 检测到 OOM 时打印内存状态

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_DATA_DIR="/tmp/chrome-douyin-profile"
PIDFILE="/tmp/chrome-debug.pid"
LOG_FILE="/tmp/chrome_debug_launchd.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /tmp/chrome_debug_watch.log
}

is_9222_alive() {
    curl -s --connect-timeout 3 http://127.0.0.1:9222/json/version >/dev/null 2>&1
}

launch_chrome() {
    nohup "$CHROME" \
        --remote-debugging-port=9222 \
        --user-data-dir="$USER_DATA_DIR" \
        --no-first-run --no-default-browser-check \
        --disable-features=ChromeWhatsNewUI \
        --window-position=9999,9999 \
        about:blank \
        > "$LOG_FILE" 2>&1 &
    echo $! > "$PIDFILE"
    log "Chrome 已启动 (PID $!)，屏幕外位置 (9999,9999)"
}

# ── 主流程 ──

log "=== chrome_debug.sh 启动 ==="

# 先检查 9222 是否已经在线
if is_9222_alive; then
    log "端口 9222 已有 Chrome 在监听，进入健康检查循环"
else
    log "端口 9222 无响应，启动 Chrome..."
    launch_chrome
    # 等最多 15 秒
    for i in $(seq 1 15); do
        sleep 1
        if is_9222_alive; then
            log "Chrome debug 启动成功（第 ${i} 秒）"
            break
        fi
    done
    if ! is_9222_alive; then
        log "❌ Chrome 启动超时（15 秒），请检查: cat $LOG_FILE"
        exit 1
    fi
fi

# ── 健康检查循环 ──
RESTART_COUNT=0
MAX_RESTARTS=5

while true; do
    sleep 10

    if is_9222_alive; then
        # 正常：端末还在，继续监控
        continue
    fi

    # 端口 9222 挂了
    RESTART_COUNT=$((RESTART_COUNT + 1))
    log "⚠️  端口 9222 无响应（第 ${RESTART_COUNT} 次）"

    if [ "$RESTART_COUNT" -gt "$MAX_RESTARTS" ]; then
        log "❌ 已连续重启 ${MAX_RESTARTS} 次失败，退出等待手动处理"
        log "   请检查: 系统内存是否充足（vm_stat），或手动启动 Chrome"
        log "   手动命令:  pkill -f 'remote-debugging-port=9222'"
        log "             $CHROME --remote-debugging-port=9222 --user-data-dir=$USER_DATA_DIR --no-first-run --no-default-browser-check about:blank &"
        exit 2
    fi

    # 递增等待时间：5s → 15s → 30s → 30s → 30s
    WAIT=$(( RESTART_COUNT <= 1 ? 5 : RESTART_COUNT == 2 ? 15 : 30 ))
    log "等待 ${WAIT} 秒后重启..."

    # 清理残留 Chrome 进程（防止多实例）
    pkill -f "remote-debugging-port=9222" 2>/dev/null || true
    sleep 2

    # 打印内存状态帮助排查
    memory_free=$(vm_stat | awk '/free/ {print $3}' | sed 's/\.//')
    log "当前空闲内存页: ${memory_free:-?}"

    launch_chrome

    # 等最多 20 秒看有没有起来
    for i in $(seq 1 20); do
        sleep 1
        if is_9222_alive; then
            log "Chrome 重启成功（第 ${i} 秒）"
            # 成功一次重置计数
            RESTART_COUNT=0
            break
        fi
    done

    if ! is_9222_alive; then
        log "❌ Chrome 重启失败（20 秒超时），继续下一轮"
    fi
done
