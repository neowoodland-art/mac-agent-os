"""
操作队列模块 — 管理操作生命周期 (状态机)

⚠️ 已废弃 — 请使用 services/command_bus.py 替代。
   本文件的文件持久化方案（JSON on disk）与新 command_bus 的内存方案共存。
   新代码使用 command_bus，旧文件保留不删。
   
每个操作经过:
  pending → checking → preparing → running → completed → cleaning → done
                                   ↘ failed → cleaning → error

存储: cross_machine/tasks/pending/{op_id}.json
       cross_machine/tasks/history/{op_id}.json (完成后移入)
"""

import json, os, time, uuid
from pathlib import Path
from datetime import datetime, timezone

from plugins.base import AGENT_SYNC, CROSS_MACHINE

TASKS_DIR = CROSS_MACHINE / "tasks"
PENDING_DIR = TASKS_DIR / "pending"
HISTORY_DIR = TASKS_DIR / "history"

# 状态常量
STATE_PENDING = "pending"
STATE_CHECKING = "checking"
STATE_PREPARING = "preparing"
STATE_RUNNING = "running"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"
STATE_CLEANING = "cleaning"
STATE_DONE = "done"
STATE_ERROR = "error"
STATE_CANCELLED = "cancelled"

VALID_STATES = {
    STATE_PENDING: [STATE_CHECKING, STATE_CANCELLED],
    STATE_CHECKING: [STATE_PREPARING, STATE_FAILED, STATE_CANCELLED],
    STATE_PREPARING: [STATE_RUNNING, STATE_FAILED, STATE_CANCELLED],
    STATE_RUNNING: [STATE_COMPLETED, STATE_FAILED, STATE_CANCELLED],
    STATE_COMPLETED: [STATE_CLEANING],
    STATE_FAILED: [STATE_CLEANING],
    STATE_CLEANING: [STATE_DONE, STATE_ERROR],
    STATE_DONE: [],
    STATE_ERROR: [],
    STATE_CANCELLED: [],
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs():
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def submit_operation(op_type: str, target_machine: str, params: dict) -> dict:
    """提交一个新操作"""
    _ensure_dirs()
    op_id = f"op_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    op = {
        "operation_id": op_id,
        "type": op_type,
        "target_machine": target_machine,
        "params": params,
        "status": STATE_PENDING,
        "states": [
            {"state": STATE_PENDING, "time": _now(), "message": "操作已提交"}
        ],
        "created_at": _now(),
        "updated_at": _now(),
        "output": "",
        "error": "",
        "triggered_by": "dashboard",
    }
    filepath = PENDING_DIR / f"{op_id}.json"
    filepath.write_text(json.dumps(op, indent=2, ensure_ascii=False))
    return op


def transition_state(op_id: str, new_state: str, message: str = "") -> bool:
    """转换操作状态"""
    op = get_operation(op_id)
    if not op:
        return False
    
    current = op["status"]
    allowed = VALID_STATES.get(current, [])
    if new_state not in allowed:
        return False
    
    op["status"] = new_state
    op["states"].append({"state": new_state, "time": _now(), "message": message or ""})
    op["updated_at"] = _now()
    
    # 如果到达终态,移入 history
    if new_state in (STATE_DONE, STATE_ERROR, STATE_CANCELLED):
        _ensure_dirs()
        old_path = PENDING_DIR / f"{op_id}.json"
        new_path = HISTORY_DIR / f"{op_id}.json"
        if old_path.exists():
            old_path.write_text(json.dumps(op, indent=2, ensure_ascii=False))
            old_path.rename(new_path)
    else:
        filepath = PENDING_DIR / f"{op_id}.json"
        filepath.write_text(json.dumps(op, indent=2, ensure_ascii=False))
    
    return True


def get_operation(op_id: str) -> dict | None:
    """获取操作详情"""
    for d in [PENDING_DIR, HISTORY_DIR]:
        fp = d / f"{op_id}.json"
        if fp.exists():
            try:
                return json.loads(fp.read_text())
            except:
                return None
    return None


def list_operations(status: str = "", limit: int = 50) -> list[dict]:
    """列出操作"""
    _ensure_dirs()
    result = []
    
    # 当前 pending 的
    for fp in sorted(PENDING_DIR.glob("*.json"), reverse=True)[:limit]:
        try:
            op = json.loads(fp.read_text())
            if not status or op["status"] == status:
                result.append(op)
        except:
            pass
    
    # 历史
    if not status or status in (STATE_DONE, STATE_ERROR, STATE_CANCELLED):
        for fp in sorted(HISTORY_DIR.glob("*.json"), reverse=True)[:limit]:
            try:
                op = json.loads(fp.read_text())
                if not status or op["status"] == status:
                    result.append(op)
            except:
                pass
    
    return result[:limit]


def cancel_operation(op_id: str) -> bool:
    """取消操作"""
    return transition_state(op_id, STATE_CANCELLED, "用户取消")


def update_operation(op_id: str, updates: dict) -> bool:
    """更新操作数据 (输出/错误等)"""
    op = get_operation(op_id)
    if not op:
        return False
    for k, v in updates.items():
        if k in ("output", "error", "params"):
            op[k] = v
    op["updated_at"] = _now()
    filepath = PENDING_DIR / f"{op_id}.json"
    if not filepath.exists():
        filepath = HISTORY_DIR / f"{op_id}.json"
    if filepath.exists():
        filepath.write_text(json.dumps(op, indent=2, ensure_ascii=False))
    return True


def cleanup_stale_locks(max_age_sec: int = 3600):
    """清理过期的资源锁"""
    locks_dir = TASKS_DIR / "locks"
    if not locks_dir.exists():
        return
    now = time.time()
    for fp in locks_dir.glob("*.json"):
        try:
            data = json.loads(fp.read_text())
            acquired = data.get("acquired_at", "")
            if acquired:
                acquired_ts = datetime.fromisoformat(acquired).timestamp()
                if now - acquired_ts > max_age_sec:
                    fp.unlink()
        except:
            fp.unlink()
