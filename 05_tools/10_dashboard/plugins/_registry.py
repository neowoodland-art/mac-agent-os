# plugins/_registry.py
# 联邦机器注册表 — 读 cross_machine 获取所有机器信息
# WPRA v2.0: 优先 machines/*/ 读聚合, 降级到旧 _registry.json
# 版本: 2.0.0 | 更新: 2026-05-31

import json, re
from pathlib import Path

CROSS_MACHINE = Path(__file__).resolve().parents[3] / "04_memory" / "cross_machine"
REGISTRY_PATH = CROSS_MACHINE / "status" / "live" / "_registry.json"
DATA_DIR = CROSS_MACHINE / "data"
MACHINES_DIR = CROSS_MACHINE / "machines"


# ── WPRA v2.0: 辅助函数 ─────────────────────────────

def _read_wpra_names() -> list[str]:
    """从 machines/*/heartbeat.json 读取所有机器名"""
    if not MACHINES_DIR.exists():
        return []
    names = []
    for md in sorted(MACHINES_DIR.iterdir()):
        if not md.is_dir():
            continue
        hb = md / "heartbeat.json"
        if hb.exists():
            try:
                data = json.loads(hb.read_text())
                names.append(data.get("machine_name", md.name[:8]))
                continue
            except:
                pass
        # 降级: MACHINE.yaml
        mid = md / "MACHINE.yaml"
        if mid.exists():
            try:
                text = mid.read_text()
                m = re.search(r'machine_name:\s*"?([^"\n]+)"?', text)
                names.append(m.group(1) if m else md.name[:8])
            except:
                names.append(md.name[:8])
    return names


def _read_wpra_info() -> list[dict]:
    """从 machines/*/heartbeat.json 读取所有机器详情"""
    if not MACHINES_DIR.exists():
        return []
    machines = []
    for md in sorted(MACHINES_DIR.iterdir()):
        if not md.is_dir():
            continue
        uid = md.name
        hb = md / "heartbeat.json"
        if hb.exists():
            try:
                d = json.loads(hb.read_text())
                machines.append({
                    "hostname": d.get("machine_name", uid[:8]),
                    "uid": d.get("machine_uid", uid),
                    "last_seen": d.get("updated_at", ""),
                    "status": d.get("status", "unknown"),
                    "guardd_version": d.get("guardd_version", ""),
                    "source": "machines/heartbeat",
                })
                continue
            except:
                pass
        # 降级: 只有目录没有心跳 → 离线
        machines.append({
            "hostname": uid[:8],
            "uid": uid,
            "last_seen": "",
            "status": "offline",
            "guardd_version": "",
            "source": "machines_dir_only",
        })
    return machines


# ── 公开接口 (WPRA 优先, 降级到旧路径) ───────────────

def get_machine_list() -> list[str]:
    """WPRA v2.0: 优先从 machines/*/ 读取，降级到 _registry.json"""
    names = _read_wpra_names()
    if names:
        return sorted(set(names))

    # Fallback: 旧 _registry.json
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
    """WPRA v2.0: 优先从 machines/*/ 读取，降级到 _registry.json"""
    machines = _read_wpra_info()
    if machines:
        for m in machines:
            if m["hostname"] == hostname or not hostname:
                return m

    # Fallback: 旧 _registry.json
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
    """读取所有机器写入的某插件共享数据（已是每人一文件 ✅）"""
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
