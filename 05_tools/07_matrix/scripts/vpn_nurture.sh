#!/bin/bash
# ──────────────────────────────────────────────
# Matrix 养号 × 天行 L2TP VPN 集成脚本
# macOS 26 兼容版（使用 scutil 控制 VPN）
# 自动：连VPN → 跑养号 → 断VPN
# ──────────────────────────────────────────────

SERVICE_NAME="天行L2TP"
MATRIX_SCRIPT="/Users/chengzige/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts"
PYTHON="/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3"

function log() { echo "[$(date '+%H:%M:%S')] $1"; }

# ─── 1. 连接 VPN ───
function vpn_connect() {
    log "🔗 连接 L2TP VPN..."
    # 用 scutil 启动 VPN（macOS 26 兼容）
    scutil --nc start "$SERVICE_NAME" 2>&1
    sleep 5

    local new_ip=$(curl -s --max-time 5 ifconfig.me 2>/dev/null)
    log "   VPN 出口 IP: $new_ip"

    # 如果 IP 没变，等3秒再试一次
    if [ "$new_ip" = "114.218.238.69" ] || [ -z "$new_ip" ]; then
        sleep 3
        new_ip=$(curl -s --max-time 5 ifconfig.me 2>/dev/null)
        log "   重查出口 IP: $new_ip"
    fi
}

# ─── 2. 断开 VPN ───
function vpn_disconnect() {
    log "🔌 断开 L2TP VPN..."
    scutil --nc stop "$SERVICE_NAME" 2>&1
    log "   VPN 已断开"
}

# ─── 3. 跑养号 ───
function run_nurture() {
    local account="$1"
    local rounds="${2:-5}"
    log "▶️ 养号开始: $account (${rounds}轮)"
    cd "$MATRIX_SCRIPT" && $PYTHON matrix.py nurture run \
        -a "$account" -r "$rounds" --no-daemon 2>&1
    local ret=$?
    if [ $ret -eq 0 ]; then
        log "✅ 养号完成: $account"
    else
        log "❌ 养号失败: $account (exit=$ret)"
    fi
    return $ret
}

# ─── 主流程 ───
function main() {
    echo "═══════════════════════════════════"
    echo " Matrix 养号 × 天行 L2TP VPN"
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
        echo "前置条件：先安装天行VPN配置"
        echo "  桌面有 TianXing-L2TP.mobileconfig，双击安装"
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

    # 连接 VPN
    vpn_connect

    # 跑养号
    local failed=0
    for acc in "${accounts[@]}"; do
        run_nurture "$acc" "$rounds"
        [ $? -ne 0 ] && failed=1
    done

    # 断开 VPN
    vpn_disconnect

    # 汇总
    echo "═══════════════════════════════════"
    if [ $failed -eq 0 ]; then
        log "🎉 全部完成！共执行 ${#accounts[@]} 个账号"
    else
        log "⚠️  部分账号执行失败，请检查日志"
    fi
    echo "═══════════════════════════════════"
}

main "$@"
