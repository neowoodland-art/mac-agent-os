#!/bin/bash
# deploy.sh — AgentOS 一键部署脚本
# 其他机器在 git pull 后运行此脚本，即可同步本机所有变更
# 用法: bash 00_bootstrap/deploy.sh
# 目标: 在其他机器上运行一次，环境变量 → 本地配置 → 依赖检查 → 全部就绪

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_SYNC="$(cd "$SCRIPT_DIR/.." && pwd)"

info() { echo -e "\033[36m[INFO]\033[0m $1"; }
ok()   { echo -e "\033[32m[OK]\033[0m $1"; }
warn() { echo -e "\033[33m[WARN]\033[0m $1"; }
err()  { echo -e "\033[31m[ERROR]\033[0m $1"; }

echo "============================================"
echo "  AgentOS 一键部署脚本"
echo "  仓库: $AGENT_SYNC"
echo "  时间: $(date '+%Y-%m-%d %H:%M')"
echo "============================================"

# ── 步骤1: 设置环境变量 AGENT_SYNC / AGENT_LOCAL ──
echo ""
info "步骤1/5: 设置环境变量..."

if [ -z "$AGENT_SYNC" ]; then
    export AGENT_SYNC="$AGENT_SYNC"
fi
if [ -z "$AGENT_LOCAL" ]; then
    export AGENT_LOCAL="$HOME/workbuddy-agent-os/agent-local"
fi

# 写入 .zshrc
for RC_FILE in "$HOME/.zshrc" "$HOME/.bash_profile"; do
    if [ -f "$RC_FILE" ]; then
        if ! grep -q "export AGENT_SYNC" "$RC_FILE" 2>/dev/null; then
            echo "" >> "$RC_FILE"
            echo "# AgentOS 路径变量（由 deploy.sh 自动添加）" >> "$RC_FILE"
            echo "export AGENT_SYNC=\"$AGENT_SYNC\"" >> "$RC_FILE"
            echo "export AGENT_LOCAL=\"$AGENT_LOCAL\"" >> "$RC_FILE"
            ok "已写入 $RC_FILE"
        else
            ok "$RC_FILE 已有 AGENT_SYNC 设置"
        fi
        break
    fi
done

# ── 步骤2: 创建 agent-local 目录结构 ──
echo ""
info "步骤2/5: 创建本机目录结构..."

mkdir -p "$AGENT_LOCAL/identity"
mkdir -p "$AGENT_LOCAL/memory/raw"
mkdir -p "$AGENT_LOCAL/memory/vector_db"
mkdir -p "$AGENT_LOCAL/memory/daily"
mkdir -p "$AGENT_LOCAL/runtime/cache"
mkdir -p "$AGENT_LOCAL/tools/matrix/config"
mkdir -p "$AGENT_LOCAL/tools/matrix/identities"
mkdir -p "$AGENT_LOCAL/tools/matrix/data"
ok "目录结构已创建"

# ── 步骤3: 创建本地配置（如不存在）──
echo ""
info "步骤3/5: 配置本地参数..."

LOCAL_CONFIG="$AGENT_LOCAL/config.yaml"
if [ ! -f "$LOCAL_CONFIG" ]; then
    HOST="$(hostname)"
    cat > "$LOCAL_CONFIG" << CONFEOF
# agent-local/config.yaml — 本机唯一配置入口
# 此文件每台机器独立，不同步到 Git。覆盖 ORACLE.yaml 中的默认值。

hostname: "$HOST"
machine_uid: ""

# 代理设置（各机器不同）
proxy:
  socks5: "socks5://127.0.0.1:10800"

# 端口分配
ports:
  dashboard: 9988
  camouflage_base: 9200
CONFEOF
    ok "已创建: $LOCAL_CONFIG"
else
    ok "本地配置已存在: $LOCAL_CONFIG"
fi

# ── 步骤4: 检查 Python 和依赖 ──
echo ""
info "步骤4/5: 检查运行环境..."

PYTHON_OK=false
for py in "$AGENT_LOCAL/../.workbuddy/binaries/python/envs/agent-os/bin/python3" \
          "$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3" \
          "/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3" \
          "/usr/local/bin/python3" "/usr/bin/python3"; do
    if [ -x "$py" ]; then
        VER=$("$py" --version 2>&1)
        info "Python: $VER ($py)"
        PYTHON_OK=true
        break
    fi
done

if [ "$PYTHON_OK" = false ]; then
    warn "未找到可用的 Python 3。请先安装 WorkBuddy 或 Python 3.13+"
fi

# 检查关键依赖
if [ "$PYTHON_OK" = true ]; then
    # 找可用的 pip
    for py in "$HOME/.workbuddy/binaries/python/envs/agent-os/bin/pip3" \
              "$HOME/.workbuddy/binaries/python/versions/3.13.12/bin/pip3" \
              "pip3"; do
        if command -v "$py" &>/dev/null; then
            PIP="$py"
            break
        fi
    done
fi

# ── 步骤5: 同步 ORACLE 和授权 ──
echo ""
info "步骤5/5: 同步配置..."

# 确保 ORACLE.yaml 可读
if [ -f "$AGENT_SYNC/ORACLE.yaml" ]; then
    ok "ORACLE.yaml 已就绪"
else
    warn "ORACLE.yaml 不存在（可能尚未创建）"
fi

# 提醒用户
echo ""
echo "============================================"
ok "部署完成!"
echo ""
echo "  环境变量已写入 shell 配置文件"
echo "  请执行: source ~/.zshrc"
echo ""
echo "  后续步骤:"
echo "  1. 编辑本机配置: vim $AGENT_LOCAL/config.yaml"
echo "  2. 运行 setup_env.sh (如环境变量未生效):"
echo "     source ~/.zshrc && bash $AGENT_SYNC/00_bootstrap/setup_env.sh"
echo "============================================"