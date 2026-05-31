"""
agentos - AgentOS 系统管理 CLI
=================================

统一入口，管理 AgentOS 的全部系统级操作。

用法:
    agentos                   显示帮助
    agentos init              换机一键初始化
    agentos sync              双机增量同步
    agentos skill list        列出所有技能
    agentos skill install     安装技能到 WorkBuddy
    agentos skill build       打包技能为 .skill 包
    agentos skill search      搜索技能
    agentos tool list         列出所有工具
    agentos check             全系统健康检查
    agentos upgrade [--module <name>]  统一模块升级（拉取代码 + 安装依赖 + 环境检查）
    agentos config status     查看配置状态
    agentos config diff       查看配置差异
    agentos config apply      部署配置（A类自动 / B类选择）
    agentos config rollback   回滚至备份
    agentos backup            备份 agent-local/（materials + memory/raw）
    agentos restore <路径>    从备份还原 agent-local/
"""

from pathlib import Path

__version__ = "2.0.0"
__agent_sync_root__ = str(Path.home() / "workbuddy-agent-os" / "agent-sync")
__agent_local_root__ = str(Path.home() / "workbuddy-agent-os" / "agent-local")
