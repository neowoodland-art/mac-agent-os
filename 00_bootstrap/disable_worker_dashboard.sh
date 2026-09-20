#!/bin/bash
# disable_worker_dashboard.sh — 停用 worker 机器上的 Dashboard（只保留 guardd）
#
# 背景：Dashboard 是联邦的统一控制平面，**只有 master（chengzigedeAir）运行**；
#       worker 只跑 guardd（:9090 节点代理）。
#       worker 误装 Dashboard 会导致「数据视图分裂」：账号标签/备注等本机数据
#       不跨机同步，同一账号在不同看板显示不同值 → 出现"改了看不到"的困惑。
#
# 用法（在 worker 机器上执行）:
#   bash 00_bootstrap/disable_worker_dashboard.sh
#
# 恢复（如需在 worker 上重新启用）:
#   mv ~/Library/LaunchAgents/com.agentos.dashboard.plist{.disabled,}
#   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.agentos.dashboard.plist

echo "============================================"
echo "  停用本机 Dashboard（保留 guardd）"
echo "  主机: $(hostname)   时间: $(date '+%Y-%m-%d %H:%M')"
echo "============================================"
echo

# ── 安全检查：master 不应执行本脚本（多来源识别，避免 hostname 返回 IP 时误判）──
IDENT="$(hostname) $(scutil --get ComputerName 2>/dev/null) $(scutil --get LocalHostName 2>/dev/null)"
HOSTID_MD="$HOME/workbuddy-agent-os/agent-local/identity/HOST_ID.md"
[ -f "$HOSTID_MD" ] && IDENT="$IDENT $(head -20 "$HOSTID_MD" | tr '\n' ' ')"

IS_MASTER=false
echo "$IDENT" | grep -qiE "chengzige|橙子" && IS_MASTER=true

if [ "$IS_MASTER" = "true" ] && [ "$1" != "--force" ]; then
    echo "⛔ 检测到本机疑似 master（识别串: ${IDENT:0:80}…）"
    echo "   master 必须运行 Dashboard（联邦统一控制平面），已中止。"
    echo
    echo "   若确认要在本机停用（例如本机降级为 worker），请加 --force："
    echo "     bash $0 --force"
    exit 1
fi
[ "$IS_MASTER" = "true" ] && echo "⚠️  master 身份 + --force，继续执行（用户明确要求）" && echo

# ── ① 卸载 launchd 服务 ──
echo "① 卸载 launchd 服务..."
launchctl bootout "gui/$(id -u)/com.agentos.dashboard" 2>&1 | head -2 || echo "   （服务未运行或已卸载）"

# ── ② 禁用 plist（改名保留，不删除）──
echo "② 禁用 plist（改名保留，符合「不删除文件」纪律）..."
PLIST="$HOME/Library/LaunchAgents/com.agentos.dashboard.plist"
if [ -f "$PLIST" ]; then
    mv "$PLIST" "$PLIST.disabled" && echo "   ✅ 已改名为 com.agentos.dashboard.plist.disabled"
else
    echo "   （plist 不存在或已禁用）"
fi

sleep 2

# ── ③ 验证 ──
echo "③ 验证..."
DASH_N=$(ps aux | grep "uvicorn app:app" | grep -v grep | wc -l | tr -d ' ')
GUARDD_N=$(ps aux | grep -c "[g]uardd" | tr -d ' ')
echo "   Dashboard 进程数: $DASH_N   （应为 0）"
echo "   guardd 进程数:    $GUARDD_N   （应 > 0）"
if lsof -i :9988 >/dev/null 2>&1; then
    echo "   ⚠️ 9988 端口仍在监听"
else
    echo "   ✅ 9988 端口已释放"
fi
echo
if [ "$DASH_N" = "0" ] && [ "$GUARDD_N" != "0" ]; then
    echo "✅ 完成：Dashboard 已停用，guardd 正常运行"
    echo "   请统一访问中心看板：http://100.111.43.6:9988"
else
    echo "⚠️ 请检查上述结果（Dashboard 应为 0，guardd 应 > 0）"
fi
