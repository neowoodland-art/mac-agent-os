#!/bin/bash
# ==============================================================
# Matrix 初始化脚本 v5.2
# 新机部署 & 旧版升级 通用
#
# 用法:
#   bash init_matrix.sh              # 完整初始化
#   bash init_matrix.sh --upgrade    # 仅升级（保留配置）
#   bash init_matrix.sh --fix-python # 仅修复 Python 路径
# ==============================================================

set -e
MODE="${1:-full}"

echo "╔══════════════════════════════════════════════════╗"
echo "║     Matrix 初始化脚本 v5.2                      ║"
echo "╚══════════════════════════════════════════════════╝"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_SYNC_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
AGENT_LOCAL_DIR="$HOME/workbuddy-agent-os/agent-local"
MATRIX_CODE="$AGENT_SYNC_DIR/05_tools/07_matrix"

# ═══════════════════════════════════════════════════════════
# 0. 检测环境
# ═══════════════════════════════════════════════════════════
echo ""
echo "📋 [0/8] 检测环境..."
echo "  脚本目录: $SCRIPT_DIR"
echo "  代码目录: $AGENT_SYNC_DIR"
echo "  本地数据: $AGENT_LOCAL_DIR"

# 检测 Python
PYTHON=""
if [ -f "$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3" ]; then
    PYTHON="$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3"
elif [ -f "$HOME/.workbuddy/binaries/python/envs/dashboard/bin/python" ]; then
    PYTHON="$HOME/.workbuddy/binaries/python/envs/dashboard/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="$(which python3)"
else
    echo "❌ 找不到 Python 3"
    exit 1
fi
echo "  Python: $PYTHON ($($PYTHON --version 2>&1))"

# ═══════════════════════════════════════════════════════════
# 1. 拉取代码
# ═══════════════════════════════════════════════════════════
echo ""
echo "📦 [1/8] 拉取最新代码..."
cd "$AGENT_SYNC_DIR"
if git pull 2>/dev/null; then
    echo "  ✅ 代码已更新"
else
    echo "  ⚠️  git pull 失败，尝试克隆..."
    cd "$HOME/workbuddy-agent-os"
    rm -rf agent-sync
    git clone git@github.com:neowoodland-art/mac-agent-os.git agent-sync 2>/dev/null || \
    git clone git@gitee.com:babycalf/mac-agent-os.git agent-sync
    echo "  ✅ 代码已克隆"
    cd "$AGENT_SYNC_DIR"
fi

# ═══════════════════════════════════════════════════════════
# 2. 创建目录结构
# ═══════════════════════════════════════════════════════════
echo ""
echo "📁 [2/8] 创建目录结构..."
mkdir -p "$AGENT_LOCAL_DIR/tools/matrix/config"
mkdir -p "$AGENT_LOCAL_DIR/tools/matrix/identities"
mkdir -p "$AGENT_LOCAL_DIR/tools/matrix/data"
mkdir -p "$AGENT_LOCAL_DIR/tools/matrix/recordings"
mkdir -p "$AGENT_LOCAL_DIR/tools/matrix/logs"
echo "  ✅ 目录已就绪"

# ═══════════════════════════════════════════════════════════
# 3. 安装 Python 依赖
# ═══════════════════════════════════════════════════════════
echo ""
echo "📦 [3/8] 安装 Python 依赖..."
$PYTHON -m pip install -q --upgrade pip 2>/dev/null || true
$PYTHON -m pip install -q httpx pyyaml requests 2>/dev/null || true
$PYTHON -m pip install -q fastapi uvicorn 2>/dev/null || true
$PYTHON -m pip install -q playwright 2>/dev/null || true

# 安装 matrix 依赖
if [ -f "$MATRIX_CODE/requirements.txt" ]; then
    $PYTHON -m pip install -q -r "$MATRIX_CODE/requirements.txt" 2>/dev/null || true
fi

# 检测 Camoufox
CAMOUFOX_PATH="$($PYTHON -m camoufox path 2>/dev/null || true)"
if [ -z "$CAMOUFOX_PATH" ]; then
    echo "  📥 安装 Camoufox..."
    $PYTHON -m pip install -q camoufox
    $PYTHON -m camoufox fetch 2>&1 | tail -1 || true
