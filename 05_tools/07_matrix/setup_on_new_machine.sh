#!/bin/bash
# ==============================================================
# Matrix 新机部署脚本 v5.2
# 在新 Mac 上首次部署时运行一次
# 用法: bash setup_on_new_machine.sh
# ==============================================================

set -e

echo "╔══════════════════════════════════════════════════╗"
echo "║     Matrix 新机部署脚本 v5.2                    ║"
echo "╚══════════════════════════════════════════════════╝"

# ── 1. 检测环境 ──
echo ""
echo "📋 [1/7] 检测环境..."

ARCH=$(uname -m)
echo "  架构: $ARCH"
if [ "$ARCH" != "arm64" ] && [ "$ARCH" != "x86_64" ]; then
    echo "  ⚠️  未知架构: $ARCH，继续..."
fi

# ── 2. 拉取代码 ──
echo ""
echo "📦 [2/7] 拉取代码..."
MATRIX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_SYNC_DIR="$(dirname "$(dirname "$(dirname "$MATRIX_DIR")")")"

if [ -d "$AGENT_SYNC_DIR/.git" ]; then
    echo "  仓库已存在，拉取更新..."
    cd "$AGENT_SYNC_DIR"
    git pull
else
    echo "  首次克隆..."
    cd "$(dirname "$AGENT_SYNC_DIR")"
    git clone git@github.com:neowoodland-art/mac-agent-os.git agent-sync 2>/dev/null || \
    git clone git@gitee.com:babycalf/mac-agent-os.git agent-sync
fi

# ── 3. 创建目录结构 ──
echo ""
echo "📁 [3/7] 创建目录结构..."
AGENT_LOCAL="$HOME/workbuddy-agent-os/agent-local"
mkdir -p "$AGENT_LOCAL/tools/matrix/config"
mkdir -p "$AGENT_LOCAL/tools/matrix/identities"
mkdir -p "$AGENT_LOCAL/tools/matrix/data"
mkdir -p "$AGENT_LOCAL/tools/matrix/recordings"
mkdir -p "$AGENT_LOCAL/tools/matrix/logs"

# ── 4. 创建配置 ──
echo ""
echo "⚙️  [4/7] 创建初始配置..."

# accounts.yaml（从模板复制，如不存在）
if [ ! -f "$AGENT_LOCAL/tools/matrix/config/accounts.yaml" ]; then
    cp "$MATRIX_DIR/config_template/accounts.yaml" \
       "$AGENT_LOCAL/tools/matrix/config/accounts.yaml"
    echo "  ✅ accounts.yaml 已创建（请编辑填入你的账号）"
else
    echo "  ⏭ accounts.yaml 已存在，跳过"
fi

# sms.yaml（短信API配置）
if [ ! -f "$MATRIX_DIR/config/sms.yaml" ]; then
    cp "$MATRIX_DIR/config_template/sms.yaml" \
       "$MATRIX_DIR/config/sms.yaml" 2>/dev/null || true
    echo "  ✅ sms.yaml 已创建"
fi

# ai.yaml（AI评论配置）
if [ ! -f "$MATRIX_DIR/config/ai.yaml" ]; then
    cp "$MATRIX_DIR/config_template/ai.yaml" \
       "$MATRIX_DIR/config/ai.yaml" 2>/dev/null || true
    echo "  ✅ ai.yaml 已创建（不配API key则AI功能禁用）"
fi

# schedule.yaml（定时任务）
if [ ! -f "$MATRIX_DIR/config/schedule.yaml" ]; then
    cp "$MATRIX_DIR/config_template/schedule.yaml" \
       "$MATRIX_DIR/config/schedule.yaml" 2>/dev/null || true
    echo "  ✅ schedule.yaml 已创建"
fi

# profiles.json（人设数据模板）
if [ ! -f "$AGENT_LOCAL/tools/matrix/data/profiles.json" ]; then
    cp "$MATRIX_DIR/config_template/profiles.json" \
       "$AGENT_LOCAL/tools/matrix/data/profiles.json" 2>/dev/null || true
    echo "  ✅ profiles.json 已创建（请编辑填入你的账号人设）"
fi

# ── 5. 检测 Python ──
echo ""
echo "🐍 [5/7] 检测 Python..."
PYTHON=""
if [ -f "$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3" ]; then
    PYTHON="$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3"
    echo "  ✅ agent-os Python: $PYTHON"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
    echo "  ⚠️  使用系统 Python: $(python3 --version)"
else
    echo "  ❌ 未找到 Python 3，请先安装"
    exit 1
fi

# ── 6. 安装 Python 依赖 ──
echo ""
echo "📦 [6/7] 安装 Python 依赖..."
$PYTHON -m pip install -q pyyaml requests httpx 2>/dev/null || true
$PYTHON -m pip install -q -r "$MATRIX_DIR/requirements.txt" 2>/dev/null || true

# 检测 Camoufox
CAMOUFOX_PATH="$($PYTHON -m camoufox path 2>/dev/null || true)"
if [ -z "$CAMOUFOX_PATH" ]; then
    echo "  📥 安装 Camoufox..."
    $PYTHON -m pip install camoufox -q
    $PYTHON -m camoufox fetch 2>&1 | tail -1 || true
else
    echo "  ✅ Camoufox: $CAMOUFOX_PATH"
fi

# ── 7. 安装 mc 命令 ──
echo ""
echo "🔗 [7/7] 安装 mc 命令..."
if [ ! -f /usr/local/bin/mc ]; then
    ln -sf "$MATRIX_DIR/mc" /usr/local/bin/mc 2>/dev/null || \
    echo "  ⚠️  无法创建软链接，请手动: sudo ln -sf $MATRIX_DIR/mc /usr/local/bin/mc"
    echo "  ✅ mc 命令已安装"
else
    echo "  ⏭ mc 已存在"
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   ✅ 部署完成                                   ║"
echo "║                                                 ║"
echo "║   下一步:                                       ║"
echo "║   1. 编辑 accounts.yaml 填入你的账号             ║"
echo "║   2. 编辑 profiles.json 填入人设信息             ║"
echo "║   3. 扫码登录: mc account login <账号ID>         ║"
echo "║   4. 启动看板: 见 start_dashboard.sh             ║"
echo "╚══════════════════════════════════════════════════╝"
