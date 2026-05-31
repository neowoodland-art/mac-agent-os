#!/bin/bash
# trae-agent 自动安装脚本
# 用于换机后一键安装 trae-agent 环境
# 用法: ./install_trae_agent.sh
# 最后更新：2026-05-02

set -euo pipefail

echo "================================================"
echo "  Trae Agent 自动安装脚本"
echo "================================================"

# 配置
TRAE_AGENT_DIR="$HOME/workbuddy-agent-os/agent-local/tools/trae-agent"
TOOL_DIR="$HOME/workbuddy-agent-os/agent-sync/05_tools/08_trae_agent"
UV_PATH="$HOME/.local/bin/uv"

# 步骤1: 检查系统依赖
echo ""
echo "[1/5] 检查系统依赖..."

# Python 3.12+
PYTHON_VERSION=$(python3 --version 2>/dev/null | grep -oP '\d+\.\d+' | head -1 || echo "0")
if [ "$(echo "$PYTHON_VERSION >= 3.12" | bc 2>/dev/null)" != "1" ]; then
    echo "  警告: 系统 Python 版本 ($PYTHON_VERSION) 低于 3.12"
    echo "  使用 WorkBuddy 托管 Python"
    WORKBUDDY_PYTHON="$HOME/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
    if [ -f "$WORKBUDDY_PYTHON" ]; then
        echo "  ✅ 使用 WorkBuddy Python 3.13.12"
        export PATH="$HOME/.workbuddy/binaries/python/versions/3.13.12/bin:$PATH"
    else
        echo "  ❌ 未找到兼容的 Python 版本，请安装 Python 3.12+"
        exit 1
    fi
else
    echo "  ✅ Python $PYTHON_VERSION"
fi

# uv 包管理器
if [ ! -f "$UV_PATH" ]; then
    echo "  安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "  ✅ uv 安装完成"
else
    echo "  ✅ uv $(uv --version 2>/dev/null || echo '已安装')"
fi
export PATH="$HOME/.local/bin:$PATH"

# Git
if ! command -v git &>/dev/null; then
    echo "  ❌ Git 未安装"
    exit 1
fi
echo "  ✅ Git $(git --version | head -1)"

# 步骤2: 克隆 trae-agent 仓库
echo ""
echo "[2/5] 克隆 trae-agent 仓库..."
if [ -d "$TRAE_AGENT_DIR" ]; then
    echo "  trae-agent 已存在，更新..."
    cd "$TRAE_AGENT_DIR" && git pull
else
    mkdir -p "$(dirname "$TRAE_AGENT_DIR")"
    # 优先 Gitee 镜像（国内），fallback GitHub
    git clone https://gitee.com/ByteDance/trae-agent.git "$TRAE_AGENT_DIR" 2>/dev/null \
        || git clone https://github.com/bytedance/trae-agent.git "$TRAE_AGENT_DIR"
fi
echo "  ✅ 克隆完成"

# 步骤3: 安装 Python 依赖
echo ""
echo "[3/5] 安装 Python 依赖..."
cd "$TRAE_AGENT_DIR"
uv sync --all-extras --index-url https://pypi.tuna.tsinghua.edu.cn/simple
echo "  ✅ 依赖安装完成"

# 步骤4: 创建默认配置
echo ""
echo "[4/5] 创建默认配置..."
if [ ! -f "$TRAE_AGENT_DIR/trae_config.yaml" ]; then
    cp "$TOOL_DIR/trae_config.yaml.example" "$TRAE_AGENT_DIR/trae_config.yaml" 2>/dev/null \
        || cp "$TRAE_AGENT_DIR/trae_config.yaml.example" "$TRAE_AGENT_DIR/trae_config.yaml" 2>/dev/null
    echo "  ✅ 默认配置已创建"
else
    echo "  ✅ 配置已存在，跳过"
fi

# 步骤5: 验证安装
echo ""
echo "[5/5] 验证安装..."
if cd "$TRAE_AGENT_DIR" && uv run python3 -m trae_agent.cli --help &>/dev/null; then
    echo "  ✅ trae-agent CLI 可用"
else
    echo "  ❌ 验证失败"
    exit 1
fi

# Docker 检查（非强制）
echo ""
echo "  Docker 状态:"
if command -v docker &>/dev/null; then
    echo "  ✅ Docker $(docker --version | head -1)"
else
    echo "  ⚠️ Docker 未安装（trae-agent 默认使用 Docker 隔离）"
    echo "     安装: https://www.docker.com/products/docker-desktop/"
    echo "     或轻量方案: https://github.com/abiosoft/colima"
fi

echo ""
echo "================================================"
echo "  ✅ Trae Agent 安装完成！"
echo "================================================"
echo ""
echo "使用方法:"
echo "  trae_agent.sh run \"描述你的任务\""
echo "  trae_agent.sh interactive"
echo ""
echo "配置文件: $TRAE_AGENT_DIR/trae_config.yaml"
echo "请编辑配置文件设置 LLM API Key"
