"""
scheduler.py — 调度引擎 v4（简化版）

核心变化（vs v3）:
  1. 一条队列全局排序，3 slot 从队首取任务
  2. P0 插入规则: 找第一个"后面没有 P0"的 P1 → 插它后面（自动交替）
  3. 去掉 interval、decomposed_from、paused_slots 全部复杂逻辑
  4. executor 读输出改为非阻塞（select）
  5. _pop_next 增加 task_store 状态校验，过期自动清除
"""
import logging
import time
from typing import Optional
from modules.task_store import (
    TaskStore, STATUS_QUEUED, STATUS_RUNNING,
    STATUS_COMPLETED, STATUS_FAILED, TERMINAL_STATUSES
)
from modules.priority_queue import PriorityQueue
from modules.slot_manager import BrowserSlotManager
from modules.executor import Executor

logger = logging.getLogger("guardd.scheduler")


class Scheduler:
    """调度引擎 v4 — 单队列 + 交替规则 + 事件驱动编排"""

    def __init__(self, task_store: TaskStore, priority_queue: PriorityQueue,
                 slot_manager: BrowserSlotManager, executor: Executor,
                 on_task_event=None):
        self.task_store = task_store
        self.queue_priority = PriorityQueue()   # P0
        self.queue_normal = PriorityQueue()     # P1
        self.queue_filler = PriorityQueue()     # P2

        self.slot_manager = slot_manager
        self.executor = executor
        self.active_tasks: dict[int, dict] = {}
        self.account_slots: dict[str, int] = {}
        self.on_task_event = on_task_event

        self.loop_interval = 15
        self.max_slots = slot_manager.max_slots if slot_manager else 3

    # ═══════════════════════════════════════════════════════
    # 主循环
    # ═══════════════════════════════════════════════════════

    def run_cycle(self):
        while True:
            try:
                self._check_all_active_tasks()
                self._schedule_all_slots()
                self.slot_manager.check_health()
            except Exception as e:
                logger.error(f"调度循环异常: {e}")
            time.sleep(self.loop_interval)

    # ═══════════════════════════════════════════════════════
    # 任务提交
    # ═══════════════════════════════════════════════════════

    def submit_task(self, task: dict):
        task_id = task["task_id"]
        task["status"] = STATUS_QUEUED
        task["queued_at"] = time.time()
        self.task_store.save(task)

        priority = task.get("priority", 1)
        if priority == 0:
            self._insert_p0(task)
        elif priority == 2:
            self.queue_filler.push(task)
            logger.info(f"  📥 [{task_id[:30]}] 入队 P2 (队尾)")
        else:
            self.queue_normal.push(task)
            logger.info(f"  📥 [{task_id[:30]}] 入队 P1 (日常)")

        if self._has_free_slot():
            self._schedule_all_slots()

    def _insert_p0(self, task: dict):
        """P0 插入: 直接入 priority 队列"""
        task_id = task["task_id"]
        self.queue_priority.push(task)
        logger.info(f"  📥 [{task_id[:30]}] 入队 P0")

    def _has_free_slot(self) -> bool:
        """检查是否有空闲 slot。使用 active_tasks 长度作为主要依据，
        避免 executor 线程尚未调用 acquire() 时的竞态条件。"""
        # active_tasks 是同步设置的（在 _assign_task 中），比 slot_manager 更准确
        active_count = len(self.active_tasks)
        max_s = self.max_slots
        free = active_count < max_s
        return free

    # ═══════════════════════════════════════════════════════
    # 活跃任务检查
    # ═══════════════════════════════════════════════════════

    def _check_all_active_tasks(self):
        if not self.active_tasks:
            return

        for slot_id, task in list(self.active_tasks.items()):
            status = task.get("status", "")

            if status not in TERMINAL_STATUSES:
                continue

            logger.info(f"  ✅ [{task['task_id'][:30]}] 完成 (status={status})")
            if self.on_task_event:
                try:
                    self.on_task_event("completed" if status == STATUS_COMPLETED else "failed", task)
                except Exception:
                    pass
            self._release_slot(slot_id)

    def _release_slot(self, slot_id: int):
        task = self.active_tasks.pop(slot_id, None)
        if task:
            for acct in (task.get("accounts") or []):
                if acct and acct in self.account_slots:
                    del self.account_slots[acct]
                    logger.info(f"  🔓 slot {slot_id} 释放账号 {acct}")
                # 同步释放 slot_manager
                if self.slot_manager:
                    try:
                        self.slot_manager.release_by_account(acct)
                    except Exception:
                        pass

    # ═══════════════════════════════════════════════════════
    # Slot 分配
    # ═══════════════════════════════════════════════════════

    def _schedule_all_slots(self):
        usage = self.slot_manager.get_usage() if self.slot_manager else {"max": self.max_slots, "used": 0, "slots": []}
        max_s = usage.get("max", self.max_slots)

        for slot_id in range(max_s):
            if slot_id in self.active_tasks:
                continue

            if self.slot_manager:
                slots_info = usage.get("slots", [])
                slot_info = next((s for s in slots_info if s.get("slot_id") == slot_id), None)
                if slot_info and slot_info.get("account_id"):
                    continue

            task = self._pop_next(slot_id)
            if not task:
                continue

            self._assign_task(slot_id, task)

    def _pop_next(self, slot_id: int) -> Optional[dict]:
        """取下一个可用任务，按 P0/P1 交替规则，跳过 busy 账号和过期条目。

        交替规则: 优先取 P0，但已分配的 P0 数量>=P1 时取 P1，
        确保 P0 和 P1 交替执行，不会 3 个 slot 全跑 P0。
        """
        # 统计本轮已分配给前几个 slot 的 P0/P1 数量
        p0_assigned = 0
        p1_assigned = 0
        for sid in range(slot_id):
            _t = self.active_tasks.get(sid)
            if _t:
                _p = _t.get("priority")
                if _p == 0:
                    p0_assigned += 1
                elif _p == 1:
                    p1_assigned += 1

        # 交替策略：P0 已多于 P1 时优先取 P1，否则优先取 P0
        prefer_p1 = (p0_assigned > p1_assigned) and self.queue_normal.size() > 0

        if prefer_p1:
            queue_order = [
                (self.queue_normal, "P1"),
                (self.queue_priority, "P0"),
                (self.queue_filler, "P2"),
            ]
        else:
            queue_order = [
                (self.queue_priority, "P0"),
                (self.queue_normal, "P1"),
                (self.queue_filler, "P2"),
            ]

        for queue, _ in queue_order:
            candidates = queue.get_all()
            candidates.sort(key=lambda c: c.get("queued_at", 0))

            for candidate in candidates:
                accounts = candidate.get("accounts", [])
                if any(acct in self.account_slots for acct in accounts):
                    continue

                task_id = candidate["task_id"]

                # 校验 task_store 状态
                stored = self.task_store.get(task_id)
                if not stored:
                    queue.remove(task_id)
                    logger.warning(f"  ⏭ [{task_id[:30]}] 过期清除（无记录）")
                    continue
                if stored.get("status") != STATUS_QUEUED:
                    queue.remove(task_id)
                    logger.info(f"  ⏭ [{task_id[:30]}] 过期清除（status={stored.get('status')}）")
                    continue

                removed = queue.remove(task_id)
                if not removed:
                    continue

                candidate["status"] = STATUS_RUNNING
                self.task_store.save(candidate)
                return candidate

        return None

    def _assign_task(self, slot_id: int, task: dict):
        self.active_tasks[slot_id] = task
        task["started_at"] = time.time()
        task["slot_id"] = slot_id

        for acct in (task.get("accounts") or []):
            if acct:
                self.account_slots[acct] = slot_id

        self.task_store.save(task)
        accts_str = ",".join(task.get("accounts", []))
        logger.info(f"  ▶️ [{task['task_id'][:30]}] slot {slot_id} 开始 (accounts={accts_str})")

        if self.on_task_event:
            try:
                self.on_task_event("started", task)
            except Exception:
                pass

        try:
            import threading
            threading.Thread(target=self.executor.execute, args=(task,), daemon=True).start()
        except Exception as e:
            logger.error(f"  ❌ [{task['task_id'][:30]}] 执行失败: {e}")

    # ═══════════════════════════════════════════════════════
    # 辅助
    # ═══════════════════════════════════════════════════════

    def kill_active(self):
        for slot_id, task in list(self.active_tasks.items()):
            try:
                self.executor.kill(task["task_id"])
            except Exception:
                pass
        self.active_tasks.clear()
        self.account_slots.clear()

    def clear_all(self):
        """清空所有队列 + 杀死活跃任务，完全还原"""
        self.kill_active()
        # 清空内存队列
        for q in [self.queue_priority, self.queue_normal, self.queue_filler]:
            q.clear()
        # 将 task_store 中所有 queued/pending 状态的任务标记为 cancelled
        for status in ("queued", "pending"):
            for t in self.task_store.get_by_status(status):
                t["status"] = "cancelled"
                self.task_store.save(t)
        if self.slot_manager:
            self.slot_manager.cleanup_orphans()

    def queue_sizes(self) -> dict:
        return {
            "priority": self.queue_priority.size(),
            "normal": self.queue_normal.size(),
            "filler": self.queue_filler.size(),
        }

    def get_all_queued(self) -> list:
        """返回排队队列（P0/P1 交替排序，P2 附加末尾）"""
        p0_list = self.queue_priority.get_all()
        p1_list = self.queue_normal.get_all()
        p2_list = self.queue_filler.get_all()

        # 按 queued_at 排序后交替合并
        p0_list.sort(key=lambda x: x.get("queued_at", 0))
        p1_list.sort(key=lambda x: x.get("queued_at", 0))

        result = []
        p0_i, p1_i = 0, 0
        last_p0 = False  # 上一次取了 P0？

        while p0_i < len(p0_list) or p1_i < len(p1_list):
            if p0_i >= len(p0_list):
                # 只剩 P1
                p1_list[p1_i]["queue"] = "P1"
                result.append(p1_list[p1_i])
                p1_i += 1
            elif p1_i >= len(p1_list):
                # 只剩 P0
                p0_list[p0_i]["queue"] = "P0"
                result.append(p0_list[p0_i])
                p0_i += 1
            elif last_p0:
                # 上次取了 P0，这次取 P1（交替）
                p1_list[p1_i]["queue"] = "P1"
                result.append(p1_list[p1_i])
                p1_i += 1
                last_p0 = False
            else:
                # 上次取了 P1 或刚开始，取 P0
                p0_list[p0_i]["queue"] = "P0"
                result.append(p0_list[p0_i])
                p0_i += 1
                last_p0 = True

        # P2 全部附加末尾
        for item in p2_list:
            item["queue"] = "P2"
            result.append(item)

        return result
