"""
⚠️ 已废弃 — 请使用 services/browser_orchestrator.py 替代。
   本文件保留供 app.py 过渡使用，新代码禁止导入。

资源锁模块 — 浏览器/账号/身份互斥

管理三把锁:
  - browser:   每台机器只能开一个浏览器
  - account:   同一账号不能同时被两个操作使用
  - identity:  同一身份不能同时被两个浏览器使用

锁文件路径: cross_machine/tasks/locks/{resource_type}/{resource_id}.json
"""

import json, time
from pathlib import Path
from datetime import datetime, timezone

from plugins.base import CROSS_MACHINE

LOCKS_DIR = CROSS_MACHINE / "tasks" / "locks"
DEFAULT_TTL = 3600  # 1小时自动过期


def _now():
    return datetime.now(timezone.utc).isoformat()


def _lock_path(resource_type: str, resource_id: str) -> Path:
    d = LOCKS_DIR / resource_type
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{resource_id}.json"


def acquire_lock(resource_type: str, resource_id: str,
                 holder: str, ttl: int = DEFAULT_TTL) -> dict:
    """获取资源锁
    
    Returns:
        {"success": True} 或 {"success": False, "held_by": "...", "message": "..."}
    """
    fp = _lock_path(resource_type, resource_id)
    
    # 检查是否已被占用
    if fp.exists():
        try:
            existing = json.loads(fp.read_text())
            # 检查 TTL
            acquired = existing.get("acquired_at", "")
            if acquired:
                acquired_ts = datetime.fromisoformat(acquired).timestamp()
                if time.time() - acquired_ts < ttl:
                    return {
                        "success": False,
                        "held_by": existing.get("held_by", "未知"),
                        "message": f"{resource_type}:{resource_id} 已被 {existing.get('held_by', '未知')} 占用"
                    }
                else:
                    # TTL 过期, 覆盖
                    pass
        except:
            pass
    
    lock = {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "held_by": holder,
        "acquired_at": _now(),
        "ttl": ttl,
    }
    fp.write_text(json.dumps(lock, indent=2))
    return {"success": True}


def release_lock(resource_type: str, resource_id: str, holder: str = "") -> bool:
    """释放资源锁"""
    fp = _lock_path(resource_type, resource_id)
    if not fp.exists():
        return True
    if holder:
        try:
            data = json.loads(fp.read_text())
            if data.get("held_by") != holder:
                return False  # 不是自己的锁, 不能释放
        except:
            pass
    fp.unlink(missing_ok=True)
    return True


def check_lock(resource_type: str, resource_id: str) -> dict:
    """检查资源锁状态"""
    fp = _lock_path(resource_type, resource_id)
    if not fp.exists():
        return {"locked": False}
    try:
        data = json.loads(fp.read_text())
        return {"locked": True, "held_by": data.get("held_by", "?"), "since": data.get("acquired_at", "")}
    except:
        return {"locked": False}


def acquire_browser_lock(machine: str, holder: str) -> dict:
    """获取浏览器锁 (每机器全局一把)"""
    return acquire_lock("browser", machine, holder)


def release_browser_lock(machine: str, holder: str = "") -> bool:
    """释放浏览器锁"""
    return release_lock("browser", machine, holder)


def acquire_account_lock(account_id: str, holder: str) -> dict:
    """获取账号锁"""
    return acquire_lock("account", account_id, holder)


def release_account_lock(account_id: str, holder: str = "") -> bool:
    """释放账号锁"""
    return release_lock("account", account_id, holder)


def acquire_identity_lock(identity_dir: str, holder: str) -> dict:
    """获取身份锁"""
    return acquire_lock("identity", identity_dir, holder)


def release_identity_lock(identity_dir: str, holder: str = "") -> bool:
    """释放身份锁"""
    return release_lock("identity", identity_dir, holder)


def release_all_locks(holder: str):
    """释放指定持有者的所有锁"""
    for resource_type in ["browser", "account", "identity"]:
        d = LOCKS_DIR / resource_type
        if not d.exists():
            continue
        for fp in d.glob("*.json"):
            try:
                data = json.loads(fp.read_text())
                if data.get("held_by") == holder:
                    fp.unlink(missing_ok=True)
            except:
                fp.unlink(missing_ok=True)
