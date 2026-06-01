#!/bin/bash
# ─────────────────────────────────────────────────
# 多机同步脚本 — 拉取最新代码 + 重建依赖
# 在 7kecheng / 5kechengdeAir 上各执行一次
# ─────────────────────────────────────────────────

set -e
echo "════════════════════════════════════════"
echo " AgentOS 多机同步 $(date '+%Y-%m-%d %H:%M')"
echo "════════════════════════════════════════"

# ── 1. 拉取最新代码 ──
echo ""
echo "=== 1. 拉取最新代码 ==="
cd ~/workbuddy-agent-os/agent-sync
git pull --rebase origin main
echo "   ✅ 代码已更新 ($(git log --oneline -1))"

# ── 2. 重建 Dashboard venv ──
echo ""
echo "=== 2. 重建 Dashboard venv ==="
VENV=~/.workbuddy/binaries/python/envs/dashboard
rm -rf "$VENV"

# 使用 managed Python 3.13（如果不可用则用 system Python）
PY_BIN=~/.workbuddy/binaries/python/versions/3.13.12/bin/python3
if [ ! -f "$PY_BIN" ]; then
    PY_BIN=/usr/bin/python3
fi
echo "   使用 Python: $($PY_BIN --version)"

$PY_BIN -m venv "$VENV"
$VENV/bin/pip install fastapi uvicorn pyyaml -q
echo "   ✅ Dashboard venv 就绪"

# ── 3. 更新 launchd 配置 ──
echo ""
echo "=== 3. 更新 launchd 配置 ==="
# Dashboard
cp ~/workbuddy-agent-os/agent-sync/05_tools/00_setup/guardd/com.agentos.dashboard.plist \
   ~/Library/LaunchAgents/com.agentos.dashboard.plist 2>/dev/null || true

# SOCKS5 转发器
cp ~/workbuddy-agent-os/agent-sync/05_tools/00_setup/guardd/com.agentos.socks5-forwarder.plist \
   ~/Library/LaunchAgents/com.agentos.socks5-forwarder.plist 2>/dev/null || true

echo "   ✅ launchd 配置已更新"

# ── 4. 重启服务 ──
echo ""
echo "=== 4. 重启服务 ==="
# 重启 Dashboard
launchctl bootout gui/$(id -u)/com.agentos.dashboard 2>/dev/null || true
sleep 1
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.agentos.dashboard.plist 2>/dev/null || \
launchctl load ~/Library/LaunchAgents/com.agentos.dashboard.plist 2>/dev/null || true

# guardd 下次心跳会自动更新
echo "   ✅ 服务已重启"

# ── 5. 验证 ──
echo ""
echo "=== 5. 验证 ==="
sleep 3
curl -s http://localhost:9988/api/machines 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'   Dashboard: {d[\"total\"]} 台机器在线')
for m in d['machines']:
    print(f'     {m[\"hostname\"]:20s} {m[\"status\"]}')
" 2>/dev/null || echo "   ⚠️ Dashboard 启动中，稍后刷新 http://localhost:9988"

echo ""
echo "════════════════════════════════════════"
echo " ✅ 同步完成！"
echo "════════════════════════════════════════"
