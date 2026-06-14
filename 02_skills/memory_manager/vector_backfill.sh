#!/bin/bash
# =============================================================================
# 向量库增量更新脚本 (vector_backfill.sh v1.1)
# 联邦系统定时任务 — 将 L2 新事实回填到 ChromaDB 向量索引
# 依赖: oMLX macOS App + matrix Python venv
# =============================================================================
set -e

AGENT_SYNC="/Users/7kecheng/workbuddy-agent-os/agent-sync"
PYTHON="/Users/7kecheng/.workbuddy/binaries/python/envs/matrix/bin/python3"
SKILL_DIR="/Users/7kecheng/.workbuddy/skills/memory_manager"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="$AGENT_SYNC/04_memory/vector_db/backfill.log"

OMLX_APP="/Applications/oMLX.app"
OMLX_PORT=8000
OMLX_API_KEY="omlx"
OMLX_CHECK_URL="http://localhost:${OMLX_PORT}/v1/models"
OMLX_CHECK_HEADER="Authorization: Bearer ${OMLX_API_KEY}"
OMLX_WAIT_MAX=60        # 最多等 60 秒（模型加载可能较慢）

echo "[${TIMESTAMP}] 🚀 向量库增量更新开始"

# ═══════════════════════════════════════════════════════════
# 1. 检查 oMLX 是否运行，未运行则自动启动
# ═══════════════════════════════════════════════════════════
if curl -sf -H "$OMLX_CHECK_HEADER" "$OMLX_CHECK_URL" > /dev/null 2>&1; then
    echo "[${TIMESTAMP}] ✅ oMLX 运行中"
else
    echo "[${TIMESTAMP}] 🚀 oMLX 未运行，正在启动..."
    open "$OMLX_APP"
    
    # 等待就绪（最多 60s）
    for i in $(seq 1 $OMLX_WAIT_MAX); do
        sleep 1
        if curl -sf -H "$OMLX_CHECK_HEADER" "$OMLX_CHECK_URL" > /dev/null 2>&1; then
            echo "[${TIMESTAMP}] ✅ oMLX 启动完成（${i}s）"
            break
        fi
        if [ $i -eq $OMLX_WAIT_MAX ]; then
            echo "[${TIMESTAMP}] ❌ oMLX 启动超时（${OMLX_WAIT_MAX}s），放弃本次更新"
            exit 1
        fi
    done
fi

# ═══════════════════════════════════════════════════════════
# 2. 统计更新前 chroma 文件数
# ═══════════════════════════════════════════════════════════
BEFORE=0
if [ -d "$AGENT_SYNC/04_memory/vector_db/chroma" ]; then
    BEFORE=$(find "$AGENT_SYNC/04_memory/vector_db/chroma" -name "*.chroma.sqlite3" 2>/dev/null | wc -l)
fi

# ═══════════════════════════════════════════════════════════
# 3. 执行增量回填
# ═══════════════════════════════════════════════════════════
echo "[${TIMESTAMP}] 🔄 执行增量回填..."
cd "$SKILL_DIR"
OUTPUT=$($PYTHON semantic_search.py --root "$AGENT_SYNC" backfill 2>&1)
EXIT_CODE=$?

# ═══════════════════════════════════════════════════════════
# 4. 统计结果
# ═══════════════════════════════════════════════════════════
SUCCESS=$(echo "$OUTPUT" | grep -c "\[OK\]" || true)
FAIL=$(echo "$OUTPUT" | grep -c "\[FAIL\]" || true)
echo "$OUTPUT" >> "$LOG_FILE"

if [ $EXIT_CODE -eq 0 ]; then
    echo "[${TIMESTAMP}] ✅ 向量库更新完成 (成功: $SUCCESS, 失败: $FAIL)"
    echo "[${TIMESTAMP}]  更新前 chroma 文件数: $BEFORE"
else
    echo "[${TIMESTAMP}] ❌ 向量库更新异常 (code=$EXIT_CODE)"
fi

echo "[${TIMESTAMP}] 📝 日志已保存: $LOG_FILE"
echo "[${TIMESTAMP}] 🏁 结束"
