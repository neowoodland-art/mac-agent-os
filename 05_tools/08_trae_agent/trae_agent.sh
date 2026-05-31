#!/bin/bash
# trae-agent 封装脚本
# AgentOS 工具入口 - 将 trae-agent CLI 封装为标准化工具
# 用法: trae_agent.sh <run|interactive|show-config|tools> [参数...]
# 最后更新：2026-05-02

set -euo pipefail

TRAE_AGENT_DIR="$HOME/workbuddy-agent-os/agent-local/tools/trae-agent"
TRAE_CONFIG="$TRAE_AGENT_DIR/trae_config.yaml"

if [ ! -d "$TRAE_AGENT_DIR" ]; then
    echo "错误: trae-agent 未安装" >&2
    echo "请先运行: install_trae_agent.sh" >&2
    exit 1
fi

_trae() {
    export PATH="$HOME/.local/bin:$PATH"
    # 绕过系统代理（macOS 系统代理端口 6478 会拦截本地 LLM 请求）
    export NO_PROXY="localhost,127.0.0.1,::1"
    export no_proxy="localhost,127.0.0.1,::1"
    cd "$TRAE_AGENT_DIR"
    uv run python3 -m trae_agent.cli "$@"
}

# Docker 默认镜像配置
DEFAULT_DOCKER_IMAGE="python:3.12-slim"

# Colima 沙箱管理
COLIMA_HOME="$HOME/.colima"
COLIMA_LIMA_HOME="$HOME/.lima"

_colima_status() {
    # 检查 Colima / Docker 运行状态
    if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
        return 0
    fi
    return 1
}

_trae_docker() {
    # 在 Docker 中运行 trae-agent 以隔离环境
    if ! _colima_status; then
        echo "⚠️ Docker 沙箱未就绪（Colima 未运行）" >&2
        echo "   启动命令: colima start --cpu 2 --memory 4 --disk 20" >&2
        echo "   查看状态: colima status" >&2
        echo "   回退到本地执行（--no-docker 模式）..." >&2
        echo "" >&2
        _trae "$@"
        return
    fi
    export PATH="$HOME/.local/bin:$PATH"
    export NO_PROXY="localhost,127.0.0.1,::1"
    export no_proxy="localhost,127.0.0.1,::1"
    cd "$TRAE_AGENT_DIR"
    uv run python3 -m trae_agent.cli run --docker-image "$DEFAULT_DOCKER_IMAGE" "$@"
}

case "${1:-help}" in
    run|r)
        shift
        if [ $# -eq 0 ]; then
            echo "用法: trae_agent.sh run [--no-docker] [选项] \"任务描述\"" >&2
            echo "或从文件读取: trae_agent.sh run -f /path/to/task.txt" >&2
            exit 1
        fi
        # 检查是否跳过 Docker
        if [ "${1:-}" = "--no-docker" ]; then
            shift
            _trae run --config-file "$TRAE_CONFIG" "$@"
        else
            _trae_docker --config-file "$TRAE_CONFIG" "$@"
        fi
        ;;
    interactive|i|shell)
        # 交互式模式
        shift
        _trae interactive --config-file "$TRAE_CONFIG" "$@"
        ;;
    show-config|config)
        # 显示当前配置
        shift
        _trae show-config --config-file "$TRAE_CONFIG" "$@"
        ;;
    tools)
        # 列出可用工具
        _trae tools
        ;;
    help|--help|-h)
        echo "Trae Agent - AI 编程助手 CLI"
        echo ""
        echo "用法: trae_agent.sh <命令> [参数...]"
        echo ""
        echo "命令:"
        echo "  run, r           执行任务（非交互模式）"
        echo "  interactive, i   交互式模式"
        echo "  show-config, config  查看配置"
        echo "  tools            列出可用工具"
        echo "  help             本帮助"
        echo ""
        echo "示例:"
        echo "  trae_agent.sh run \"创建一个 Hello World Python 脚本\""
        echo "  trae_agent.sh run --no-docker -p omix -m Qwen3-8B-MLX-4bit \"分析代码\""
        echo "  trae_agent.sh interactive"
        echo ""
        echo "Docker 沙箱（Colima）:"
        echo "  默认在 Docker 容器中执行任务（python:3.12-slim）"
        echo "  跳过 Docker: trae_agent.sh run --no-docker \"任务\""
        echo "  Colima 状态: colima status"
        echo "  Colima 启动: colima start --cpu 2 --memory 4 --disk 20"
        echo ""
        echo "配置文件: $TRAE_CONFIG"
        echo "后端: oMLX (localhost:8000)"
        ;;
    *)
        echo "未知命令: $1" >&2
        echo "用法: trae_agent.sh help" >&2
        exit 1
        ;;
esac
