#!/bin/bash
# ============================================================
# AgentOS 核心配置部署脚本 v2.0
# 用途：将 01_core/ 下的配置文件安全部署到 ~/.workbuddy/
#       带版本检查 + 多机角色预设
# 使用：cd ~/workbuddy-agent-os/agent-sync/00_bootstrap && bash apply-config.sh
# ============================================================

set -euo pipefail

# ---------- 颜色定义 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
header(){ echo -e "${CYAN}━━━ $1 ━━━${NC}"; }

# ---------- 定位路径 ----------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_OS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CORE_DIR="$AGENT_OS_ROOT/01_core"
WORKBUDDY_DIR="$HOME/.workbuddy"

# ---------- 版本追踪 ----------
VERSION_FILE="$WORKBUDDY_DIR/.config-version.json"
CURRENT_VERSION=$(date +%Y%m%d_%H%M%S)

# 多机角色预设（当前统一版本，后续可按角色分配）
# 角色: unified | main-node | submit-node | media-node
HOST_ROLE="${HOST_ROLE:-unified}"

info "核心配置目录: $CORE_DIR"
info "WorkBuddy 目录: $WORKBUDDY_DIR"
info "本机角色: $HOST_ROLE"

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

# CONSTITUTION.md（架构宪法，按需加载）
if [ -f "$AGENT_OS_ROOT/CONSTITUTION.md" ]; then
    cp "$AGENT_OS_ROOT/CONSTITUTION.md" "$WORKBUDDY_DIR/CONSTITUTION.md"
    ok "CONSTITUTION.md 已部署（架构宪法，WorkBuddy AI 按需加载）"
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

# ---------- 版本追踪 ----------
header "版本信息"

# 写入部署版本记录
cat > "$VERSION_FILE" << VERSIONEOF
{
  "deployed_at": "$CURRENT_VERSION",
  "host_role": "$HOST_ROLE",
  "files": {
    "SOUL.md": "$(md5 -q "$WORKBUDDY_DIR/SOUL.md" 2>/dev/null || echo 'unknown')",
    "IDENTITY.md": "$(md5 -q "$WORKBUDDY_DIR/IDENTITY.md" 2>/dev/null || echo 'unknown')",
    "USER.md": "$(md5 -q "$WORKBUDDY_DIR/USER.md" 2>/dev/null || echo 'unknown')"
  }
}
VERSIONEOF
ok "版本记录已保存: $VERSION_FILE"

# 多机角色提示
if [ "$HOST_ROLE" != "unified" ]; then
    info "本机角色: $HOST_ROLE"
    info "后续可根据角色加载不同的 SOUL.md/IDENTITY.md 变体"
fi

# ---------- 安装 Git pre-push 钩子（防止 --force） ----------
HOOK_SRC="$AGENT_OS_ROOT/00_bootstrap/hooks/pre-push"
HOOK_DST="$AGENT_OS_ROOT/.git/hooks/pre-push"
if [ -f "$HOOK_SRC" ] && [ -d "$(dirname "$HOOK_DST")" ]; then
    cp "$HOOK_SRC" "$HOOK_DST"
    chmod +x "$HOOK_DST"
    ok "Git pre-push 钩子已安装（禁止 --force）"
fi

# ---------- 自动注册到集群 ----------
info "自动注册本机到集群..."
if python3 "$AGENT_OS_ROOT/05_tools/01_system/cluster_registry.py" register 2>/dev/null; then
    ok "集群注册成功"
    info "查看集群状态: agentos cluster-status"
else
    warn "集群注册失败（不影响核心配置）"
fi

echo ""
echo "========================================="
ok "核心配置部署完成（v2.0）！"
echo "========================================="
echo ""
info "配置文件位置: $WORKBUDDY_DIR/"
info "备份位置: ${BACKUP_DIR:-无旧配置，无需备份}"
info "本机角色: $HOST_ROLE"
echo ""
warn "请重启 WorkBuddy 以使配置生效"
