#!/bin/bash
# ===============================================================
# 养号主控脚本 — 抖音1h → 小红书1h → 循环
# 并行运行三个账号，每个阶段固定时长
# macOS 兼容：用 macos_timeout 替代 GNU timeout
# ===============================================================

PYTHON="/Users/5kecheng/.workbuddy/binaries/python/envs/agent-os/bin/python3"
MATRIX="$HOME/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts/matrix.py"
LOG_DIR="/tmp/nurture_master"
mkdir -p "$LOG_DIR"

# macOS 兼容的 timeout 实现（GNU timeout 在 macOS 不可用）
macos_timeout() {
    local secs=$1; shift
    "$@" &
    local pid=$!
    (sleep "$secs" && kill -TERM "$pid" 2>/dev/null) &
    local killer=$!
    wait "$pid" 2>/dev/null
    local status=$?
    kill "$killer" 2>/dev/null
    wait "$killer" 2>/dev/null
    return $status
}

echo "[$(date '+%H:%M:%S')] ========================================"
echo "[$(date '+%H:%M:%S')] 养号主控启动"
echo "[$(date '+%H:%M:%S')] ========================================"

# ═══════════════════════════════════════════════════════════════
# Phase 0: 全量 Cookie 备份（防误删）
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[$(date '+%H:%M:%S')] 💾 全量 Cookie 备份..."
$PYTHON -c "
import sys; sys.path.insert(0, '$HOME/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts')
from matrix_modules.utils.cookie_manager import backup_all_identities
bak = backup_all_identities(platform='master', label='pre_start')
for k, v in bak.items():
    if v: print(f'  ✅ {k}: {v.split(chr(47))[-1]}')
    else: print(f'  ⚠️ {k}: 无 cookie 文件')
" 2>&1
echo ""

# ═══════════════════════════════════════════════════════════════
# Phase 1: 抖音 1 小时
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[$(date '+%H:%M:%S')] ════════════════════════════════════════"
echo "[$(date '+%H:%M:%S')] Phase 1: 抖音养号（1 小时）"
echo "[$(date '+%H:%M:%S')] ════════════════════════════════════════"
echo ""

# 抖音三个账号并行（-r 10 表示多轮循环，由 nurture_multi 管理时长）
# --no-daemon: 阶段结束后正常关闭浏览器，释放 profile 供下一阶段使用
$PYTHON $MATRIX nurture run \
    -a douyin_01 -a douyin_02 -a douyin_camo01 -r 10 \
    --no-daemon \
    > "$LOG_DIR/douyin_phase.log" 2>&1 &
DY_PID=$!
# 4000s 超时保护
( sleep 4000 && kill $DY_PID 2>/dev/null ) &
DY_KILLER=$!
wait $DY_PID 2>/dev/null
DY_STATUS=$?
kill $DY_KILLER 2>/dev/null; wait $DY_KILLER 2>/dev/null
echo "[$(date '+%H:%M:%S')] 抖音阶段退出码: $DY_STATUS"

# ═══════════════════════════════════════════════════════════════
# 阶段间休息 30 秒
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[$(date '+%H:%M:%S')] 阶段切换，休息 30 秒..."
sleep 30

# ═══════════════════════════════════════════════════════════════
# Phase 2: 小红书 1 小时
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[$(date '+%H:%M:%S')] ════════════════════════════════════════"
echo "[$(date '+%H:%M:%S')] Phase 2: 小红书养号（1 小时）"
echo "[$(date '+%H:%M:%S')] ════════════════════════════════════════"
echo ""

# 小红书三个账号并行
$PYTHON $MATRIX nurture run \
    -a xhs_01 -a xhs_02 -a xhs_03 -r 10 \
    > "$LOG_DIR/xhs_phase.log" 2>&1 &
XHS_PID=$!
( sleep 4000 && kill $XHS_PID 2>/dev/null ) &
XHS_KILLER=$!
wait $XHS_PID 2>/dev/null
XHS_STATUS=$?
kill $XHS_KILLER 2>/dev/null; wait $XHS_KILLER 2>/dev/null
echo "[$(date '+%H:%M:%S')] 小红书阶段退出码: $XHS_STATUS"

# ═══════════════════════════════════════════════════════════════
# 完成
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[$(date '+%H:%M:%S')] ========================================"
echo "[$(date '+%H:%M:%S')] 养号主控完成"
echo "[$(date '+%H:%M:%S')]   抖音: $([ $DY_STATUS -eq 0 ] && echo '✅' || echo '❌')"
echo "[$(date '+%H:%M:%S')]   小红书: $([ $XHS_STATUS -eq 0 ] && echo '✅' || echo '❌')"
echo "[$(date '+%H:%M:%S')] ========================================"
