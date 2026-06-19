#!/bin/bash
# AgentOS launchd wrapper — 自动解析 $HOME 路径，适配多机
# 用法: launch.sh <script_relative_path> [args...]
# 示例: launch.sh 05_tools/00_setup/guardd/guardd.py

SCRIPT_REL="$1"
shift

PYTHON="$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3"
SCRIPT="$HOME/workbuddy-agent-os/agent-sync/$SCRIPT_REL"

exec "$PYTHON" "$SCRIPT" "$@"
