#!/bin/bash
# ============================================================
# AgentOS 技能导入脚本
# 用途：将 02_skills/ 下的自定义技能注册到 WorkBuddy
# 使用：cd ~/workbuddy-agent-os/agent-sync/00_bootstrap && bash import_skills.sh [skill_name]
# 参数：skill_name - 可选，指定导入单个技能；不传则导入全部
# ============================================================

set -euo pipefail

# ---------- 颜色定义 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---------- 定位路径 ----------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_OS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_DIR="$AGENT_OS_ROOT/02_skills"
USER_SKILLS_DIR="$HOME/.workbuddy/skills"
PROJECT_SKILLS_DIR=""

# 尝试找到当前工作区的 .workbuddy/skills 目录
for ws in "$HOME/WorkBuddy"/*; do
    if [ -d "$ws/.workbuddy/skills" ]; then
        PROJECT_SKILLS_DIR="$ws/.workbuddy/skills"
        break
    fi
done

info "技能源目录: $SKILLS_DIR"
info "用户级技能目录: $USER_SKILLS_DIR"

# ---------- 创建目标目录 ----------
mkdir -p "$USER_SKILLS_DIR"

# ---------- 导入技能 ----------
TARGET_SKILL="${1:-}"

import_skill() {
    local skill_dir="$1"
    local skill_name="$(basename "$skill_dir")"
    
    # 跳过模板目录
    if [ "$skill_name" = "_template" ]; then
        return
    fi
    
    # 检查 SKILL.md 是否存在
    if [ ! -f "$skill_dir/SKILL.md" ]; then
        warn "跳过 $skill_name：缺少 SKILL.md"
        return
    fi
    
    # 复制技能到用户级目录
    local dest="$USER_SKILLS_DIR/$skill_name"
    if [ -d "$dest" ]; then
        warn "$skill_name 已存在，更新..."
        rm -rf "$dest"
    fi
    
    cp -r "$skill_dir" "$dest"
    ok "已导入: $skill_name → $dest"
}

if [ -n "$TARGET_SKILL" ]; then
    # 导入指定技能
    if [ -d "$SKILLS_DIR/$TARGET_SKILL" ]; then
        import_skill "$SKILLS_DIR/$TARGET_SKILL"
    else
        err "技能不存在: $TARGET_SKILL"
    fi
else
    # 导入全部技能
    info "扫描技能目录..."
    for skill_dir in "$SKILLS_DIR"/*/; do
        if [ -d "$skill_dir" ]; then
            import_skill "$skill_dir"
        fi
    done
fi

echo ""
echo "========================================="
ok "技能导入完成！"
echo "========================================="
echo ""
info "已导入的技能目录: $USER_SKILLS_DIR/"
info "重启 WorkBuddy 后新技能将生效"
