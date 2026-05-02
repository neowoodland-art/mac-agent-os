#!/bin/bash
# ============================================================
# AgentOS 全量打包脚本
# 用途：将整个 agent-os 目录打包为可分享/备份的压缩包
# 使用：cd ~/workbuddy-agent-os/agent-sync/07_migration && bash pack.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_OS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/exports"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
ARCHIVE_NAME="agent-os_${TIMESTAMP}.tar.gz"

mkdir -p "$OUTPUT_DIR"

info() { echo "[INFO] $1"; }
ok()   { echo "[OK] $1"; }

info "正在打包 $AGENT_OS_ROOT ..."

# 排除运行时缓存和虚拟环境
tar -czf "$OUTPUT_DIR/$ARCHIVE_NAME" \
    -C "$(dirname "$AGENT_OS_ROOT")" \
    --exclude="*/cache/*" \
    --exclude="*/.venv/*" \
    --exclude="*/__pycache__/*" \
    --exclude="*/.DS_Store" \
    --exclude="*/node_modules/*" \
    "$(basename "$AGENT_OS_ROOT")"

SIZE="$(du -sh "$OUTPUT_DIR/$ARCHIVE_NAME" | cut -f1)"
ok "打包完成: $OUTPUT_DIR/$ARCHIVE_NAME ($SIZE)"
echo ""
info "其他人可通过以下命令解压："
info "  tar -xzf $ARCHIVE_NAME -C ~/"
info "  cd ~/workbuddy-agent-os/agent-sync/00_bootstrap && bash init.sh"
