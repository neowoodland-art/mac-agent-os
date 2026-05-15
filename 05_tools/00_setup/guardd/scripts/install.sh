#!/bin/bash
# guardd 安装脚本 — 部署到 launchd，设置 300 秒周期
# 用法: bash scripts/install.sh

set -euo pipefail

GUARDD_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="$GUARDD_DIR/com.agentos.guardd.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.agentos.guardd.plist"
GUARDD_PY="$GUARDD_DIR/guardd.py"
RUNTIME_DIR="$HOME/workbuddy-agent-os/agent-local/runtime/guardd"

echo "=== guardd 安装脚本 ==="
echo "源目录: $GUARDD_DIR"

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

# 4. 修复 plist 中的路径为绝对路径
#    替换占位符（如果有），否则直接复制
cp "$PLIST_SRC" "$PLIST_DEST"
echo "✅ plist 已部署: $PLIST_DEST"

# 5. 加载到 launchd
launchctl bootout gui/$(id -u) "$PLIST_DEST" 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$PLIST_DEST"
echo "✅ guardd 已加载到 launchd"

# 6. 立即启动一次（测试）
launchctl kickstart -k gui/$(id -u)/com.agentos.guardd
echo "✅ guardd 已启动"

# 7. 验证
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
