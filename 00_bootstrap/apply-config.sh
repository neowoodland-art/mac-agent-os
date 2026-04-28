#!/bin/bash
# ============================================================
# AgentOS 核心配置部署脚本
# 用途：将 01_core/ 下的配置文件安全部署到 ~/.workbuddy/
# 使用：cd ~/agent-os/00_bootstrap && bash apply-config.sh
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
CORE_DIR="$AGENT_OS_ROOT/01_core"
WORKBUDDY_DIR="$HOME/.workbuddy"

info "核心配置目录: $CORE_DIR"
info "WorkBuddy 目录: $WORKBUDDY_DIR"

# ---------- 备份旧配置 ----------
BACKUP_DIR="$WORKBUDDY_DIR/backup_$(date +%Y%m%d_%H%M%S)"
CONFIG_FILES=("SOUL.md" "IDENTITY.md" "USER.md" "mcp.json")

NEED_BACKUP=false
for f in "${CONFIG_FILES[@]}"; do
    if [ -f "$WORKBUDDY_DIR/$f" ]; then
        NEED_BACKUP=true
        break
    fi
done

if [ "$NEED_BACKUP" = true ]; then
    info "检测到已有配置文件，创建备份..."
    mkdir -p "$BACKUP_DIR"
    for f in "${CONFIG_FILES[@]}"; do
        if [ -f "$WORKBUDDY_DIR/$f" ]; then
            cp "$WORKBUDDY_DIR/$f" "$BACKUP_DIR/"
            info "已备份: $f → $BACKUP_DIR/$f"
        fi
    done
    ok "旧配置已备份到: $BACKUP_DIR"
fi

# ---------- 确保 .workbuddy 目录存在 ----------
mkdir -p "$WORKBUDDY_DIR"

# ---------- 部署配置文件 ----------
info "部署配置文件到 ~/.workbuddy/ ..."

# SOUL.md
if [ -f "$CORE_DIR/SOUL.md" ]; then
    cp "$CORE_DIR/SOUL.md" "$WORKBUDDY_DIR/SOUL.md"
    ok "SOUL.md 已部署"
fi

# IDENTITY.md
if [ -f "$CORE_DIR/IDENTITY.md" ]; then
    cp "$CORE_DIR/IDENTITY.md" "$WORKBUDDY_DIR/IDENTITY.md"
    ok "IDENTITY.md 已部署"
fi

# USER.md
if [ -f "$CORE_DIR/USER.md" ]; then
    cp "$CORE_DIR/USER.md" "$WORKBUDDY_DIR/USER.md"
    ok "USER.md 已部署"
fi

# mcp.json（合并而非覆盖）
if [ -f "$CORE_DIR/mcp.json" ]; then
    if [ -f "$WORKBUDDY_DIR/mcp.json" ]; then
        # 已存在 mcp.json，提示用户手动合并
        warn "$WORKBUDDY_DIR/mcp.json 已存在"
        warn "请手动合并 $CORE_DIR/mcp.json 中的配置到现有文件"
        info "参考命令: diff $CORE_DIR/mcp.json $WORKBUDDY_DIR/mcp.json"
    else
        cp "$CORE_DIR/mcp.json" "$WORKBUDDY_DIR/mcp.json"
        ok "mcp.json 已部署"
    fi
fi

# ---------- 删除 BOOTSTRAP.md（如果存在且身份已确认） ----------
if [ -f "$WORKBUDDY_DIR/BOOTSTRAP.md" ]; then
    info "检测到 BOOTSTRAP.md，身份已确认"
    if [ "${AUTO_DELETE_BOOTSTRAP:-}" = "yes" ]; then
        rm "$WORKBUDDY_DIR/BOOTSTRAP.md"
        ok "BOOTSTRAP.md 已删除"
    else
        info "如需删除 BOOTSTRAP.md，运行: AUTO_DELETE_BOOTSTRAP=yes bash apply-config.sh"
    fi
fi

echo ""
echo "========================================="
ok "核心配置部署完成！"
echo "========================================="
echo ""
info "配置文件位置: $WORKBUDDY_DIR/"
info "备份位置: ${BACKUP_DIR:-无旧配置，无需备份}"
echo ""
warn "请重启 WorkBuddy 以使配置生效"
