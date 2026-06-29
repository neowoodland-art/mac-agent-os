"""
task_store.py — 任务持久化存储 (guardd 模块)

职责:
  - 内存 dict + SQLite 双写
  - 内存保性能，SQLite 持久化
  - 启动时从未完成的任务恢复
"""
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Task status constants
STATUS_PENDING = "pending"
STATUS_SCHEDULED = "scheduled"
STATUS_QUEUED = "queued"
STATUS_PREFLIGHT = "preflight"
STATUS_RUNNING = "running"
STATUS_PAUSED = "paused"
STATUS_WAITING_DEP = "waiting_dep"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"
STATUS_SKIPPED = "skipped"

TERMINAL_STATUSES = {STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED, STATUS_SKIPPED}
ACTIVE_STATUSES = {STATUS_RUNNING, STATUS_QUEUED, STATUS_PREFLIGHT, STATUS_PAUSED, STATUS_WAITING_DEP}


class TaskStore:
    """任务持久化存储 — 内存 dict + SQLite 双写"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            home = Path.home()
            db_path = str(home / "workbuddy-agent-os" / "agent-local" / "runtime" / "guardd" / "tasks.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._lock = threading.Lock()
        self._mem: dict = {}  # task_id → task dict
        self._init_db()
        self._load_from_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS account_health (
                    account_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
            """)
            conn.commit()

    def _load_from_db(self):
        """启动时从 SQLite 加载所有任务到内存"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT task_id, data, status FROM tasks").fetchall()
        for task_id, data_json, status in rows:
            task = json.loads(data_json)
            task["status"] = status
            self._mem[task_id] = task

    def save(self, task: dict) -> None:
        """保存/更新任务（内存 + SQLite）"""
        task_id = task["task_id"]
        status = task.get("status", STATUS_PENDING)
        now = time.time()
        
        with self._lock:
            self._mem[task_id] = task
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO tasks (task_id, data, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (task_id, json.dumps(task, ensure_ascii=False), status, task.get("created_at", now), now),
                )
                conn.commit()

    def get(self, task_id: str) -> Optional[dict]:
        with self._lock:
            return self._mem.get(task_id)

    def get_by_status(self, *statuses) -> List[dict]:
        with self._lock:
            return [t for t in self._mem.values() if t.get("status") in statuses]

    def get_active(self) -> List[dict]:
        return self.get_by_status(*ACTIVE_STATUSES)

    def find_dependents(self, task_id: str) -> List[str]:
        """查找依赖指定 task_id 的所有任务"""
        result = []
        with self._lock:
            for tid, task in self._mem.items():
                deps = task.get("depends_on", [])
                if task_id in deps:
                    result.append(tid)
        return result

    def save_account_health(self, account_id: str, data: dict) -> None:
        data["updated_at"] = time.time()
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO account_health (account_id, data, updated_at) VALUES (?, ?, ?)",
                    (account_id, json.dumps(data, ensure_ascii=False), time.time()),
                )
                conn.commit()

    def get_account_health(self, account_id: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT data FROM account_health WHERE account_id = ?", (account_id,)).fetchone()
            if row:
                return json.loads(row[0])
        return None

    def get_unfinished(self) -> List[dict]:
        """获取所有未完成的任务（启动恢复用）"""
        return self.get_by_status(*ACTIVE_STATUSES)

    def reset_unfinished(self) -> int:
        """启动时将 running 状态重置为 queued"""
        count = 0
        for task in self.get_unfinished():
            if task.get("status") == STATUS_RUNNING:
                task["status"] = STATUS_QUEUED
                task["message"] = "guardd 重启恢复"
                self.save(task)
                count += 1
        return count

    def get_group_last_completed(self, group_id: str) -> Optional[float]:
        """获取某组任务最后一次完成的时间戳
        
        Args:
            group_id: 任务组ID (decomposed_from 或 task_id)
        Returns:
            最后完成时间的 Unix 时间戳，没有完成过的返回 None
        """
        with self._lock:
            last_time = None
            for tid, task in self._mem.items():
                if task.get("decomposed_from") == group_id or tid == group_id:
                    last_completed = task.get("completed_at")
                    if last_completed and (last_time is None or last_completed > last_time):
                        last_time = last_completed
            return last_time

    def all_tasks(self) -> List[dict]:
        with self._lock:
            return list(self._mem.values())

    def count(self) -> dict:
        with self._lock:
            counts = {}
            for t in self._mem.values():
                s = t.get("status", "unknown")
                counts[s] = counts.get(s, 0) + 1
            return counts