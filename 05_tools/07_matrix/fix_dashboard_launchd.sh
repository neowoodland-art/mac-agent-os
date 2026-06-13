#!/bin/bash
# 修复 Dashboard launchd 配置
# 自动检测当前机器的 Python 路径并更新 plist
# 用法: bash fix_dashboard_launchd.sh

PLIST="$HOME/Library/LaunchAgents/com.agentos.dashboard.plist"

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

echo "🔍 检测到 Python: $PYTHON"

# 停止旧服务
echo "🛑 停止旧服务..."
launchctl bootout gui/$(id -u)/com.agentos.dashboard 2>/dev/null || true

# 生成新的 plist
DASHBOARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../10_dashboard"

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

echo "✅ plist 已更新: $PLIST"

# 启动服务
echo "🚀 启动服务..."
launchctl bootstrap gui/$(id -u) "$PLIST" 2>/dev/null || \
launchctl kickstart -k gui/$(id -u)/com.agentos.dashboard 2>/dev/null || true

echo "✅ Dashboard 已启动"
echo "   访问: http://localhost:9988"
echo "   日志: /tmp/dashboard_launchd.log"
