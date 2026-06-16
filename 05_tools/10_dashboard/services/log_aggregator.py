"""
日志聚合模块 — 操作日志记录/查询/清理

每个操作产生一条结构化日志,存储在 cross_machine/tasks/logs/ 目录。
日志按日期分割: cross_machine/tasks/logs/2026-06-16.jsonl
"""

import json, gzip
from pathlib import Path
from datetime import datetime, timezone, timedelta

from plugins.base import CROSS_MACHINE

LOGS_DIR = CROSS_MACHINE / "tasks" / "logs"
MAX_LOG_AGE_DAYS = 30


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _log_path(date: str = "") -> Path:
    if not date:
        date = _today()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / f"{date}.jsonl"


def write_log(entry: dict):
    """写入一条操作日志"""
    if "timestamp" not in entry:
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    fp = _log_path()
    with open(fp, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def query_logs(machine: str = "", op_type: str = "",
               status: str = "", days: int = 7,
               limit: int = 200) -> list[dict]:
    """查询操作日志,支持按机器/类型/状态/天数过滤"""
    results = []
    today = datetime.now()
    
    for i in range(days):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        fp = _log_path(date)
        if not fp.exists():
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except:
                        continue
                    # 过滤
                    if machine and entry.get("machine", "") != machine:
                        continue
                    if op_type and entry.get("type", "") != op_type:
                        continue
                    if status and entry.get("status", "") != status:
                        continue
                    results.append(entry)
                    if len(results) >= limit:
                        return results
        except:
            continue
    
    return results


def get_log_stats(days: int = 7) -> dict:
    """获取日志统计"""
    logs = query_logs(days=days, limit=10000)
    total = len(logs)
    by_type = {}
    by_machine = {}
    by_status = {}
    
    for entry in logs:
        t = entry.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        
        m = entry.get("machine", "unknown")
        by_machine[m] = by_machine.get(m, 0) + 1
        
        s = entry.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1
    
    return {
        "total": total,
        "by_type": by_type,
        "by_machine": by_machine,
        "by_status": by_status,
        "days": days,
    }


def cleanup_old_logs(max_days: int = MAX_LOG_AGE_DAYS) -> dict:
    """清理超过 max_days 的旧日志"""
    removed = 0
    today = datetime.now()
    
    if not LOGS_DIR.exists():
        return {"removed": 0}
    
    for fp in LOGS_DIR.glob("*.jsonl"):
        try:
            # 从文件名提取日期
            date_str = fp.stem
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if (today - file_date).days > max_days:
                fp.unlink()
                removed += 1
        except:
            continue
    
    return {"removed": removed}