else
    echo "  ✅ Camoufox: $CAMOUFOX_PATH"
fi

# ═══════════════════════════════════════════════════════════
# 4. 创建/更新配置
# ═══════════════════════════════════════════════════════════
echo ""
echo "⚙️  [4/8] 创建配置文件..."

# accounts.yaml
if [ ! -f "$AGENT_LOCAL_DIR/tools/matrix/config/accounts.yaml" ]; then
    cp "$MATRIX_CODE/config_template/accounts.yaml" \
       "$AGENT_LOCAL_DIR/tools/matrix/config/accounts.yaml"
    echo "  ✅ accounts.yaml 已创建（请编辑填入你的账号）"
else
    echo "  ⏭ accounts.yaml 已存在"

    # 检查旧版格式：identity_dir 是否为非 phone_ 开头的格式
    if grep -q "identity_dir: douyin_\|identity_dir: identities/" "$AGENT_LOCAL_DIR/tools/matrix/config/accounts.yaml" 2>/dev/null; then
        echo "  ⚠️  检测到旧版格式，建议迁移到共享身份格式"
        echo "     新注册的账号会自动使用 phone_ 开头的共享身份目录"
        echo "     现有账号不受影响"
    fi
fi

# sms.yaml（短信API）
if [ ! -f "$MATRIX_CODE/config/sms.yaml" ]; then
    cp "$MATRIX_CODE/config_template/sms.yaml" "$MATRIX_CODE/config/sms.yaml" 2>/dev/null || true
    echo "  ✅ sms.yaml 已创建"
else
    echo "  ⏭ sms.yaml 已存在"
fi

# ai.yaml（AI评论）
if [ ! -f "$MATRIX_CODE/config/ai.yaml" ]; then
    cp "$MATRIX_CODE/config_template/ai.yaml" "$MATRIX_CODE/config/ai.yaml" 2>/dev/null || true
    echo "  ✅ ai.yaml 已创建（不配API key则AI禁用）"
else
    echo "  ⏭ ai.yaml 已存在"
fi

# schedule.yaml（定时任务）
if [ ! -f "$MATRIX_CODE/config/schedule.yaml" ]; then
    cp "$MATRIX_CODE/config_template/schedule.yaml" "$MATRIX_CODE/config/schedule.yaml" 2>/dev/null || true
    echo "  ✅ schedule.yaml 已创建"
else
    echo "  ⏭ schedule.yaml 已存在"
fi

# profiles.json（人设数据）
if [ ! -f "$AGENT_LOCAL_DIR/tools/matrix/data/profiles.json" ]; then
    cp "$MATRIX_CODE/config_template/profiles.json" \
       "$AGENT_LOCAL_DIR/tools/matrix/data/profiles.json" 2>/dev/null || true
    echo "  ✅ profiles.json 已创建（请编辑填入人设）"
else
    echo "  ⏭ profiles.json 已存在"
fi

# ═══════════════════════════════════════════════════════════
# 5. 修复 mc 命令
# ═══════════════════════════════════════════════════════════
echo ""
echo "🔧 [5/8] 修复 mc 命令..."
if [ ! -f /usr/local/bin/mc ] || [ "$(readlink /usr/local/bin/mc 2>/dev/null)" != "$MATRIX_CODE/mc" ]; then
    sudo ln -sf "$MATRIX_CODE/mc" /usr/local/bin/mc 2>/dev/null || \
    ln -sf "$MATRIX_CODE/mc" ~/bin/mc 2>/dev/null || \
    echo "  ⚠️  无法创建软链接，请手动: sudo ln -sf $MATRIX_CODE/mc /usr/local/bin/mc"
fi

# 验证 mc 包装器不是旧版硬编码路径
if grep -q "/Users/5kecheng\|/Users/chengzige" "$MATRIX_CODE/mc" 2>/dev/null; then
    echo "  ⚠️  mc 包装器包含硬编码路径，重新从仓库拉取..."
    cd "$AGENT_SYNC_DIR"
    git checkout -- 05_tools/07_matrix/mc
    echo "  ✅ mc 已修复"
