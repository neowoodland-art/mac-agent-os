#!/bin/bash
# ──────────────────────────────────────────────
# Matrix 养号 × 天行 SOCKS5 代理 集成脚本
# 全自动：启动转发器 → 跑养号 → 关闭转发器
# macOS 26 兼容，零系统配置，零手动操作
# ──────────────────────────────────────────────

SCRIPT_DIR="/Users/chengzige/workbuddy-agent-os/agent-sync"
FORWARDER="$SCRIPT_DIR/05_tools/05_crawl/longcat/socks5_forwarder.py"
MATRIX_SCRIPT="$SCRIPT_DIR/05_tools/07_matrix/scripts"
PYTHON="/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3"

LOCAL_PROXY_PORT=10800
FWD_PID=""

function log() { echo "[$(date '+%H:%M:%S')] $1"; }

# ─── 1. 启动本地转发器 ───
function start_forwarder() {
    log "🔗 启动 SOCKS5 本地转发器 (端口 $LOCAL_PROXY_PORT)..."
    $PYTHON "$FORWARDER" $LOCAL_PROXY_PORT > /tmp/socks5_fwd.log 2>&1 &
    FWD_PID=$!
    sleep 2
    # 验证
    curl -s --max-time 5 --socks5 "127.0.0.1:$LOCAL_PROXY_PORT" ifconfig.me > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        local ip=$(curl -s --max-time 5 --socks5 "127.0.0.1:$LOCAL_PROXY_PORT" ifconfig.me 2>/dev/null)
        log "   ✅ 转发器就绪，出口 IP: $ip"
    else
        log "   ❌ 转发器启动失败"
        exit 1
    fi
}

# ─── 2. 停止转发器 ───
function stop_forwarder() {
    if [ -n "$FWD_PID" ] && kill -0 "$FWD_PID" 2>/dev/null; then
        log "🔌 关闭 SOCKS5 转发器..."
        kill "$FWD_PID" 2>/dev/null
        sleep 1
        log "   ✅ 转发器已关闭"
    fi
}

# ─── 3. 更新账号配置使用本地代理 ───
function set_proxy_for_account() {
    local account="$1"
    local config_file="$SCRIPT_DIR/agent-local/tools/matrix/identities/$account/config.yaml"
    local orig_file="${config_file}.original"
    
    # 保存原配置（仅第一次备份）
    if [ ! -f "$orig_file" ]; then
        cp "$config_file" "$orig_file"
    fi
    
    # 修改 proxy 为本地转发器
    $PYTHON -c "
import yaml
with open('$config_file') as f:
    cfg = yaml.safe_load(f)
cfg['identity']['proxy'] = {'server': 'socks5://127.0.0.1:$LOCAL_PROXY_PORT'}
cfg['identity']['platform'] = 'douyin'
with open('$config_file', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
print('   proxy: socks5://127.0.0.1:$LOCAL_PROXY_PORT')
"
}

# ─── 4. 恢复账号配置 ───
function restore_proxy() {
    local account="$1"
    local orig_file="$SCRIPT_DIR/agent-local/tools/matrix/identities/$account/config.yaml.original"
    local config_file="$SCRIPT_DIR/agent-local/tools/matrix/identities/$account/config.yaml"
    if [ -f "$orig_file" ]; then
        cp "$orig_file" "$config_file"
        log "   配置已恢复"
    fi
}

# ─── 主流程 ───
function main() {
    echo "═══════════════════════════════════"
    echo " Matrix 养号 × 天行 SOCKS5 代理"
    echo "═══════════════════════════════════"

    if [ $# -eq 0 ]; then
        echo ""
        echo "用法:"
        echo "  bash vpn_nurture.sh <账号ID> [轮数]"
        echo "  bash vpn_nurture.sh <账号1> <账号2> ... [--rounds N]"
        echo ""
        echo "示例:"
        echo "  bash vpn_nurture.sh douyin_test 5"
        echo "  bash vpn_nurture.sh douyin_01 douyin_02 --rounds 3"
        echo ""
        exit 1
    fi

    # 解析参数
    local rounds=5
    local accounts=()
    local next_is_rounds=0
    for arg in "$@"; do
        if [ "$arg" = "--rounds" ]; then
            next_is_rounds=1
        elif [ $next_is_rounds -eq 1 ]; then
            rounds=$arg
            next_is_rounds=0
        elif echo "$arg" | grep -qE '^[0-9]+$' && [ ${#accounts[@]} -eq 0 ]; then
            rounds=$arg
        else
            accounts+=("$arg")
        fi
    done

    # 启动转发器
    start_forwarder

    # 为每个账号配置代理
    for acc in "${accounts[@]}"; do
        log "📝 配置 $acc 使用代理..."
        set_proxy_for_account "$acc"
    done

    # 跑养号
    local failed=0
    for acc in "${accounts[@]}"; do
        log "▶️ 养号: $acc (${rounds}轮)"
        cd "$MATRIX_SCRIPT" && $PYTHON matrix.py nurture run \
            -a "$acc" -r "$rounds" --no-daemon 2>&1
        [ $? -ne 0 ] && failed=1
    done

    # 恢复配置
    for acc in "${accounts[@]}"; do
        restore_proxy "$acc"
    done

    # 关闭转发器
    stop_forwarder

    # 汇总
    echo "═══════════════════════════════════"
    if [ $failed -eq 0 ]; then
        log "🎉 全部完成！共执行 ${#accounts[@]} 个账号"
    else
        log "⚠️  部分失败，请检查日志"
    fi
    echo "═══════════════════════════════════"
}

# 确保退出时清理
trap stop_forwarder EXIT

main "$@"
