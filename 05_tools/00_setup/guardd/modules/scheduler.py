"""
scheduler.py — 调度引擎 (guardd 模块, v2 并行版)

职责:
  - 主循环 run_cycle()，每15秒执行一轮
  - 管理 3 个并行 slot（替代原有的单 active_task 串行模式）
  - 检查当前所有 slot 的任务状态
  - 从优先级队列取出下一个可执行任务
  - 支持 P0/P1/P2 优先级 + B 类任务间隔执行
  - 任务拆解（复合任务 → 最小单元）
  - slot 空闲时自动顶替

v2 变更 (2026-06-28):
  去串行化: active_task → active_tasks[slot_id]
  支持最多 max_slots 个并行任务
  新增: _schedule_all_slots() 循环检查所有 slot
  新增: _check_interval() B类任务间隔检测
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
    """调度引擎 — 支持 3 slot 并行的 v2 版"""

    def __init__(self, task_store: TaskStore, priority_queue: PriorityQueue,
                 slot_manager: BrowserSlotManager, executor: Executor):
        self.task_store = task_store
        self.queue = priority_queue
        self.slot_manager = slot_manager
        self.executor = executor
        self.active_tasks: dict[int, dict] = {}  # slot_id → task dict
        self.paused_tasks: dict[int, dict] = {}
        self.loop_interval = 15  # 15秒
        self.max_slots = slot_manager.max_slots if slot_manager else 3

    def run_cycle(self):
        """主循环（每15秒执行一轮）"""
        while True:
            try:
                self._check_all_active_tasks()
                self._schedule_all_slots()
                self.slot_manager.check_health()
            except Exception as e:
                logger.error(f"调度循环异常: {e}")
            time.sleep(self.loop_interval)

    def submit_task(self, task: dict):
        """提交一个新任务到调度器"""
        task_id = task["task_id"]
        priority = task.get("priority", 1)
        status = task.get("status", STATUS_PENDING)

        # 检查依赖
        deps = task.get("depends_on", [])
        if deps:
            all_done = True
            for dep_id in deps:
                dep = self.task_store.get(dep_id)
                if not dep or dep.get("status") != STATUS_COMPLETED:
                    all_done = False
                    break
            if not all_done:
                task["status"] = STATUS_WAITING_DEP
                self.task_store.save(task)
                logger.info(f"  ⏳ [{task_id}] 等待依赖完成: {deps}")
                return

        task["status"] = STATUS_QUEUED
        task["queued_at"] = time.time()
        # 保留间隔参数
        interval = task.get("interval", 0)
        if interval:
            task["interval"] = interval
            logger.info(f"  📥 [{task_id}] 入队 (priority={priority}, interval={interval}s)")
        else:
            logger.info(f"  📥 [{task_id}] 入队 (priority={priority})")
        self.task_store.save(task)
        self.queue.push(task)

        # 如果有空闲 slot，立即尝试调度
        usage = self.slot_manager.get_usage() if self.slot_manager else {"used": 0, "max": 3}
        if usage.get("used", 0) < usage.get("max", 3):
            self._schedule_all_slots()

    def _check_all_active_tasks(self):
        """检查所有活跃任务是否完成或超时"""
        if not self.active_tasks:
            return

        completed_slots = []
        for slot_id, task in list(self.active_tasks.items()):
            task_id = task["task_id"]
            status = task.get("status", "")

            # 超时检测
            if status == STATUS_RUNNING:
                elapsed = time.time() - task.get("started_at", time.time())
                max_time = task.get("max_execution_sec", 7200)
                if elapsed > max_time:
                    logger.warning(f"  ⏰ [{task_id}] 超时 ({elapsed:.0f}s > {max_time}s), 自动终止")
                    self.executor.kill(task_id)
                    task["status"] = STATUS_FAILED
                    task["error"] = f"超时 ({elapsed:.0f}s)"
                    task["completed_at"] = time.time()
                    self.task_store.save(task)
                    self._notify_dependents(task)
                    # 释放 slot
                    if self.slot_manager:
                        # 从 slot 信息中获取 browser_id
                        slot_info = self.slot_manager.find_account(task.get("accounts", [""])[0]) if task.get("accounts") else None
                        if slot_info:
                            self.slot_manager.release(slot_info["browser_id"])
                    completed_slots.append(slot_id)
                    continue

            if status not in TERMINAL_STATUSES:
                continue  # 还在运行

            # 任务已完成
            logger.info(f"  ✅ [{task_id}] 完成 (status={status})")
            self._notify_dependents(task)

            # 释放 slot
            if self.slot_manager and task.get("accounts"):
                slot_info = self.slot_manager.find_account(task["accounts"][0])
                if slot_info:
                    self.slot_manager.release(slot_info["browser_id"])
            completed_slots.append(slot_id)

        # 清理已完成的 slot
        for slot_id in completed_slots:
            self.active_tasks.pop(slot_id, None)

            # 如果该 slot 有被暂停的任务，恢复
            if slot_id in self.paused_tasks:
                paused = self.paused_tasks.pop(slot_id)
                paused["status"] = STATUS_QUEUED
                self.queue.push(paused)
                logger.info(f"  🔄 恢复 slot {slot_id} 的暂停任务")

    def _schedule_all_slots(self):
        """遍历所有 slot，为空闲的分配任务"""
        usage = self.slot_manager.get_usage() if self.slot_manager else {"max": self.max_slots, "used": 0, "slots": []}
        max_s = usage.get("max", self.max_slots)

        for slot_id in range(max_s):
            if slot_id in self.active_tasks:
                continue  # 这个 slot 还在跑

            # 检查 slot_manager 中该 slot 是否真的空闲
            if self.slot_manager:
                slots_info = usage.get("slots", [])
                slot_info = next((s for s in slots_info if s.get("slot_id") == slot_id), None)
                if slot_info and slot_info.get("account_id"):
                    continue  # slot 管理器认为该槽位还在忙

            # 从队列取下一个可执行任务
            task = self._pop_next_task(slot_id)
            if not task:
                continue  # 队列为空

            # 检查槽位可用
            if self.slot_manager and task.get("accounts"):
                account_id = task["accounts"][0]
                existing = self.slot_manager.find_account(account_id)
                if existing:
                    task["status"] = STATUS_QUEUED
                    task["message"] = f"等待槽位释放: {account_id}"
                    self.task_store.save(task)
                    self.queue.push(task)
                    logger.info(f"  ⏳ [{task['task_id']}] 账号 {account_id} 忙，重新排队")
                    continue

            # 执行任务
            self.active_tasks[slot_id] = task
            task["status"] = STATUS_RUNNING
            task["started_at"] = time.time()
            task["slot_id"] = slot_id
            self.task_store.save(task)
            logger.info(f"  ▶️ [{task['task_id']}] slot {slot_id} 开始执行")

            try:
                import threading
                threading.Thread(target=self.executor.execute, args=(task,), daemon=True).start()
            except Exception as e:
                logger.error(f"  ❌ [{task['task_id']}] 执行失败: {e}")

    def _pop_next_task(self, slot_id: int) -> Optional[dict]:
        """从队列取出下一个适合的任务

        优先级: P0 > P1 > P2
        B 类任务: 检查间隔时间
        """
        # 按优先级排序（P0=0最高，P1=1，P2=2），同优先级按入队时间
        candidates = self.queue.get_all()
        candidates.sort(key=lambda c: (c.get("priority", 1), c.get("scheduled_at", 0)))
        for candidate in candidates:
            task_id = candidate.get("task_id")
            task = self.task_store.get(task_id)
            if not task:
                continue

            # 检查间隔（B 类任务）
            if not self._check_interval(task):
                continue

            # 从队列中移除
            self.queue.remove(task_id)
            return task

        return None

    def _check_interval(self, task: dict) -> bool:
        """B 类任务间隔检测

        如果任务带有 interval 参数，检查同组上一个任务的完成时间。
        间隔未到则跳过（保留在队列中）。
        """
        interval = task.get("interval", 0)
        if not interval or interval == "0":
            return True  # 无间隔，直接放行

        # 解析间隔值
        try:
            if isinstance(interval, str) and "-" in interval:
                # 范围间隔 "30-90" → 取当前设定值（实际值在任务创建时已确定）
                parts = interval.split("-")
                interval = int(parts[1])  # 用最大值作为检查基准
            else:
                interval = int(interval)
        except (ValueError, TypeError):
            return True

        if interval <= 0:
            return True

        # 从 task_store 查该组的最后完成时间
        group_id = task.get("decomposed_from", task.get("task_id", ""))
        last_time = self.task_store.get_group_last_completed(group_id)
        if last_time is None:
            return True  # 还没有完成过，放行

        elapsed = time.time() - last_time
        if elapsed < interval:
            logger.debug(f"  ⏳ [{task['task_id']}] 间隔未到 ({elapsed:.0f}s < {interval}s), 跳过")
            return False

        return True

    def _notify_dependents(self, completed_task: dict):
        """通知依赖此任务的下游任务（支持跨机）"""
        task_id = completed_task["task_id"]
        dep_ids = self.task_store.find_dependents(task_id)
        hostname = __import__("os").uname().nodename

        for dep_id in dep_ids:
            dep = self.task_store.get(dep_id)
            if not dep or dep.get("status") != STATUS_WAITING_DEP:
                continue

            all_done = True
            for d in dep.get("depends_on", []):
                t = self.task_store.get(d)
                if not t or t.get("status") != STATUS_COMPLETED:
                    all_done = False
                    break

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
                self.queue.push(dep)
                logger.info(f"  📤 [{dep_id}] 依赖满足, 入队执行")

    def kill_active(self):
        """终止所有活跃任务"""
        for slot_id, task in list(self.active_tasks.items()):
            try:
                self.executor.kill(task["task_id"])
            except Exception:
                pass
        self.active_tasks.clear()
