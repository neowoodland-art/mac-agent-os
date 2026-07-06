"""
priority_queue.py — 优先级队列 (guardd 模块)

基于 heapq 实现，支持:
  - 按优先级排序（0=最高）
  - 按时间调度（scheduled_at）
  - 取消/重排
"""
import heapq
import time
from typing import Optional, List
from threading import Lock


class PriorityQueue:
    """优先级队列 — 支持时间调度"""

    def __init__(self):
        self._heap = []
        self._task_map = {}  # task_id → (priority, scheduled_at, task_id)
        self._lock = Lock()

    def push(self, task: dict) -> None:
        """推入任务，保留 accounts/cmd_type 等关键字段"""
        task_id = task["task_id"]
        priority = task.get("priority", 1)
        scheduled_at = task.get("scheduled_at", 0) or 0
        if isinstance(scheduled_at, str):
            try:
                scheduled_at = float(scheduled_at)
            except (ValueError, TypeError):
                scheduled_at = 0
        item = (priority, scheduled_at, task_id)
        with self._lock:
            heapq.heappush(self._heap, item)
            self._task_map[task_id] = {
                "priority": priority,
                "scheduled_at": scheduled_at,
                "accounts": task.get("accounts", []),
                "cmd_type": task.get("cmd_type", ""),
                "queued_at": task.get("queued_at", 0),
            }

    def pop_ready(self, now: float = None) -> Optional[str]:
        """取出到时间且优先级最高的任务，返回 task_id"""
        if now is None:
            now = time.time()
        with self._lock:
            while self._heap:
                priority, scheduled_at, task_id = self._heap[0]
                if scheduled_at <= now:
                    heapq.heappop(self._heap)
                    self._task_map.pop(task_id, None)
                    return task_id
                else:
                    return None  # 堆顶还没到时间
            return None

    def peek(self) -> Optional[dict]:
        """查看堆顶但不取出"""
        with self._lock:
            if not self._heap:
                return None
            priority, scheduled_at, task_id = self._heap[0]
            return {"task_id": task_id, "priority": priority, "scheduled_at": scheduled_at}

    def remove(self, task_id: str) -> bool:
        """从队列中移除任务"""
        with self._lock:
            if task_id in self._task_map:
                # 标记移除（实际在 pop 时清理）
                self._task_map[task_id] = None
                return True
            return False

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._heap) == 0

    def size(self) -> int:
        with self._lock:
            return len(self._heap)

    def clear(self):
        """清空队列"""
        with self._lock:
            self._heap.clear()
            self._task_map.clear()

    def get_all(self) -> List[dict]:
        """返回所有队列中的任务信息（含 accounts/cmd_type 等字段）"""
        with self._lock:
            result = []
            for p, s, tid in self._heap:
                info = self._task_map.get(tid)
                if info is None:
                    continue
                result.append({
                    "task_id": tid,
                    "priority": info.get("priority", p),
                    "scheduled_at": info.get("scheduled_at", s),
                    "accounts": info.get("accounts", []),
                    "cmd_type": info.get("cmd_type", ""),
                    "queued_at": info.get("queued_at", 0),
                })
            return result
