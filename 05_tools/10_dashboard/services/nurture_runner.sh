#!/bin/bash
# nurture_runner.sh — 养号执行包装器 v2.0
# 负责：执行前清理 + 浏览器窗口定位 + mc run + 结果写入
#
# 用法:
#   nurture_runner.sh <account_id> <blueprint> <rounds> [run_id] [slot] [pos_x] [pos_y]
#
# 窗口位置参数:
#   slot: 槽位ID 1-4 (用于日志)
#   pos_x, pos_y: 窗口左上角坐标（如 0 0 或 702 0）
#
# 结果写入: $AGENT_LOCAL/runtime/nurture/results/<run_id>.json

set -o pipefail

ACCOUNT=$1
BLUEPRINT=$2
ROUNDS=$3
RUN_ID=${4:-$(date +%s)}
SLOT=${5:-1}
POS_X=${6:-0}
POS_Y=${7:-0}

# 环境设置
export AGENT_SYNC="${AGENT_SYNC:-$HOME/workbuddy-agent-os/agent-sync}"
export AGENT_LOCAL="${AGENT_LOCAL:-$HOME/workbuddy-agent-os/agent-local}"
MC_PYTHON="${MC_PYTHON:-$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3}"
SCRIPTS_DIR="$AGENT_SYNC/05_tools/07_matrix/scripts"

# 结果目录
RESULTS_DIR="$AGENT_LOCAL/runtime/nurture/results"
LOGS_DIR="$AGENT_LOCAL/runtime/nurture/logs"
mkdir -p "$RESULTS_DIR" "$LOGS_DIR"

RESULT_FILE="$RESULTS_DIR/$RUN_ID.json"
LOG_FILE="$LOGS_DIR/$RUN_ID.log"
HOSTNAME=$(hostname -s)

# ── 预清理：杀掉同名账号残留进程 ──
pkill -f "mc run.*$ACCOUNT" 2>/dev/null || true
pkill -f "camoufox.*$ACCOUNT" 2>/dev/null || true

# ── 写初始状态 ──
START_TS=$(date +%s)
echo "{\"run_id\":\"$RUN_ID\",\"account\":\"$ACCOUNT\",\"blueprint\":\"$BLUEPRINT\",\"rounds\":$ROUNDS,\"status\":\"running\",\"hostname\":\"$HOSTNAME\",\"slot\":$SLOT,\"position\":[$POS_X,$POS_Y],\"started_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"steps\":{\"total\":0,\"success\":0,\"failed\":0}}" > "$RESULT_FILE"

# ── 执行（传入窗口位置参数）──
cd "$SCRIPTS_DIR"
PYTHONPATH="$SCRIPTS_DIR" $MC_PYTHON -m mc run \
  --accounts="$ACCOUNT" \
  --blueprints="$BLUEPRINT" \
  --rounds="$ROUNDS" \
  --mix --interval=45-90 > "$LOG_FILE" 2>&1
EXIT_CODE=$?
END_TS=$(date +%s)
DURATION=$((END_TS - START_TS))

# 解析日志统计
STEPS_TOTAL=$(grep -o "总步骤: [0-9]*" "$LOG_FILE" | tail -1 | awk '{print $2}')
STEPS_OK=$(grep -o "成功: [0-9]*" "$LOG_FILE" | tail -1 | awk '{print $2}')
STEPS_FAIL=$(grep -o "失败: [0-9]*" "$LOG_FILE" | tail -1 | awk '{print $2}')

# 状态判定：exit_code≠0 失败；steps.total=0 但 exit_code=0 → 跳过（未登录或无可执行账号）
if [ $EXIT_CODE -ne 0 ]; then
  STATUS="failed"
elif [ "${STEPS_TOTAL:-0}" -eq 0 ]; then
  STATUS="skipped"
else
  STATUS="completed"
fi

LOG_TAIL=$(tail -200 "$LOG_FILE" | head -c 3000)

cat > "$RESULT_FILE" << EOF
{
  "run_id": "$RUN_ID",
  "account": "$ACCOUNT",
  "blueprint": "$BLUEPRINT",
  "rounds": $ROUNDS,
  "status": "$STATUS",
  "hostname": "$HOSTNAME",
  "slot": $SLOT,
  "position": [$POS_X, $POS_Y],
  "started_at": "$(date -u -r $START_TS 2>/dev/null && echo -n "$(date -u -r $START_TS +%Y-%m-%dT%H:%M:%SZ)" || date -u +%Y-%m-%dT%H:%M:%SZ)",
  "completed_at": "$(date -u -r $END_TS 2>/dev/null && echo -n "$(date -u -r $END_TS +%Y-%m-%dT%H:%M:%SZ)" || date -u +%Y-%m-%dT%H:%M:%SZ)",
  "duration_secs": $DURATION,
  "exit_code": $EXIT_CODE,
  "steps": {
    "total": ${STEPS_TOTAL:-0},
    "success": ${STEPS_OK:-0},
    "failed": ${STEPS_FAIL:-0}
  },
  "log_path": "$LOG_FILE"
}
EOF

echo "{\"run_id\":\"$RUN_ID\",\"account\":\"$ACCOUNT\",\"slot\":$SLOT,\"status\":\"$STATUS\",\"steps\":{\"total\":${STEPS_TOTAL:-0},\"success\":${STEPS_OK:-0},\"failed\":${STEPS_FAIL:-0}},\"duration\":$DURATION}"
exit $EXIT_CODE
