#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# fleet_reconcile.sh — AgentOS 联邦对账引擎 (v1.0)
# 功能: 本机读取 ORACLE → 检查自己该执行的任务 → 报告不一致
# 用法: bash 00_bootstrap/fleet_reconcile.sh
# 
# 自动对账流程:
#   1. 读 ORACLE.yaml → 找到本机定义
#   2. 检查本机环境变量、目录、文件是否就绪
#   3. 检查 ORACLE 中本机该执行的任务是否在运行
#   4. 输出对账报告
# ═══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORACLE="$SCRIPT_DIR/ORACLE.yaml"
LOCAL_HOSTNAME=$(hostname)

# 查找可用 Python（优先 agent-os 虚拟环境）
if [ -f "$SCRIPT_DIR/.venv/bin/python3" ]; then
    PYTHON="$SCRIPT_DIR/.venv/bin/python3"
elif [ -f "$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3" ]; then
    PYTHON="$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3"
else
    PYTHON="python3"
fi

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✅${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠️${NC} $1"; }
fail() { echo -e "  ${RED}❌${NC} $1"; }
info() { echo -e "  ${CYAN}ℹ️${NC} $1"; }

echo ""
echo "═══════════════════════════════════════════════"
echo "  📋 AgentOS 联邦对账"
echo "═══════════════════════════════════════════════"
echo ""

# ── 1. 检查 ORACLE ──
if [ ! -f "$ORACLE" ]; then
    fail "ORACLE.yaml 不存在"
    exit 1
fi
ok "ORACLE.yaml 已读取"

# ── 2. 本机身份 ──
# 在 ORACLE 中找到本机
MACHINE_INFO=$($PYTHON -c "
import yaml
d = yaml.safe_load(open('$ORACLE'))
hostname = '$LOCAL_HOSTNAME'
for name, info in d.get('machines', {}).items():
    if info.get('hostname') == hostname or name == hostname:
        print(yaml.dump({name: info}, default_flow_style=False))
        break
else:
    print('NOT_FOUND')
")

if [ "$MACHINE_INFO" = "NOT_FOUND" ]; then
    warn "本机 ($LOCAL_HOSTNAME) 未在 ORACLE 中找到，可能是一台新机器"
    info "如需加入联邦，请在 ORACLE.yaml 中添加本机定义"
else
    ok "本机身份: $LOCAL_HOSTNAME"
    echo "$MACHINE_INFO" | head -6 | sed 's/^/  /'
fi

# ── 3. 环境变量对账 ──
echo ""
echo "━━━ 3. 运行环境 ━━━"

# AGENT_SYNC
if [ -n "$AGENT_SYNC" ]; then
    ok "AGENT_SYNC=$AGENT_SYNC"
elif grep -q "AGENT_SYNC" ~/.zshrc 2>/dev/null; then
    warn "AGENT_SYNC 已配置但未生效，请执行: source ~/.zshrc"
    info "设置临时变量: export AGENT_SYNC=\"\$HOME/workbuddy-agent-os/agent-sync\""
    export AGENT_SYNC="$HOME/workbuddy-agent-os/agent-sync"
else
    warn "AGENT_SYNC 未配置"
    info "写入 .zshrc: bash $SCRIPT_DIR/00_bootstrap/setup_env.sh && source ~/.zshrc"
fi

# AGENT_LOCAL
if [ -z "$AGENT_LOCAL" ]; then
    export AGENT_LOCAL="$HOME/workbuddy-agent-os/agent-local"
fi
ok "AGENT_LOCAL=${AGENT_LOCAL:-$HOME/workbuddy-agent-os/agent-local}"

# ── 4. 目录结构 ──
echo ""
echo "━━━ 4. 目录结构 ━━━"

SYNC_DIR="${AGENT_SYNC:-$SCRIPT_DIR}"
LOCAL_DIR="${AGENT_LOCAL:-$HOME/workbuddy-agent-os/agent-local}"

test -d "$SYNC_DIR" && ok "agent-sync: ✅" || fail "agent-sync: ❌ 不存在"
test -d "$LOCAL_DIR" && ok "agent-local: ✅" || {
    fail "agent-local: ❌ 不存在"
    mkdir -p "$LOCAL_DIR" && ok "  → 已自动创建"
}

# ── 5. 关键文件 ──
echo ""
echo "━━━ 5. 关键文件 ━━━"

test -f "$SYNC_DIR/ORACLE.yaml" && ok "ORACLE.yaml: ✅" || fail "ORACLE.yaml: ❌"
test -f "$LOCAL_DIR/config.yaml" && ok "config.yaml: ✅" || {
    warn "config.yaml: ❌ 不存在"
    info "正在创建默认配置..."
    $PYTHON -c "
import yaml
config = {
    'hostname': '$LOCAL_HOSTNAME',
    'proxy': {'socks5': 'socks5://127.0.0.1:10800', 'http': ''},
    'ports': {'dashboard': 9988, 'camouflage_base': 9200},
}
with open('$LOCAL_DIR/config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)
print('  -> 已创建默认 config.yaml')
"
}

# ── 6. Git 状态 ──
echo ""
echo "━━━ 6. Git 状态 ━━━"

if cd "$SYNC_DIR" 2>/dev/null; then
    GIT_LOG=$(git log --oneline -1 2>/dev/null)
    GIT_STATUS=$(git status --short 2>/dev/null | head -3)
    ok "仓库: $(basename $(git rev-parse --show-toplevel 2>/dev/null))"
    info "最新提交: $GIT_LOG"
    if [ -n "$GIT_STATUS" ]; then
        warn "有未提交的更改:"
        echo "$GIT_STATUS" | while read line; do echo "    $line"; done
    else
        ok "工作区干净"
    fi
else
    fail "Git 仓库不可用"
fi

# ── 7. Dashboard ──
echo ""
echo "━━━ 7. 服务状态 ━━━"

DASH=$(curl -s --connect-timeout 3 http://localhost:9988/api/identity 2>/dev/null)
if [ -n "$DASH" ]; then
    HOST=$(echo "$DASH" | $PYTHON -c "import sys,json;print(json.load(sys.stdin).get('hostname','?'))" 2>/dev/null)
    ok "Dashboard: ✅ 运行中 ($HOST:9988)"
else
    warn "Dashboard: ❌ 未运行"
    info "启动: cd \$SYNC_DIR/05_tools/10_dashboard && \$PYTHON run.py 9988 &"
fi

# ── 8. ORACLE 中本机的任务检查 ──
echo ""
echo "━━━ 8. 任务对账 ━━━"

$PYTHON -c "
import yaml, json, os, subprocess
d = yaml.safe_load(open('$ORACLE'))
hostname = '$LOCAL_HOSTNAME'

# 找本机的机器名
my_name = None
for name, info in d.get('machines', {}).items():
    if info.get('hostname') == hostname or name == hostname:
        my_name = name
        break

if not my_name:
    print('  ⚠️ 本机未在 ORACLE 中找到任务定义')
else:
    # 找本机该执行的任务
    my_tasks = []
    for t in d.get('tasks', []):
        machines = t.get('on_machines', [])
        if any(my_name in m or hostname in m for m in machines):
            my_tasks.append(t)
    
    if my_tasks:
        print(f'  本机 ({my_name}) 应执行 {len(my_tasks)} 个任务:')
        for t in my_tasks:
            print(f'    - {t[\"name\"]}: {t.get(\"schedule\",\"?\")} → {t.get(\"blueprint\",\"?\")}')
    else:
        print(f'  本机 ({my_name}) 无定时任务')
        print('  (本机可能只负责运行 Dashboard 或按需执行)')
" 2>&1

# ── 汇总 ──
echo ""
echo "═══════════════════════════════════════════════"
echo "  对账完成"
echo "═══════════════════════════════════════════════"
echo ""
echo "  如果全部 ✅，本机已达标。"
echo "  如果有 ⚠️ 或 ❌，请按提示修复。"
echo "  同步所有机器: bash $SCRIPT_DIR/00_bootstrap/fleet_sync.sh"
echo ""
