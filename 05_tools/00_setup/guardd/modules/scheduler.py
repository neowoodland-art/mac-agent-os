"""
scheduler.py — 调度引擎 (guardd 模块)

职责:
  - 主循环 run_cycle()，每15秒执行一轮
  - 检查当前任务状态
  - 从优先级队列取出下一个可执行任务
  - 任务拆解（把群组任务拆成子任务）
  - 依赖完成后通知下游
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
    """调度引擎 — guardd 主循环"""

    def __init__(self, task_store: TaskStore, priority_queue: PriorityQueue,
                 slot_manager: BrowserSlotManager, executor: Executor):
        self.task_store = task_store
        self.queue = priority_queue
        self.slot_manager = slot_manager
        self.executor = executor
        self.active_task: Optional[dict] = None
        self.paused_task: Optional[dict] = None
        self.loop_interval = 15  # 15秒

    def run_cycle(self):
        """主循环（每15秒执行一轮）"""
        while True:
            try:
                self._check_active_task()
                self._schedule_next()
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
            # 检查所有依赖是否已完成
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
        self.task_store.save(task)
        self.queue.push(task)
        logger.info(f"  📥 [{task_id}] 入队 (priority={priority})")

        # 如果当前没有活跃任务，立即触发调度
        if not self.active_task:
            self._schedule_next()

    def _check_active_task(self):
        """检查当前活跃任务是否完成或超时"""
        if not self.active_task:
            return

        task_id = self.active_task["task_id"]
        status = self.active_task.get("status", "")

        # 超时检测：运行中的任务超过 max_execution_sec 则自动标记失败
        if status == STATUS_RUNNING:
            elapsed = time.time() - self.active_task.get("started_at", time.time())
            max_time = self.active_task.get("max_execution_sec", 7200)
            if elapsed > max_time:
                logger.warning(f"  ⏰ [{task_id}] 超时 ({elapsed:.0f}s > {max_time}s), 自动终止")
                self.executor.kill(task_id)
                self.active_task["status"] = STATUS_FAILED
                self.active_task["error"] = f"超时 ({elapsed:.0f}s)"
                self.active_task["completed_at"] = time.time()
                self.task_store.save(self.active_task)
                self._notify_dependents(self.active_task)
                self.active_task = None
                return

        if status not in TERMINAL_STATUSES:
            return  # 还在运行

        # 任务已完成
        logger.info(f"  ✅ [{task_id}] 完成 (status={status})")
        completed_task = self.active_task

        # 通知依赖此任务的下游
        self._notify_dependents(completed_task)

        # 如果有被暂停的任务，恢复
        if self.paused_task:
            self.paused_task["status"] = STATUS_QUEUED
            self.queue.push(self.paused_task)
            self.paused_task = None
            logger.info(f"  🔄 恢复被暂停的任务")

        self.active_task = None

    def _schedule_next(self):
        """从队列取出下一个可执行任务"""
        if self.active_task:
            return  # 当前任务还在跑

        # 检查是否有 P0（高优）任务
        next_task_id = self.queue.pop_ready()
        if not next_task_id:
            return

        next_task = self.task_store.get(next_task_id)
        if not next_task:
            return

        # 检查槽位
        if self.slot_manager:
            account_id = next_task.get("accounts", [""])[0] if next_task.get("accounts") else ""
            existing = self.slot_manager.find_account(account_id)
            if existing:
                # 账号已在其他槽位运行
                next_task["status"] = STATUS_QUEUED
                next_task["message"] = f"等待槽位释放: {account_id}"
                self.task_store.save(next_task)
                self.queue.push(next_task)  # 重新入队
                logger.info(f"  ⏳ [{next_task_id}] 账号 {account_id} 忙，重新排队")
                return

        # 执行任务
        self.active_task = next_task
        next_task["status"] = STATUS_RUNNING
        next_task["started_at"] = time.time()
        self.task_store.save(next_task)
        logger.info(f"  ▶️ [{next_task_id}] 开始执行")

        # 同步执行（在调度线程内，不阻塞主循环的下一轮）
        try:
            import threading
            threading.Thread(target=self.executor.execute, args=(next_task,), daemon=True).start()
        except Exception as e:
            logger.error(f"  ❌ [{next_task_id}] 执行失败: {e}")

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
            dep["message"] = "依赖 {} 已完成".format(task_id)
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
                        method="POST",
                    )
                    urllib.request.urlopen(req, timeout=5)
                    logger.info("  [{}] 跨机依赖，已发送到 {}".format(dep_id, dep_machine))
                except Exception as e:
                    logger.warning("  [{}] 跨机发送失败: {}".format(dep_id, e))
            else:
                self.queue.push(dep)
                logger.info("  [{}] 依赖满足，入队 (delay={}s)".format(dep_id, interval))

    def kill_active(self):
        """终止当前活跃任务"""
        if self.active_task:
            self.executor.kill(self.active_task["task_id"])
            self.active_task["status"] = STATUS_FAILED
            self.active_task["error"] = "被用户取消"
            self.task_store.save(self.active_task)
            self.active_task = None
