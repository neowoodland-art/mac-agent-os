#!/bin/bash
# ============================================================
# AgentOS 解包还原脚本
# 用途：从打包文件中还原 agent-os 目录
# 使用：bash unpack.sh <archive_path> [target_dir]
# ============================================================

set -euo pipefail

info() { echo "[INFO] $1"; }
ok()   { echo "[OK] $1"; }
err()  { echo "[ERROR] $1"; exit 1; }

ARCHIVE="${1:-}"
TARGET="${2:-$HOME}"

if [ -z "$ARCHIVE" ]; then
    echo "用法: bash unpack.sh <archive_path> [target_dir]"
    echo "示例: bash unpack.sh ./agent-os_20260425_120000.tar.gz ~/"
    exit 1
fi

if [ ! -f "$ARCHIVE" ]; then
    err "文件不存在: $ARCHIVE"
fi

info "解压 $ARCHIVE 到 $TARGET ..."
tar -xzf "$ARCHIVE" -C "$TARGET"
ok "解压完成"

AGENT_OS_DIR="$TARGET/agent-os"
if [ -d "$AGENT_OS_DIR" ]; then
    echo ""
    info "下一步操作："
    echo "  1. cd $AGENT_OS_DIR/00_bootstrap && bash init.sh"
    echo "  2. bash apply-config.sh"
    echo "  3. bash import_skills.sh"
    echo "  4. 用 Obsidian 打开 $AGENT_OS_DIR/03_knowledge/ 作为 Vault"
else
    info "解压完成，请检查目标目录"
fi
