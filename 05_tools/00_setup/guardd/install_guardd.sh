#!/bin/bash
# ═══════════════════════════════════════════════════════════
# guardd — 自动安装/修复脚本
# 适用: 任何联邦机器（自动适配当前用户）
# 用法: bash install_guardd.sh
# ═══════════════════════════════════════════════════════════

set -e

USER_HOME="$HOME"
USER_NAME="$(whoami)"
AGENT_SYNC="$HOME/workbuddy-agent-os/agent-sync"
AGENT_LOCAL="$HOME/workbuddy-agent-os/agent-local"
GUARDD_DIR="$AGENT_SYNC/05_tools/00_setup/guardd"
GUARDD_PY="$GUARDD_DIR/guardd.py"

# 检测 WorkBuddy 管理的 Python
PYTHON_BIN=""
for p in "$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3" \
          "$HOME/.workbuddy/binaries/python/versions/3.13.12/bin/python3" \
          "/usr/bin/python3"; do
    if [ -x "$p" ]; then
        PYTHON_BIN="$p"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "❌ 未找到可用的 Python 3"
    exit 1
fi

echo "════════════════════════════════════════════"
echo " guardd 安装脚本"
echo " 用户: $USER_NAME"
echo " 路径: $AGENT_SYNC"
echo " Python: $PYTHON_BIN"
echo "════════════════════════════════════════════"
echo ""

# ── 1. 创建必要目录 ──
echo "[1/5] 创建运行时目录..."
mkdir -p "$AGENT_LOCAL/identity"
mkdir -p "$AGENT_LOCAL/runtime/guardd"

# ── 2. 修复 guardd.py 的 logger bug（已固化的版本会从仓库同步） ──
echo "[2/5] 检查 guardd.py..."
if [ ! -f "$GUARDD_PY" ]; then
    echo "❌ guardd.py 不存在 — 请先 git pull"
    exit 1
fi

# ── 3. 生成 plist ──
echo "[3/5] 生成 launchd plist..."
PLIST_PATH="$HOME/Library/LaunchAgents/com.agentos.guardd.plist"

cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentos.guardd</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_BIN}</string>
        <string>${GUARDD_PY}</string>
    </array>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${AGENT_LOCAL}/runtime/guardd/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${AGENT_LOCAL}/runtime/guardd/stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:${HOME}/.workbuddy/binaries/python/versions/3.13.12/bin</string>
        <!-- GUARDD_DASHBOARD_URL 已废弃: 改为读 agent-local/config.yaml 中的 dashboard_url
        <key>GUARDD_DASHBOARD_URL</key>
        <string>http://localhost:9988</string>
        -->
    </dict>
    <key>KeepAlive</key>
    <false/>
    <key>ThrottleInterval</key>
    <integer>300</integer>
</dict>
</plist>
EOF
echo "  ✅ plist 已生成: $PLIST_PATH"

# ── 4. 卸载旧服务 ──
echo "[4/5] 卸载旧 guardd 服务..."
launchctl bootout gui/$(id -u)/com.agentos.guardd 2>/dev/null || true
# 兼容旧版 launchctl
launchctl unload "$PLIST_PATH" 2>/dev/null || true
echo "  ✅ 已卸载"

# ── 5. 加载新服务 ──
echo "[5/5] 加载 guardd 服务..."
launchctl bootstrap gui/$(id -u) "$PLIST_PATH" 2>/dev/null || launchctl load "$PLIST_PATH"
echo "  ✅ 已加载"

echo ""
echo "════════════════════════════════════════════"
echo " ✅ 安装完成！"
echo "════════════════════════════════════════════"
echo ""
echo "查看状态: launchctl print gui/$(id -u)/com.agentos.guardd | grep state"
echo "查看日志: tail -f $AGENT_LOCAL/runtime/guardd/stdout.log"
echo ""
echo "如需卸载:"
echo "  launchctl bootout gui/$(id -u)/com.agentos.guardd"
echo "  rm ~/Library/LaunchAgents/com.agentos.guardd.plist"
