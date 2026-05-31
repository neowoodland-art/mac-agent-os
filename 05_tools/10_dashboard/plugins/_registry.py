# plugins/_registry.py
# 联邦机器注册表 — 读 cross_machine 获取所有机器信息

import json
from pathlib import Path

CROSS_MACHINE = Path(__file__).resolve().parents[3] / "04_memory" / "cross_machine"
REGISTRY_PATH = CROSS_MACHINE / "status" / "live" / "_registry.json"
DATA_DIR = CROSS_MACHINE / "data"


def get_machine_list() -> list[str]:
    """返回所有已注册机器的 hostname 列表"""
    if not REGISTRY_PATH.exists():
        return []
    try:
        reg = json.loads(REGISTRY_PATH.read_text())
        return sorted(set(
            info.get("hostname", "") for info in reg.values()
        ))
    except:
        return []


def get_machine_info(hostname: str = "") -> dict:
    """返回机器注册信息"""
    if not REGISTRY_PATH.exists():
        return {}
    try:
        reg = json.loads(REGISTRY_PATH.read_text())
        for uid, info in reg.items():
            if info.get("hostname") == hostname or not hostname:
                return {"uid": uid, **info}
        return {}
    except:
        return {}


def get_plugin_data(plugin_name: str) -> list[dict]:
    """读取所有机器写入的某插件共享数据"""
    path = DATA_DIR / plugin_name
    if not path.exists():
        return []
    results = []
    for f in sorted(path.iterdir()):
        if f.suffix == ".json":
            try:
                results.append(json.loads(f.read_text()))
            except:
                pass
    return results
