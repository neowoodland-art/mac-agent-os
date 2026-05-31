#!/bin/bash
# ============================================================
# AgentOS 技能导出脚本
# 用途：将指定技能导出为可分发的压缩包
# 使用：cd ~/workbuddy-agent-os/agent-sync/00_bootstrap && bash export_skills.sh <skill_name>
# 示例：bash export_skills.sh memory_manager
# ============================================================

set -euo pipefail

# ---------- 颜色定义 ----------
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }

# ---------- 定位路径 ----------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_OS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_DIR="$AGENT_OS_ROOT/02_skills"
OUTPUT_DIR="$AGENT_OS_ROOT/07_migration/exports"

mkdir -p "$OUTPUT_DIR"

# ---------- 参数检查 ----------
SKILL_NAME="${1:-}"
if [ -z "$SKILL_NAME" ]; then
    echo "用法: bash export_skills.sh <skill_name>"
    echo "可导出的技能:"
    ls -1 "$SKILLS_DIR" | grep -v "_template"
    exit 1
fi

SKILL_PATH="$SKILLS_DIR/$SKILL_NAME"
if [ ! -d "$SKILL_PATH" ]; then
    echo "错误: 技能不存在: $SKILL_NAME"
    exit 1
fi

# ---------- 读取版本号 ----------
VERSION="1.0.0"
if [ -f "$SKILL_PATH/version.json" ]; then
    VERSION="$(python3 -c "import json; print(json.load(open('$SKILL_PATH/version.json')).get('version', '1.0.0'))" 2>/dev/null || echo "1.0.0")"
fi

# ---------- 打包 ----------
ARCHIVE_NAME="${SKILL_NAME}_v${VERSION}.zip"
ARCHIVE_PATH="$OUTPUT_DIR/$ARCHIVE_NAME"

cd "$SKILLS_DIR"
zip -r "$ARCHIVE_PATH" "$SKILL_NAME/" -x "*.pyc" "__pycache__/*" ".DS_Store"
cd - > /dev/null

ok "已导出: $ARCHIVE_PATH"
info "其他人可通过以下命令导入:"
info "  cd ~/workbuddy-agent-os/agent-sync/00_bootstrap && bash import_skills.sh $ARCHIVE_PATH"
