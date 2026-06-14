#!/bin/bash
# =============================================================================
# 向量库增量更新脚本 (vector_backfill.sh)
# 联邦系统定时任务 — 将 L2 新事实回填到 ChromaDB 向量索引
# 依赖: oMLX (localhost:8000) + matrix Python venv
# =============================================================================
set -e

AGENT_SYNC="/Users/7kecheng/workbuddy-agent-os/agent-sync"
PYTHON="/Users/7kecheng/.workbuddy/binaries/python/envs/matrix/bin/python3"
SKILL_DIR="/Users/7kecheng/.workbuddy/skills/memory_manager"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="$AGENT_SYNC/04_memory/vector_db/backfill.log"

echo "[${TIMESTAMP}] 🚀 向量库增量更新开始"

# 1. 检查 oMLX 是否运行
if ! curl -sf http://localhost:8000/v1/models > /dev/null 2>&1; then
    echo "[${TIMESTAMP}] ⚠️  oMLX 未运行 (localhost:8000)，跳过更新"
    echo "[${TIMESTAMP}] 💡 请先启动 oMLX: AppleScript → Start Server"
    exit 0
fi
echo "[${TIMESTAMP}] ✅ oMLX 运行正常"

# 2. 统计更新前向量数
BEFORE=0
if [ -d "$AGENT_SYNC/04_memory/vector_db/chroma" ]; then
    BEFORE=$(find "$AGENT_SYNC/04_memory/vector_db/chroma" -name "*.chroma.sqlite3" 2>/dev/null | wc -l)
fi

# 3. 执行增量回填
echo "[${TIMESTAMP}] 🔄 执行增量回填..."
cd "$SKILL_DIR"
OUTPUT=$($PYTHON semantic_search.py --root "$AGENT_SYNC" backfill 2>&1)
EXIT_CODE=$?

# 4. 统计结果
SUCCESS=$(echo "$OUTPUT" | grep -c "\[OK\]" || true)
FAIL=$(echo "$OUTPUT" | grep -c "\[FAIL\]" || true)
echo "$OUTPUT" | tee -a "$LOG_FILE"

if [ $EXIT_CODE -eq 0 ]; then
    echo "[${TIMESTAMP}] ✅ 向量库更新完成 (成功: $SUCCESS, 失败: $FAIL)"
    echo "[${TIMESTAMP}] ✅ 更新前 chroma 文件数: $BEFORE"
else
    echo "[${TIMESTAMP}] ❌ 向量库更新异常 (code=$EXIT_CODE)"
fi

echo "[${TIMESTAMP}] 📝 日志已保存: $LOG_FILE"
echo "[${TIMESTAMP}] 🏁 结束"
