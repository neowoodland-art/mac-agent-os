#!/bin/bash
# run_all.sh — 全量账号运行脚本（采集信息 + 养号）
# 版本: 1.0 | 最后更新: 2026-06-13
#
# 执行流程:
#   Phase 1: 采集所有账号资料 → 更新 profiles.json
#   Phase 2: 对所有已登录账号执行养号
#
# 同手机号账号共享浏览器指纹（phone_15370103682）

cd "$(dirname "$0")"
PYTHON="/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3"
REPORT="/tmp/matrix_run_report_$(date +%Y%m%d_%H%M).log"
START=$(date +%s)

log() { echo "[$(date '+%H:%M:%S')] $1" | tee -a "$REPORT"; }

log "============================================"
log "  Matrix 全量账号运行脚本"
log "  时间: $(date '+%Y-%m-%d %H:%M')"
log "============================================"

# ── Phase 1: 采集所有账号资料 ──
log ""
log "=== Phase 1: 采集账号资料 ==="

DOUYIN_ACCOUNTS=("douyin_test" "douyin_133" "douyin_133_2" "douyin_134")
XHS_ACCOUNTS=("xhs_01")

log "📱 抖音账号采集..."
for account in "${DOUYIN_ACCOUNTS[@]}"; do
    log "  🔄 $account → 读取主页信息..."
    $PYTHON -m mc run \
        --accounts "$account" \
        --blueprints douyin_read_profile \
        --rounds 1 --interval 5-10 2>&1 | tail -5 >> "$REPORT"
    log "  ✅ $account 采集完成"
    sleep 3
done

log ""
log "📱 小红书账号采集..."
for account in "${XHS_ACCOUNTS[@]}"; do
    log "  🔄 $account → 读取主页信息..."
    $PYTHON -m mc run \
        --accounts "$account" \
        --blueprints xiaohongshu_read_profile \
        --rounds 1 --interval 5-10 2>&1 | tail -5 >> "$REPORT"
    log "  ✅ $account 采集完成"
    sleep 3
done

# ── Phase 2: 执行养号 ──
log ""
log "=== Phase 2: 执行养号 ==="

log ""
log "🎵 抖音养号 (douyin_test, douyin_133, douyin_133_2, douyin_134)..."
$PYTHON -m mc run \
    --accounts douyin_test,douyin_133,douyin_133_2,douyin_134 \
    --blueprints douyin_daily \
    --rounds 3 --mix --interval 45-90 2>&1 | tee -a "$REPORT"

log ""
log "📕 小红书养号 (xhs_01)..."
$PYTHON -m mc run \
    --accounts xhs_01 \
    --blueprints xhs_daily \
    --rounds 3 --mix --interval 45-90 2>&1 | tee -a "$REPORT"

# ── 报告 ──
END=$(date +%s)
DURATION=$((END - START))
MIN=$((DURATION / 60))
SEC=$((DURATION % 60))

log ""
log "============================================"
log "  ✅ 全量运行完成"
log "  耗时: ${MIN}分${SEC}秒"
log "  报告: $REPORT"
log "============================================"

echo ""
echo "📊 最终 profiles.json:"
$PYTHON -c "import json; d=json.load(open('$HOME/workbuddy-agent-os/agent-local/tools/matrix/data/profiles.json')); [print(f'  {k}: {v.get(\"nickname\",\"?\")} | 粉丝={v.get(\"fans\",\"?\")} | 作品={v.get(\"posts\",\"?\")}') for k,v in d.items()]"
