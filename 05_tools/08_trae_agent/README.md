# Trae Agent 工具

**路径**: `05_tools/08_trae_agent/`
**最后更新**: 2026-05-02

## 概述

[Trae Agent](https://github.com/bytedance/trae-agent) 是字节跳动开源的命令行 AI 编程助手（MIT 许可证），
类似于 Claude Code / Gemini CLI。它能将自然语言描述的开发任务转化为可执行的软件工程工作流。

## 文件结构

```
08_trae_agent/
├── README.md                     # 本文件
├── trae_agent.sh                 # 主封装脚本（入口）
├── install_trae_agent.sh         # 自动安装脚本
└── trae_config.yaml.example      # 配置文件模板
```

## 系统依赖

- **Python** ≥ 3.12（本机使用 WorkBuddy 托管 Python 3.13.12）
- **uv** 包管理器（`curl -LsSf https://astral.sh/uv/install.sh | sh`）
- **Git**（用于克隆仓库）
- **LLM 后端**：oMLX (localhost:8000) / Ollama / 远程 API

## 安装

```bash
# 方式一：自动安装脚本
bash 05_tools/08_trae_agent/install_trae_agent.sh

# 方式二：agentos CLI
agentos tool install trae-agent
```

## 配置

编辑 `~/workbuddy-agent-os/agent-local/tools/trae-agent/trae_config.yaml`：

```yaml
model_providers:
    omix:                          # oMLX 后端
        api_key: omlx
        base_url: http://localhost:8000/v1
        provider: openai
    openai:                        # 远程 API
        api_key: sk-your-key
        base_url: https://api.openai.com/v1
        provider: openai
```

## 使用方法

```bash
# 运行任务（非交互）
trae_agent.sh run "创建一个 Hello World Python 脚本"

# 指定后端和模型
trae_agent.sh run -p omix -m Qwen3-8B-MLX-4bit "分析项目结构"

# 交互模式
trae_agent.sh interactive

# 查看配置
trae_agent.sh show-config

# 查看可用工具
trae_agent.sh tools
```

## agentos 集成

```bash
agentos tool trae run "任务描述"
agentos tool trae interactive
agentos tool trae config
```

## 已知问题

1. **oMLX Qwen3-8B Chat API**: 已知返回 500 错误，临时可用 VLM 模型或切换至远程 API
2. **网络限制**: GitHub 可能无法直接访问，安装脚本已配置 Gitee 镜像
3. **首次运行**: 需要根据 LLM 后端修改配置文件中的 API key 和 base_url
