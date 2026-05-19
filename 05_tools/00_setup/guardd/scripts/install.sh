#!/bin/bash
# guardd 安装脚本 — 动态生成 plist → 部署到 launchd，设置 300 秒周期
# 用法: bash scripts/install.sh
# 多机器兼容：自动探测本机路径，无需手动修改 plist 模板

set -euo pipefail

GUARDD_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_DEST="$HOME/Library/LaunchAgents/com.agentos.guardd.plist"
GUARDD_PY="$GUARDD_DIR/guardd.py"
RUNTIME_DIR="$HOME/workbuddy-agent-os/agent-local/runtime/guardd"

# ── 自动探测 Python ──────────────────────────────────────
# 优先使用 agent-os venv，fallback 到当前 python3
if [ -x "$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3" ]; then
    PYTHON_BIN="$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3"
elif [ -x "$HOME/.workbuddy/binaries/python/envs/default/bin/python3" ]; then
    PYTHON_BIN="$HOME/.workbuddy/binaries/python/envs/default/bin/python3"
else
    PYTHON_BIN=$(command -v python3)
fi
PYTHON_LIB_DIR="$(dirname "$(dirname "$PYTHON_BIN")")/versions/$(basename "$(dirname "$(dirname "$PYTHON_BIN")")")/lib" 2>/dev/null || echo ""

echo "=== guardd 安装脚本 ==="
echo "源目录: $GUARDD_DIR"
echo "Python:  $PYTHON_BIN"

# 1. 检查 guardd.py 是否存在
if [ ! -f "$GUARDD_PY" ]; then
    echo "❌ 未找到 guardd.py: $GUARDD_PY"
    echo "   请确保在 guardd 目录下运行此脚本"
    exit 1
fi

# 2. 创建运行时目录
mkdir -p "$RUNTIME_DIR"
echo "✅ 运行时目录: $RUNTIME_DIR"

# 3. 确保 guardd.py 可执行
chmod +x "$GUARDD_PY"
echo "✅ guardd.py 可执行权限"

# 4. 动态生成 plist（多机器兼容，不依赖静态模板）
cat > "$PLIST_DEST" << PLEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentos.guardd</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$GUARDD_PY</string>
    </array>

    <key>StartInterval</key>
    <integer>300</integer>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>${RUNTIME_DIR}/stdout.log</string>

    <key>StandardErrorPath</key>
    <string>${RUNTIME_DIR}/stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>GUARDD_DASHBOARD_URL</key>
        <string>http://localhost:9988</string>
    </dict>

    <key>KeepAlive</key>
    <false/>

    <key>ThrottleInterval</key>
    <integer>300</integer>
</dict>
</plist>
PLEOF
echo "✅ plist 已动态生成: $PLIST_DEST"

# 5. 卸载旧的 launchd job（如果存在）
launchctl bootout gui/$(id -u)/com.agentos.guardd 2>/dev/null || true

# 6. 加载新 plist
launchctl bootstrap gui/$(id -u) "$PLIST_DEST"
echo "✅ guardd 已加载到 launchd"

# 7. 立即启动一次（测试）
launchctl kickstart -k gui/$(id -u)/com.agentos.guardd
echo "✅ guardd 已启动"

# 8. 验证
sleep 2
if [ -f "$RUNTIME_DIR/last_run.json" ]; then
    echo "✅ guardd 首次运行成功"
    cat "$RUNTIME_DIR/last_run.json"
else
    echo "⏳ guardd 尚未完成首次运行，等待 10 秒..."
    sleep 8
    if [ -f "$RUNTIME_DIR/last_run.json" ]; then
        echo "✅ guardd 首次运行成功"
        cat "$RUNTIME_DIR/last_run.json"
    else
        echo "⚠️ 未检测到 last_run.json，请检查日志: $RUNTIME_DIR/guardd.log"
        if [ -f "$RUNTIME_DIR/stderr.log" ]; then
            echo "--- stderr ---"
            cat "$RUNTIME_DIR/stderr.log"
        fi
    fi
fi

echo ""
echo "=== guardd 安装完成 ==="
echo "查看状态: cat $RUNTIME_DIR/last_run.json"
echo "查看日志: cat $RUNTIME_DIR/guardd.log"
echo "手动卸载: launchctl bootout gui/$(id -u) $PLIST_DEST"
