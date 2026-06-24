"""
identity.py — AgentOS 联邦身份工具

统一 hostname 解析入口。
所有需要获取本机 hostname 的模块，从此处导入 resolve_hostname()。
"""

import os
from pathlib import Path


def _agent_local_path() -> Path:
    """获取本机数据目录路径"""
    env = os.environ.get("AGENT_LOCAL", "")
    if env:
        return Path(env)
    return Path.home() / "workbuddy-agent-os" / "agent-local"


def resolve_hostname() -> str:
    """优先从 cached_hostname 读取，兜底 os.uname().nodename

    一级降级：cached_hostname（agent-local/identity/cached_hostname）
    二级降级：os.uname().nodename（系统主机名）
    """
    cached = _agent_local_path() / "identity" / "cached_hostname"
    if cached.exists():
        raw = cached.read_text().strip()
        if raw:
            return raw
    return os.uname().nodename
