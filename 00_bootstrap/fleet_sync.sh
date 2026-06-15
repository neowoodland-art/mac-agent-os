#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# fleet_sync.sh — AgentOS 联邦一键同步脚本 (v1.0)
# 功能: 一条命令让所有机器 git pull + 环境检查 + 状态报告
# 用法: bash 00_bootstrap/fleet_sync.sh
# 
# 依赖:
#   - Tailscale 网络 (所有机器在同一网络)
#   - SSH 密钥已加入各机器 authorized_keys
#   - ORACLE.yaml 定义了所有机器信息
# ═══════════════════════════════════════════════════════════════

set -e

# ── 配置 ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORACLE="$SCRIPT_DIR/ORACLE.yaml"
PARALLEL=true

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

ok()   { echo -e "  ${GREEN}✅${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠️${NC} $1"; }
fail() { echo -e "  ${RED}❌${NC} $1"; }
info() { echo -e "  ${CYAN}ℹ️${NC} $1"; }

# ── 读取 ORACLE 获取机器信息 ──
echo ""
echo "═══════════════════════════════════════════════"
echo "  🚀 AgentOS 联邦同步"
echo "═══════════════════════════════════════════════"
echo ""

if [ ! -f "$ORACLE" ]; then
    fail "ORACLE.yaml 不存在: $ORACLE"
    exit 1
fi

# 用 Python 从 ORACLE 解析机器信息
MACHINES=$(python3 -c "
import yaml, json
d = yaml.safe_load(open('$ORACLE'))
machines = []
for name, info in d.get('machines', {}).items():
    machines.append({
        'name': name,
        'hostname': info.get('hostname', name),
        'tailscale_ip': info.get('tailscale_ip', ''),
        'user': info.get('ssh_user', ''),
    })
print(json.dumps(machines))
")

# 解析本机名
LOCAL_HOSTNAME=$(hostname)

# 同步每个远程机器
sync_machine() {
    local name="$1"
    local ip="$2"
    local user="$3"
    
    echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  📡 $name ($ip)"
    echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # SSH 执行同步
    local result
    result=$(ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 \
        "$user@$ip" '
        export AGENT_SYNC="$HOME/workbuddy-agent-os/agent-sync"
        export AGENT_LOCAL="$HOME/workbuddy-agent-os/agent-local"
        
        echo "SYNC_START"
        
        # 1. 环境变量检查
        if [ -f ~/.zshrc ] && grep -q "AGENT_SYNC" ~/.zshrc 2>/dev/null; then
            echo "ENV_OK"
        else
            echo "ENV_MISSING"
        fi
        
        # 2. git pull
        cd "$AGENT_SYNC" 2>/dev/null && {
            git pull origin main --rebase 2>&1 | tail -1
            echo "GIT_VERSION:$(git log --oneline -1 2>/dev/null)"
        } || echo "GIT_FAIL"
        
        # 3. 目录检查
        for d in "$AGENT_SYNC" "$AGENT_LOCAL"; do
            if [ -d "$d" ]; then echo "DIR_OK:$d"; else echo "DIR_FAIL:$d"; fi
        done
        
        # 4. 关键文件检查
        for f in "$AGENT_SYNC/ORACLE.yaml" "$AGENT_LOCAL/config.yaml"; do
            if [ -f "$f" ]; then echo "FILE_OK:$f"; else echo "FILE_FAIL:$f"; fi
        done
        
        # 5. Dashboard 状态
        local dash
        dash=$(curl -s --connect-timeout 3 http://localhost:9988/api/identity 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin).get('hostname',''))" 2>/dev/null)
        if [ -n "$dash" ]; then
            echo "DASH_OK:$dash"
        else
            echo "DASH_FAIL"
        fi
        
        echo "SYNC_END"
        ' 2>&1)
    
    local exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        fail "$name — SSH 连接失败 (exit=$exit_code)"
        return 1
    fi
    
    # 解析结果
    local env_ok=false dir_ok=true file_ok=true dash_ok=false git_ver=""
    while IFS= read -r line; do
        case "$line" in
            ENV_OK)      env_ok=true ;;
            ENV_MISSING) warn "$name — 环境变量 AGENT_SYNC 未在 .zshrc 中配置" ;;
            GIT_VERSION:*) git_ver="${line#GIT_VERSION:}" ;;
            GIT_FAIL)    fail "$name — Git 仓库不存在" ;;
            DIR_OK:*)    ;;
            DIR_FAIL:*)  fail "$name — 目录缺失: ${line#DIR_FAIL:}"; dir_ok=false ;;
            FILE_OK:*)   ;;
            FILE_FAIL:*) fail "$name — 文件缺失: ${line#FILE_FAIL:}"; file_ok=false ;;
            DASH_OK:*)   dash_ok=true ;;
            DASH_FAIL)   warn "$name — Dashboard 未运行" ;;
            Already|Updating|Successfully|From*) ;;
            SYNC_START|SYNC_END) ;;
        esac
    done <<< "$result"
    
    # 总结
    if $env_ok && $dir_ok && $file_ok; then
        ok "$name — 同步完成"
        [ -n "$git_ver" ] && echo "       Git: $git_ver"
        $dash_ok && echo "       Dashboard: ✅ 运行中" || echo "       Dashboard: ⚠️ 未运行"
    else
        warn "$name — 部分异常，请检查"
    fi
}

