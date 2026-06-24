"""
identity.py — AgentOS 联邦身份工具

统一 hostname 解析入口。
所有需要获取本机 hostname 的模块，从此处导入 resolve_hostname()。
"""

import json
import os
from pathlib import Path


def agent_local_path() -> Path:
    """获取本机数据目录路径"""
    env = os.environ.get("AGENT_LOCAL", "")
    if env:
        return Path(env)
    return Path.home() / "workbuddy-agent-os" / "agent-local"


def agent_sync_path() -> Path:
    """获取项目 sync 目录路径"""
    env = os.environ.get("AGENT_SYNC", "")
    if env:
        return Path(env)
    return Path.home() / "workbuddy-agent-os" / "agent-sync"


def resolve_hostname(fallback: str = "") -> str:
    """三级降级解析注册名

    1. cached_hostname（agent-local/identity/cached_hostname）— 防止 IP 变化导致身份漂移
    2. IP→hostname 映射（LAN IP → 注册名）
    3. Registry 查询（通过 machine_uid 匹配）
    4. os.uname().nodename（最终兜底）
    """
    al = agent_local_path()
    # 1. 缓存优先
    cache_file = al / "identity" / "cached_hostname"
    if cache_file.exists():
        cached = cache_file.read_text().strip()
        if cached:
            return cached

    uid = ""
    uid_file = al / "identity" / "machine_uid"
    if uid_file.exists():
        uid = uid_file.read_text().strip()

    raw = os.uname().nodename

    # 2. IP → hostname 映射（仅在无缓存时使用）
    ip_to_name = {
        "192.168.31.225": "chengzigedeAir",
        "192.168.31.226": "chengzigedeAir",
    }
    if raw in ip_to_name:
        return ip_to_name[raw]

    # 3. Registry 查询
    if uid:
        registry_dir = agent_sync_path() / "04_memory" / "cross_machine" / "registry"
        if registry_dir.exists():
            for f in registry_dir.iterdir():
                if f.suffix != ".json":
                    continue
                try:
                    data = json.loads(f.read_text())
                    if data.get("uid") == uid:
                        return data.get("hostname", fallback or raw)
                except Exception:
                    pass

    return fallback or raw
