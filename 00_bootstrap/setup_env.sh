#!/bin/bash
# setup_env.sh — 一键配置 AgentOS 环境变量
# 在任何机器上运行一次即可，后续 init.sh 会自动维护
# 用法: bash 00_bootstrap/setup_env.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
info() { echo -e "\033[36m[INFO]\033[0m $1"; }
ok()   { echo -e "\033[32m[OK]\033[0m $1"; }
warn() { echo -e "\033[33m[WARN]\033[0m $1"; }

# 检测并设置 AGENT_SYNC
if [ -z "$AGENT_SYNC" ]; then
    # 自动检测: 找脚本所在目录的父目录（agent-sync）
    CANDIDATE="$SCRIPT_DIR/.."
    if [ -f "$CANDIDATE/ORACLE.yaml" ] || [ -d "$CANDIDATE/01_core" ]; then
        export AGENT_SYNC="$CANDIDATE"
    else
        export AGENT_SYNC="$HOME/workbuddy-agent-os/agent-sync"
    fi
    warn "AGENT_SYNC 未设置，自动检测: $AGENT_SYNC"
else
    ok "AGENT_SYNC=$AGENT_SYNC"
fi

# 检测并设置 AGENT_LOCAL
if [ -z "$AGENT_LOCAL" ]; then
    CANDIDATE="${AGENT_SYNC}/agent-local"
    if [ -d "$CANDIDATE/identity" ]; then
        export AGENT_LOCAL="$CANDIDATE"
    else
        export AGENT_LOCAL="$HOME/workbuddy-agent-os/agent-local"
    fi
    warn "AGENT_LOCAL 未设置，自动检测: $AGENT_LOCAL"
else
    ok "AGENT_LOCAL=$AGENT_LOCAL"
fi

# 写入 shell 配置文件
for RC_FILE in "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.bashrc"; do
    if [ -f "$RC_FILE" ]; then
        if ! grep -q "export AGENT_SYNC" "$RC_FILE" 2>/dev/null; then
            echo "" >> "$RC_FILE"
            echo "# AgentOS 路径变量（由 setup_env.sh 自动添加）" >> "$RC_FILE"
            echo "export AGENT_SYNC=\"$AGENT_SYNC\"" >> "$RC_FILE"
            echo "export AGENT_LOCAL=\"$AGENT_LOCAL\"" >> "$RC_FILE"
            ok "已写入 $RC_FILE"
        else
            ok "$RC_FILE 已有 AGENT_SYNC 设置"
        fi
        break
    fi
done

echo ""
info "环境变量配置完成。请执行: source ~/.zshrc"
echo ""
echo "   AGENT_SYNC  = $AGENT_SYNC"
echo "   AGENT_LOCAL = $AGENT_LOCAL"