# 同步本机
sync_local() {
    echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  🖥️  本机 ($LOCAL_HOSTNAME)"
    echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 1. 环境变量
    if [ -n "$AGENT_SYNC" ]; then
        ok "环境变量 AGENT_SYNC=$AGENT_SYNC"
    elif [ -f ~/.zshrc ] && grep -q "AGENT_SYNC" ~/.zshrc 2>/dev/null; then
        warn "环境变量已配置但未生效，请执行: source ~/.zshrc"
    else
        warn "环境变量未配置"
    fi
    
    # 2. git pull
    cd "$SCRIPT_DIR" 2>/dev/null
    if git pull origin main --rebase 2>&1 | grep -q "Already up to date"; then
        ok "Git 已是最新: $(git log --oneline -1)"
    else
        ok "Git 已更新: $(git log --oneline -1)"
    fi
    
    # 3. 目录检查
    local sync_dir="$SCRIPT_DIR"
    local local_dir="${AGENT_LOCAL:-$HOME/workbuddy-agent-os/agent-local}"
    test -d "$sync_dir" && ok "agent-sync: ✅" || fail "agent-sync: ❌"
    test -d "$local_dir" && ok "agent-local: ✅" || fail "agent-local: ❌"
    
    # 4. 文件检查
    test -f "$sync_dir/ORACLE.yaml" && ok "ORACLE.yaml: ✅" || fail "ORACLE.yaml: ❌"
    test -f "$local_dir/config.yaml" && ok "config.yaml: ✅" || fail "config.yaml: ❌"
    
    # 5. Dashboard
    local dash
    dash=$(curl -s --connect-timeout 2 http://localhost:9988/api/identity 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin).get('hostname',''))" 2>/dev/null)
    if [ -n "$dash" ]; then
        ok "Dashboard: ✅ ($dash)"
    else
        warn "Dashboard: 未运行"
    fi
}

# ── 主流程 ──
sync_local

echo ""
echo "  ─────────────────────────────────────────"
echo ""

# 解析机器列表并逐个同步
REMOTE_COUNT=0
while IFS= read -r line; do
    name=$(echo "$line" | python3 -c "import sys,json;print(json.load(sys.stdin).get('name',''))")
    ip=$(echo "$line" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tailscale_ip',''))")
    user=$(echo "$line" | python3 -c "import sys,json;print(json.load(sys.stdin).get('user',''))")
    
    # 跳过本机
    if [ "$(echo "$line" | python3 -c "import sys,json;print(json.load(sys.stdin).get('hostname',''))")" = "$LOCAL_HOSTNAME" ]; then
        continue
    fi
    
    if [ -n "$ip" ] && [ -n "$user" ]; then
        sync_machine "$name" "$ip" "$user"
        REMOTE_COUNT=$((REMOTE_COUNT + 1))
        echo ""
    fi
done < <(echo "$MACHINES" | python3 -c "
import sys, json
machines = json.load(sys.stdin)
for m in machines:
    print(json.dumps(m))
")

# ── 汇总 ──
echo "═══════════════════════════════════════════════"
echo "  同步完成"
echo "═══════════════════════════════════════════════"
echo ""
ok "本机: $LOCAL_HOSTNAME"
ok "远程机器: $REMOTE_COUNT 台已同步"
echo ""
echo "  如果一切正常，所有机器的代码和配置现在是一致的。"
echo "  如果某台机器报 ❌，请检查 SSH 连接或手动登录处理。"
echo ""
