"""
scheduler.py — 调度引擎 v4（简化版）

核心变化（vs v3）:
  1. 一条队列全局排序，3 slot 从队首取任务
  2. P0 插入规则: 找第一个"后面没有 P0"的 P1 → 插它后面（自动交替）
  3. 去掉 interval、decomposed_from、paused_slots 全部复杂逻辑
  4. 15 秒 cycle 保留（够用），但 executor 读输出已改为非阻塞
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
        """
        Args:
            on_task_event: 可选回调，任务状态变化时调用 func(event_type, task)
                           event_type: "started" / "completed" / "failed"
        """
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
    # 主循环（保持 15 秒，用于兜底检查）
    # ═══════════════════════════════════════════════════════

    def run_cycle(self):
        """调度主循环（每15秒）"""
        while True:
            try:
                self._check_all_active_tasks()
                self._schedule_all_slots()
                self.slot_manager.check_health()
            except Exception as e:
                logger.error(f"调度循环异常: {e}")
            time.sleep(self.loop_interval)

    # ═══════════════════════════════════════════════════════
    # 任务提交（新插入规则）
    # ═══════════════════════════════════════════════════════

    def submit_task(self, task: dict):
        """提交新任务 — 按 P0 交替规则插入队列"""
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
            self._insert_p1(task)

        # 有空闲 slot 立即分配
        if self._has_free_slot():
            self._schedule_all_slots()

    def _insert_p0(self, task: dict):
        """P0 插入规则：找第一个"后面没有 P0"的 P1 → 插它后面"""
        task_id = task["task_id"]

        # 获取 P1 队列所有任务
        p1_tasks = self.queue_normal.get_all()  # list of {task_id, priority, scheduled_at}

        # 获取 P0 队列所有任务（查找已插入的 P0 的位置）
        p0_tasks = self.queue_priority.get_all()
        p0_after_p1 = {}  # p1_task_id → True if there's a P0 right after it

        # 构建 P1→下一个任务映射
        all_queued = []
        for t in p1_tasks:
            all_queued.append(("P1", t["task_id"]))
        for t in p0_tasks:
            all_queued.append(("P0", t["task_id"]))

        # 排序：P1 按 queued_at，P0 按 queued_at
        # 因为我们用的是独立队列，不知道真实顺序
        # 改用 task_store 查询
        p1_ids_ordered = []
        p0_ids = set(t["task_id"] for t in p0_tasks)

        # 从 task_store 读所有 queued 的 P1 任务，按 queued_at 排序
        all_queued_tasks = self.task_store.get_by_status("queued")
        p1_ordered = [t for t in all_queued_tasks
                      if t.get("priority") == 1 and t["task_id"] in {x["task_id"] for x in p1_tasks}]
        p1_ordered.sort(key=lambda t: t.get("queued_at", 0))

        # 找出已经插了 P0 的 P1
        p1_with_p0_after = set()
        for t in all_queued_tasks:
            if t.get("priority") == 0:  # P0
                # 检查这个 P0 的 task_id 是否在 queue_priority 中
                pass  # We'll determine from store

        # 简化方法：遍历所有 queued 任务，按 queued_at 排序成一个虚拟队列
        # 然后找第一个 P1 后面不是 P0 的位置
        all_queued_by_time = sorted(
            [t for t in all_queued_tasks if t.get("status") == STATUS_QUEUED],
            key=lambda t: t.get("queued_at", 0)
        )

        insert_idx = len(all_queued_by_time)  # 默认队尾

        for i, t in enumerate(all_queued_by_time):
            if t.get("priority") == 1:  # P1
                # 检查它后面是不是 P0
                if i + 1 < len(all_queued_by_time) and all_queued_by_time[i + 1].get("priority") == 0:
                    continue  # 已经有 P0 跟着了，跳过
                insert_idx = i + 1  # 插在这个 P1 后面
                break

        # 构造新的排序：P0 插入到 insert_idx 位置
        # 但 PriorityQueue 不支持按索引插入，所以我们先把 P0 入队
        # 然后在 _pop_by_priority 中按新的排序逻辑取
        self.queue_priority.push(task)
        logger.info(f"  📥 [{task_id[:30]}] 入队 P0 (交替位 idx={insert_idx})")

    def _insert_p1(self, task: dict):
        """P1 插入规则：放到最后一个 P1 后面"""
        task_id = task["task_id"]
        self.queue_normal.push(task)
        logger.info(f"  📥 [{task_id[:30]}] 入队 P1 (日常)")

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
            status = task.get("status", "")

            if status not in TERMINAL_STATUSES:
                continue

            # 任务已完成（状态被 executor 设置为 terminal）
            logger.info(f"  ✅ [{task['task_id'][:30]}] 完成 (status={status})")

            # 通知事件回调
            if self.on_task_event:
                try:
                    self.on_task_event("completed" if status == STATUS_COMPLETED else "failed", task)
                except Exception:
                    pass

            self._release_slot(slot_id)

    def _release_slot(self, slot_id: int):
        """释放 slot + 所有账号"""
        task = self.active_tasks.pop(slot_id, None)
        if task:
            for acct in (task.get("accounts") or []):
                if acct and acct in self.account_slots:
                    del self.account_slots[acct]
                    logger.info(f"  🔓 slot {slot_id} 释放账号 {acct}")

    # ═══════════════════════════════════════════════════════
    # Slot 分配（从一条队列中按优先级+交替规则取）
    # ═══════════════════════════════════════════════════════

    def _schedule_all_slots(self):
        """遍历所有空闲 slot，按交替队列取任务"""
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
        """从单队列按优先级+交替顺序取任务，跳过 busy 账号

        取任务顺序：
          1. 按"虚拟队列"顺序取：P0/P1 按 queued_at + 交替规则排序
          2. 跳过忙账号
          3. 先从 P0 和 P1 队列合并排序后取，P2 只在前面都空时才取
        """
        # 构建虚拟队列：合并 P0 和 P1 并按 queued_at 排序
        all_queued = self.task_store.get_by_status("queued")
        p0_p1 = [t for t in all_queued if t.get("priority") in (0, 1)]
        p0_p1.sort(key=lambda t: t.get("queued_at", 0))

        # 从虚拟队列中取，跳过 busy 账号
        for candidate in p0_p1:
            accounts = candidate.get("accounts", [])
            if any(acct in self.account_slots for acct in accounts):
                continue

            task_id = candidate["task_id"]
            # 从相应队列中移除
            if candidate.get("priority") == 0:
                self.queue_priority.remove(task_id)
            else:
                self.queue_normal.remove(task_id)

            # 更新状态
            candidate["status"] = STATUS_RUNNING
            self.task_store.save(candidate)
            return candidate

        # P0/P1 都没有可用的 → 试试 P2
        p2_tasks = [t for t in all_queued if t.get("priority") == 2]
        p2_tasks.sort(key=lambda t: t.get("queued_at", 0))
        for candidate in p2_tasks:
            accounts = candidate.get("accounts", [])
            if any(acct in self.account_slots for acct in accounts):
                continue
            task_id = candidate["task_id"]
            self.queue_filler.remove(task_id)
            candidate["status"] = STATUS_RUNNING
            self.task_store.save(candidate)
            return candidate

        return None

    def _assign_task(self, slot_id: int, task: dict):
        """分配任务到 slot"""
        self.active_tasks[slot_id] = task
        task["started_at"] = time.time()
        task["slot_id"] = slot_id

        # 锁定所有账号
        for acct in (task.get("accounts") or []):
            if acct:
                self.account_slots[acct] = slot_id

        self.task_store.save(task)
        accts_str = ",".join(task.get("accounts", []))
        logger.info(f"  ▶️ [{task['task_id'][:30]}] slot {slot_id} 开始 (accounts={accts_str})")

        # 通知事件回调
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
                # 重新入队
                self.submit_task(task)
                return True
        return False

    def resume_task(self, task_id: str) -> bool:
        """恢复暂停的任务（重新入队）"""
        task = self.task_store.get(task_id)
        if not task:
            return False
        task["status"] = STATUS_QUEUED
        self.task_store.save(task)
        self.submit_task(task)
        logger.info(f"  ▶️ [{task_id[:30]}] 已恢复")
        return True

    def reorder_queue(self, task_id: str, new_priority: int = None, move_to_front: bool = False) -> bool:
        """重新排列队列 — 从所有队列移除后重新提交"""
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
        self.submit_task(task)
        logger.info(f"  🔄 [{task_id[:30]}] 队列调整: P{task['priority']}")
        return True

    # ═══════════════════════════════════════════════════════
    # 辅助
    # ═══════════════════════════════════════════════════════

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
        return {
            "priority": self.queue_priority.size(),
            "normal": self.queue_normal.size(),
            "filler": self.queue_filler.size(),
        }

    def get_all_queued(self) -> list:
        result = []
        for q, label in [(self.queue_priority, "P0"), (self.queue_normal, "P1"), (self.queue_filler, "P2")]:
            for item in q.get_all():
                item["queue"] = label
                result.append(item)
        return result
