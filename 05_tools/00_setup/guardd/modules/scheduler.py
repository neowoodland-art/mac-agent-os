"""
scheduler.py — 调度引擎 (guardd 模块, v3 三队列版)

职责:
  - 主循环 run_cycle()，每15秒执行一轮
  - 三队列管理: P0 优先 / P1 日常 / P2 劣后
  - 3 slot 流水线，每 slot 独立执行
  - P0 抢占: 当前任务结束后插队，不中断浏览器
  - P2 劣后: 只在 slot 空闲时执行，可被 P0/P1 抢占
  - 账号互斥表: 同一账号不能同时在多个 slot 运行
"""
import logging
import time
from typing import Optional
from modules.task_store import (
    TaskStore, STATUS_PENDING, STATUS_QUEUED, STATUS_RUNNING,
    STATUS_WAITING_DEP, STATUS_COMPLETED, STATUS_FAILED, TERMINAL_STATUSES
)
from modules.priority_queue import PriorityQueue
from modules.slot_manager import BrowserSlotManager
from modules.executor import Executor

logger = logging.getLogger("guardd.scheduler")


class Scheduler:
    """调度引擎 v3 — 三队列 + 账号互斥 + P0/P1/P2"""

    def __init__(self, task_store: TaskStore, priority_queue: PriorityQueue,
                 slot_manager: BrowserSlotManager, executor: Executor):
        self.task_store = task_store
        # 三队列: P0优先 / P1日常 / P2劣后
        self.queue_priority = PriorityQueue()
        self.queue_normal = PriorityQueue()
        self.queue_filler = PriorityQueue()

        self.slot_manager = slot_manager
        self.executor = executor
        self.active_tasks: dict[int, dict] = {}   # slot_id → task
        self.paused_slots: dict[int, list] = {}    # slot_id → [P0待执行列表]

        # 账号互斥表: {account_id: slot_id}
        self.account_slots: dict[str, int] = {}

        self.loop_interval = 15
        self.max_slots = slot_manager.max_slots if slot_manager else 3

    # ═══════════════════════════════════════════════════════
    # 主循环
    # ═══════════════════════════════════════════════════════

    def run_cycle(self):
        """调度主循环（每15秒）"""
        while True:
            try:
                self._check_all_active_tasks()
                self._restore_paused_tasks()
                self._schedule_all_slots()
                self.slot_manager.check_health()
            except Exception as e:
                logger.error(f"调度循环异常: {e}")
            time.sleep(self.loop_interval)

    # ═══════════════════════════════════════════════════════
    # 任务提交
    # ═══════════════════════════════════════════════════════

    def submit_task(self, task: dict):
        """提交新任务（按优先级入队）"""
        task_id = task["task_id"]
        priority = task.get("priority", 1)
        accounts = task.get("accounts", [])

        task["status"] = STATUS_QUEUED
        task["queued_at"] = time.time()

        interval = task.get("interval", 0)
        if interval:
            task["interval"] = interval

        self.task_store.save(task)

        # 按优先级入队
        q = self._queue_for_priority(priority)
        q.push(task)
        logger.info(f"  📥 [{task_id[:30]}] 入队 (P{priority})")

        if self._has_free_slot():
            self._schedule_all_slots()

    def _queue_for_priority(self, priority: int) -> PriorityQueue:
        if priority == 0:
            return self.queue_priority
        elif priority == 2:
            return self.queue_filler
        return self.queue_normal

    def _has_free_slot(self) -> bool:
        usage = self.slot_manager.get_usage() if self.slot_manager else {"used": 0, "max": 3}
        return usage.get("used", 0) < usage.get("max", 3)

    # ═══════════════════════════════════════════════════════
    # 活跃任务检查
    # ═══════════════════════════════════════════════════════

    def _check_all_active_tasks(self):
        """检查所有活跃任务是否完成或超时"""
        if not self.active_tasks:
            return

        for slot_id, task in list(self.active_tasks.items()):
            task_id = task["task_id"]
            status = task.get("status", "")

            # 超时检测
            if status == STATUS_RUNNING:
                elapsed = time.time() - task.get("started_at", time.time())
                max_time = task.get("max_execution_sec", 7200)
                if elapsed > max_time:
                    logger.warning(f"  ⏰ [{task_id[:30]}] 超时 ({elapsed:.0f}s > {max_time}s)")
                    self.executor.kill(task_id)
                    task["status"] = STATUS_FAILED
                    task["error"] = f"超时 ({elapsed:.0f}s)"
                    task["completed_at"] = time.time()
                    self.task_store.save(task)
                    self._notify_dependents(task)
                    self._release_slot(slot_id)
                    continue

            if status not in TERMINAL_STATUSES:
                continue

            # 任务已完成
            logger.info(f"  ✅ [{task_id[:30]}] 完成 (status={status})")
            self._notify_dependents(task)
            self._release_slot(slot_id)

    def _release_slot(self, slot_id: int):
        """释放 slot + 账号 + 检查是否有 P0 等待"""
        task = self.active_tasks.pop(slot_id, None)
        if task:
            account_id = (task.get("accounts") or [""])[0]
            if account_id and account_id in self.account_slots:
                del self.account_slots[account_id]
                logger.info(f"  🔓 slot {slot_id} 释放账号 {account_id}")

        # 如果有 P0 等待这个 slot，推入优先队列
        if slot_id in self.paused_slots and self.paused_slots[slot_id]:
            next_task = self.paused_slots[slot_id].pop(0)
            next_task["status"] = STATUS_QUEUED
            self.queue_priority.push(next_task)
            logger.info(f"  ⏩ P0 等待任务入队: {next_task['task_id'][:30]}")
            if not self.paused_slots[slot_id]:
                del self.paused_slots[slot_id]

    def _restore_paused_tasks(self):
        """检查并恢复被 P0 打断的 P1 任务"""
        for slot_id, paused_list in list(self.paused_slots.items()):
            if paused_list:
                continue  # 还有 P0 在等，不恢复
            # P0 执行完了，恢复 P1
            if slot_id not in self.active_tasks:
                self.paused_slots.pop(slot_id, None)

    # ═══════════════════════════════════════════════════════
    # Slot 分配
    # ═══════════════════════════════════════════════════════

    def _schedule_all_slots(self):
        """遍历所有 slot，按优先级分配: P0 > P1 > P2"""
        usage = self.slot_manager.get_usage() if self.slot_manager else {"max": self.max_slots, "used": 0, "slots": []}
        max_s = usage.get("max", self.max_slots)

        for slot_id in range(max_s):
            if slot_id in self.active_tasks:
                continue

            # 检查 slot_manager 确认空闲
            if self.slot_manager:
                slots_info = usage.get("slots", [])
                slot_info = next((s for s in slots_info if s.get("slot_id") == slot_id), None)
                if slot_info and slot_info.get("account_id"):
                    continue

            # 按优先级取: P0 > P1 > P2
            task = self._pop_by_priority(slot_id)
            if not task:
                continue

            self._assign_task(slot_id, task)

    def _pop_by_priority(self, slot_id: int) -> Optional[dict]:
        """从三队列取任务: 先 P0, 再 P1, 再 P2。跳过 busy 账号。"""
        for queue, label in [
            (self.queue_priority, "P0"),
            (self.queue_normal, "P1"),
            (self.queue_filler, "P2"),
        ]:
            candidates = queue.get_all()
            candidates.sort(key=lambda c: (c.get("priority", 1), c.get("queued_at", 0)))
            for candidate in candidates:
                task_id = candidate.get("task_id")
                task = self.task_store.get(task_id)
                if not task:
                    continue
                if not self._check_interval(task):
                    continue
                # 跳过 busy 账号
                accounts = task.get("accounts", [])
                if accounts and accounts[0] in self.account_slots:
                    continue
                queue.remove(task_id)
                return task
        return None

    def _assign_task(self, slot_id: int, task: dict):
        """分配任务到 slot"""
        self.active_tasks[slot_id] = task
        task["status"] = STATUS_RUNNING
        task["started_at"] = time.time()
        task["slot_id"] = slot_id
        account_id = (task.get("accounts") or [""])[0]
        if account_id:
            self.account_slots[account_id] = slot_id
        self.task_store.save(task)
        logger.info(f"  ▶️ [{task['task_id'][:30]}] slot {slot_id} 开始 (account={account_id})")

        try:
            import threading
            threading.Thread(target=self.executor.execute, args=(task,), daemon=True).start()
        except Exception as e:
            logger.error(f"  ❌ [{task['task_id'][:30]}] 执行失败: {e}")

    # ═══════════════════════════════════════════════════════
    # P0 抢占
    # ═══════════════════════════════════════════════════════

    def insert_priority(self, task: dict):
        """P0 抢占: 账号忙则等当前任务结束，不中断浏览器"""
        account_id = (task.get("accounts") or [""])[0]
        if account_id and account_id in self.account_slots:
            slot_id = self.account_slots[account_id]
            self.paused_slots.setdefault(slot_id, []).append(task)
            logger.info(f"  ⏫ P0 等待 slot {slot_id}: {task['task_id'][:30]}")
        else:
            # 账号空闲，入优先队列
            self.queue_priority.push(task)
            self._schedule_all_slots()

    # ═══════════════════════════════════════════════════════
    # 间隔检查
    # ═══════════════════════════════════════════════════════

    def _check_interval(self, task: dict) -> bool:
        """B 类任务间隔检测"""
        interval = task.get("interval", 0)
        if not interval or interval == "0":
            return True

        try:
            if isinstance(interval, str) and "-" in interval:
                parts = interval.split("-")
                interval = int(parts[1])
            else:
                interval = int(interval)
        except (ValueError, TypeError):
            return True

        if interval <= 0:
            return True

        group_id = task.get("decomposed_from", task.get("task_id", ""))
        last_time = self.task_store.get_group_last_completed(group_id)
        if last_time is None:
            return True

        elapsed = time.time() - last_time
        if elapsed < interval:
            logger.debug(f"  ⏳ [{task['task_id'][:30]}] 间隔未到 ({elapsed:.0f}s < {interval}s)")
            return False
        return True

    # ═══════════════════════════════════════════════════════
    # 依赖通知
    # ═══════════════════════════════════════════════════════

    def _notify_dependents(self, completed_task: dict):
        """通知依赖此任务的下游任务"""
        task_id = completed_task["task_id"]
        dep_ids = self.task_store.find_dependents(task_id)
        hostname = __import__("os").uname().nodename

        for dep_id in dep_ids:
            dep = self.task_store.get(dep_id)
            if not dep or dep.get("status") != STATUS_WAITING_DEP:
                continue

            all_done = all(
                self._is_dep_completed(d)
                for d in dep.get("depends_on", [])
            )
            if not all_done:
                continue

            interval = dep.get("interval_after_dep", 0)
            dep["scheduled_at"] = time.time() + interval
            dep["status"] = STATUS_QUEUED
            dep["message"] = f"依赖 {task_id} 已完成"
            self.task_store.save(dep)

            dep_machine = dep.get("machine", "")
            if dep_machine and dep_machine != hostname:
                try:
                    import urllib.request
                    import json
                    payload = json.dumps(dep).encode()
                    req = urllib.request.Request(
                        "http://127.0.0.1:9988/api/ops/task/submit",
                        data=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    urllib.request.urlopen(req, timeout=5)
                except Exception as e:
                    logger.warning(f"跨机依赖通知失败 {dep_id}: {e}")
            else:
                self.submit_task(dep)
                logger.info(f"  📤 [{dep_id}] 依赖满足, 入队执行")

    def _is_dep_completed(self, dep_id: str) -> bool:
        t = self.task_store.get(dep_id)
        return t is not None and t.get("status") == STATUS_COMPLETED

    # ═══════════════════════════════════════════════════════
    # 手动操作
    # ═══════════════════════════════════════════════════════

    def pause_task(self, task_id: str) -> bool:
        """暂停一个运行中的任务"""
        for slot_id, task in list(self.active_tasks.items()):
            if task["task_id"] == task_id:
                self.executor.kill(task_id)
                task["status"] = STATUS_QUEUED
                task["paused_at"] = time.time()
                self.task_store.save(task)
                self._release_slot(slot_id)
                logger.info(f"  ⏸️ [{task_id[:30]}] 已暂停 (slot {slot_id})")
                return True
        return False

    def resume_task(self, task_id: str) -> bool:
        """恢复暂停的任务"""
        task = self.task_store.get(task_id)
        if not task:
            return False
        priority = task.get("priority", 1)
        q = self._queue_for_priority(priority)
        task["status"] = STATUS_QUEUED
        q.push(task)
        self.task_store.save(task)
        logger.info(f"  ▶️ [{task_id[:30]}] 已恢复")
        return True

    def reorder_queue(self, task_id: str, new_priority: int = None, move_to_front: bool = False) -> bool:
        """重新排列队列"""
        # 从所有队列移除
        for q in [self.queue_priority, self.queue_normal, self.queue_filler]:
            q.remove(task_id)
        task = self.task_store.get(task_id)
        if not task:
            return False
        if move_to_front:
            task["priority"] = 0
        elif new_priority is not None:
            task["priority"] = new_priority
        task["status"] = STATUS_QUEUED
        self.task_store.save(task)
        q = self._queue_for_priority(task["priority"])
        q.push(task)
        logger.info(f"  🔄 [{task_id[:30]}] 队列调整: P{task['priority']}")
        return True

    def kill_active(self):
        """终止所有活跃任务"""
        for slot_id, task in list(self.active_tasks.items()):
            try:
                self.executor.kill(task["task_id"])
            except Exception:
                pass
        self.active_tasks.clear()
        self.account_slots.clear()

    def queue_sizes(self) -> dict:
        """返回三队列长度（供心跳上报）"""
        return {
            "priority": self.queue_priority.size(),
            "normal": self.queue_normal.size(),
            "filler": self.queue_filler.size(),
        }

    def get_all_queued(self) -> list:
        """返回所有队列中的任务（聚合）"""
        result = []
        for q, label in [
            (self.queue_priority, "P0"),
            (self.queue_normal, "P1"),
            (self.queue_filler, "P2"),
        ]:
            for item in q.get_all():
                item["queue"] = label
                result.append(item)
        return result