else
    echo "  ✅ mc 包装器已使用自动检测路径"
fi

# ═══════════════════════════════════════════════════════════
# 6. 修复 launchd 配置
# ═══════════════════════════════════════════════════════════
echo ""
echo "🚀 [6/8] 修复 Dashboard launchd 配置..."
PLIST="$HOME/Library/LaunchAgents/com.agentos.dashboard.plist"

# 停止旧服务
launchctl bootout gui/$(id -u)/com.agentos.dashboard 2>/dev/null || true

DASHBOARD_DIR="$AGENT_SYNC_DIR/05_tools/10_dashboard"

cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentos.dashboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>app:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>9988</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$DASHBOARD_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/dashboard_launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/dashboard_launchd_err.log</string>
    <key>ThrottleInterval</key>
    <integer>5</integer>
</dict>
</plist>
EOF
echo "  ✅ launchd plist 已更新 (Python: $PYTHON)"

# ═══════════════════════════════════════════════════════════
# 7. 启动验证
# ═══════════════════════════════════════════════════════════
echo ""
echo "🚀 [7/8] 启动 Dashboard..."
launchctl bootstrap gui/$(id -u) "$PLIST" 2>/dev/null || \
launchctl kickstart -k gui/$(id -u)/com.agentos.dashboard 2>/dev/null || true
sleep 5

# 验证
if curl -s http://localhost:9988/api/matrix/recordings/status >/dev/null 2>&1; then
    echo "  ✅ Dashboard 运行正常 (端口 9988)"
else
    echo "  ⚠️  Dashboard 启动可能较慢，查看日志:"
    echo "     tail -20 /tmp/dashboard_launchd.log"
    echo "     tail -20 /tmp/dashboard_launchd_err.log"
fi

# ═══════════════════════════════════════════════════════════
# 8. 验证关键功能
# ═══════════════════════════════════════════════════════════
echo ""
echo "🔍 [8/8] 验证关键功能..."

echo -n "  mc 命令: "
if command -v mc &>/dev/null; then
    echo "✅"
else
    echo "❌ (可用 ./mc 替代)"
fi

echo -n "  蓝图文件: "
if ls "$MATRIX_CODE/blueprints/"*.json 1>/dev/null 2>&1; then
    echo "✅ ($(ls "$MATRIX_CODE/blueprints/"*.json 2>/dev/null | wc -l)个)"
else
    echo "❌"
fi

echo -n "  语料库: "
if [ -f "$MATRIX_CODE/corpus/douyin.yaml" ]; then
    echo "✅"
else
    echo "❌"
fi

echo -n "  mc task 命令: "
if $PYTHON -c "from mc.task import Task" 2>/dev/null; then
    echo "✅"
else
    echo "❌"
fi

echo -n "  定时调度器: "
if $PYTHON -c "from mc.scheduler import load_schedules" 2>/dev/null; then
    echo "✅"
else
    echo "❌"
fi

echo -n "  人设系统: "
if $PYTHON -c "from mc.corpus import CorpusManager; cm = CorpusManager(); print(cm.get_persona('test'))" 2>/dev/null; then
    echo "✅"
else
    echo "✅ (基础)"
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   ✅ 初始化完成                                 ║"
echo "║                                                 ║"
echo "║   Dashboard: http://localhost:9988              ║"
echo "║   查看日志:  tail -f /tmp/dashboard_launchd.log  ║"
echo "║                                                 ║"
echo "║   下一步:                                       ║"
echo "║   1. 编辑账号: $AGENT_LOCAL_DIR/tools/matrix/config/accounts.yaml"
echo "║   2. 编辑人设: $AGENT_LOCAL_DIR/tools/matrix/data/profiles.json"
echo "║   3. 扫码登录: mc account login <账号ID>         ║"
echo "║   4. 开始养号: mc run --accounts douyin_test --blueprints douyin_daily --rounds 3"
echo "╚══════════════════════════════════════════════════╝"
