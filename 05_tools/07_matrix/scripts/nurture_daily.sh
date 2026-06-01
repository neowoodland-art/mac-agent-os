#!/bin/bash
# nurture_daily.sh — 每日养号（mc CLI 版本）
# 替代旧的 nurture_master.sh（依赖智能体）
#
# 执行序列:
#   Batch 1: 3个抖音 (douyin_01/02/camo01)
#   Batch 2: 3个小���书 (xhs_01/02/03)
#   Batch 3: 3个抖音 (douyin_04/05/06)
#   Batch 4: 3个小红书 (xhs_04/05/06)
#
# 每个账号跑3轮，每轮随机执行蓝图，间隔45-90秒
#
# 用法:
#   bash nurture_daily.sh          # 完整执行
#   bash nurture_daily.sh --dry    # 只打印命令不执行
#   bash nurture_daily.sh --group 1  # 只跑第1组

MC="$HOME/workbuddy-agent-os/agent-sync/05_tools/07_matrix/mc"
LOG="/tmp/nurture_daily_$(date +%Y%m%d).log"
ROUNDS=3
INTERVAL="45-90"
BLUEPRINT="nurture_v1"
DRY=false
GROUP="all"

# 解析参数
for arg in "$@"; do
    case $arg in
        --dry) DRY=true ;;
        --group=*) GROUP="${arg#*=}" ;;
    esac
done

log() {
    echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG"
}

run_batch() {
    local label="$1"
    local accounts="$2"
    local cmd="$MC run --accounts $accounts --blueprints $BLUEPRINT --rounds $ROUNDS --mix --interval $INTERVAL"

    log "=== $label ==="
    log "命令: $cmd"

    if [ "$DRY" = true ]; then
        echo "  [DRY] $cmd"
        return 0
    fi

    # 执行
    $cmd >> "$LOG" 2>&1
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        log "✅ $label 完成"
    else
        log "❌ $label 失败 (exit=$exit_code)"
    fi

    # 批次间休息
    sleep 30
}

# === 执行序列 ===

log "============================================"
log " 每日养号开始 ($(date '+%Y-%m-%d %H:%M'))"
log "============================================"

if [ "$GROUP" = "all" ] || [ "$GROUP" = "1" ]; then
    run_batch "Batch 1: 抖音前三" "douyin_01,douyin_02,douyin_camo01"
fi

if [ "$GROUP" = "all" ] || [ "$GROUP" = "2" ]; then
    run_batch "Batch 2: 小红书前三" "xhs_01,xhs_02,xhs_03"
fi

if [ "$GROUP" = "all" ] || [ "$GROUP" = "3" ]; then
    run_batch "Batch 3: 抖音后三" "douyin_04,douyin_05,douyin_06"
fi

if [ "$GROUP" = "all" ] || [ "$GROUP" = "4" ]; then
    run_batch "Batch 4: 小红书后三" "xhs_04,xhs_05,xhs_06"
fi

log ""
log "============================================"
log " 每日养号结束 ($(date '+%Y-%m-%d %H:%M'))"
log " 日志: $LOG"
log "============================================"
