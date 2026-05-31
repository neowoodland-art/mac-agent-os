"""
工具函数：路径解析、shell 执行、颜色输出
"""

import os
import sys
import subprocess
from pathlib import Path

from .const import __agent_sync_root__, __agent_local_root__


def get_sync_root() -> Path:
    """获取 agent-sync 根目录"""
    env_root = os.environ.get("AGENT_SYNC_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__agent_sync_root__).expanduser()


def get_local_root() -> Path:
    """获取 agent-local 根目录"""
    env_root = os.environ.get("AGENT_LOCAL_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__agent_local_root__).expanduser()


def get_python() -> str:
    """获取 WorkBuddy 管理的 Python 路径"""
    candidates = [
        os.environ.get("AGENTOS_PYTHON"),
        str(Path.home() / ".workbuddy/binaries/python/envs/agent-os/bin/python3"),
        str(Path.home() / ".workbuddy/binaries/python/versions/3.13.12/bin/python3"),
        "python3",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return "python3"


def get_node() -> str:
    """获取 WorkBuddy 管理的 node 路径"""
    candidates = [
        str(Path.home() / ".workbuddy/binaries/node/versions/22.12.0/bin/node"),
        "node",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return "node"


def get_npx() -> str:
    """获取 WorkBuddy 管理的 npx 路径"""
    node_dir = Path.home() / ".workbuddy/binaries/node/versions/22.12.0/bin"
    npx_path = node_dir / "npx"
    if npx_path.exists():
        return str(npx_path)
    return "npx"


def run(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    """运行命令并返回结果"""
    default = {"capture_output": True, "text": True, "timeout": 120}
    default.update(kwargs)
    return subprocess.run(cmd, **default)


def color(text: str, color_name: str = "blue") -> str:
    """终端颜色输出"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "reset": "\033[0m",
    }
    return f"{colors.get(color_name, '')}{text}{colors['reset']}"


def info(msg: str):
    print(f"{color('[INFO]', 'blue')} {msg}")


def ok(msg: str):
    print(f"{color('[OK]', 'green')} {msg}")


def warn(msg: str):
    print(f"{color('[WARN]', 'yellow')} {msg}")


def err(msg: str):
    print(f"{color('[ERROR]', 'red')} {msg}")


def banner():
    """显示欢迎横幅"""
    print()
    print("=" * 60)
    print(f"  AgentOS 系统管理 CLI v1.0.0")
    print(f"  Synced:     {get_sync_root()}")
    print(f"  Local:      {get_local_root()}")
    print("=" * 60)
    print()
