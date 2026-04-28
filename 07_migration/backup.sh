#!/bin/bash
# ============================================================
# AgentOS 备份脚本
# 用途：备份核心配置、记忆体和知识库到指定目录
# 使用：cd ~/agent-os/07_migration && bash backup.sh [backup_dir]
# 说明：日常备份由坚果云自动同步，此脚本用于手动创建额外备份
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_OS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="${1:-$AGENT_OS_ROOT/04_memory/memory_backup}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

info() { echo "[INFO] $1"; }
ok()   { echo "[OK] $1"; }

mkdir -p "$BACKUP_DIR"

TARGET="$BACKUP_DIR/backup_${TIMESTAMP}"
mkdir -p "$TARGET"

info "备份核心配置..."
cp -r "$AGENT_OS_ROOT/01_core/" "$TARGET/01_core/"

info "备份记忆体..."
cp -r "$AGENT_OS_ROOT/04_memory/long_term/" "$TARGET/long_term/" 2>/dev/null || true
cp -r "$AGENT_OS_ROOT/04_memory/vector_db/" "$TARGET/vector_db/" 2>/dev/null || true
cp -r "$AGENT_OS_ROOT/04_memory/daily_summaries/" "$TARGET/daily_summaries/" 2>/dev/null || true

info "备份技能包..."
cp -r "$AGENT_OS_ROOT/02_skills/" "$TARGET/02_skills/"

SIZE="$(du -sh "$TARGET" | cut -f1)"
ok "备份完成: $TARGET ($SIZE)"

# 清理超过 30 天的旧备份
info "清理旧备份（>30天）..."
find "$BACKUP_DIR" -maxdepth 1 -type d -name "backup_*" -mtime +30 -exec rm -rf {} + 2>/dev/null || true
ok "旧备份已清理"
