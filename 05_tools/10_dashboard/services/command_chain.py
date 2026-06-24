"""
command_chain.py — 接力执行链系统

将一个或多个命令按顺序串联，上一步成功自动触发下一步。
支持失败重试、超时控制、状态查询、取消。

使用:
  from services.command_chain import CommandChain
  
  chain = CommandChain.create("nurture-then-collect", tasks)
  status = CommandChain.get_status(chain.chain_id)
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

logger = logging.getLogger("dashboard.command_chain")

_THIS_DIR = Path(__file__).resolve().parent
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL", str(Path.home() / "workbuddy-agent-os" / "agent-local")))

CHAINS_DIR = AGENT_LOCAL / "runtime" / "chains"
CHAINS_DIR.mkdir(parents=True, exist_ok=True)


class ChainTask:
    """接力链中的单个任务定义"""

    def __init__(self, task_id: str, cmd_type: str, accounts: list,
                 params: dict = None, depends_on: str = None,
                 max_retries: int = 2, timeout: int = 600,
                 on_failure: str = "abort"):
        self.task_id = task_id
        self.cmd_type = cmd_type          # nurture/collect/login/comment
        self.accounts = accounts
        self.params = params or {}
        self.depends_on = depends_on      # 前置 task_id, None=第一个
        self.max_retries = max_retries
        self.timeout = timeout
        self.on_failure = on_failure      # "abort" | "skip" | "retry"

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "type": self.cmd_type,
            "accounts": self.accounts,
            "params": self.params,
            "depends_on": self.depends_on,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "on_failure": self.on_failure,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            task_id=d["task_id"],
            cmd_type=d["type"],
            accounts=d["accounts"],
            params=d.get("params", {}),
            depends_on=d.get("depends_on"),
            max_retries=d.get("max_retries", 2),
            timeout=d.get("timeout", 600),
            on_failure=d.get("on_failure", "abort"),
        )


class ChainRun:
    """一次接力链的执行实例"""

    def __init__(self, chain_id: str, name: str, tasks: list):
        self.chain_id = chain_id
        self.name = name
        self.tasks = tasks                 # list[ChainTask]
        self.status = "pending"            # pending/running/completed/failed
        self.current_index = -1            # 当前执行到的 task 索引
        self.task_results = {}             # {task_id: ChainTaskResult}
        self.error = ""
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.completed_at = None
        self._stop_requested = False

    def to_dict(self):
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "status": self.status,
            "current_index": self.current_index,
            "total_tasks": len(self.tasks),
            "tasks": [t.to_dict() for t in self.tasks],
            "task_results": {k: v.to_dict() for k, v in self.task_results.items()},
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class ChainTaskResult:
    """单个任务的执行结果"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status = "pending"            # pending/running/completed/failed/skipped
        self.attempts = 0
        self.command_result = None
        self.error = ""
        self.started_at = None
        self.completed_at = None

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "status": self.status,
            "attempts": self.attempts,
            "command_result": self.command_result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class CommandChain:
    """接力执行链调度器"""

    _locks = {}
    _running = {}

    @classmethod
    def create(cls, name: str, tasks: list) -> ChainRun:
        """创建一条接力链

        Args:
            name: 链名称
            tasks: list[ChainTask] 或 list[dict]

        Returns:
            ChainRun 实例
        """
        # 转换 dict 为 ChainTask
        task_objects = []
        for t in tasks:
            if isinstance(t, dict):
                task_objects.append(ChainTask.from_dict(t))
            else:
                task_objects.append(t)

        chain_id = str(uuid4())[:12]
        run = ChainRun(chain_id, name, task_objects)

        # 持久化
        cls._save(run)

        # 异步启动执行
        thread = threading.Thread(target=cls._execute, args=(chain_id,), daemon=True)
        cls._running[chain_id] = thread
        thread.start()

        return run

    @classmethod
    def get_status(cls, chain_id: str) -> Optional[dict]:
        """查询接力链状态"""
        run = cls._load(chain_id)
        if run:
            return run.to_dict()
        return None

    @classmethod
    def cancel(cls, chain_id: str) -> dict:
        """取消接力链"""
        run = cls._load(chain_id)
        if not run:
            return {"error": f"接力链不存在: {chain_id}"}
        run._stop_requested = True
        run.status = "cancelled"
        run.completed_at = datetime.now(timezone.utc).isoformat()
        cls._save(run)
        return {"ok": True, "chain_id": chain_id, "status": "cancelled"}

    @classmethod
    def list_chains(cls, limit: int = 20) -> list:
        """列出最近创建的接力链"""
        chains = []
        if CHAINS_DIR.exists():
            for f in sorted(CHAINS_DIR.iterdir(), reverse=True)[:limit]:
                if f.suffix == ".json":
                    try:
                        data = json.loads(f.read_text())
                        chains.append({
                            "chain_id": data.get("chain_id", f.stem),
                            "name": data.get("name", ""),
                            "status": data.get("status", ""),
                            "total_tasks": len(data.get("tasks", [])),
                            "current_index": data.get("current_index", -1),
                            "created_at": data.get("created_at", ""),
                            "completed_at": data.get("completed_at", ""),
                        })
                    except Exception:
                        pass
        return chains

    # ── 内部方法 ──

    @classmethod
    def _execute(cls, chain_id: str):
        """执行接力链（在后台线程运行）"""
        run = cls._load(chain_id)
        if not run:
            return

        run.status = "running"
        cls._save(run)

        for idx, task in enumerate(run.tasks):
            if run._stop_requested:
                break

            run.current_index = idx
            result = ChainTaskResult(task.task_id)
            result.status = "running"
            result.started_at = datetime.now(timezone.utc).isoformat()
            run.task_results[task.task_id] = result
            cls._save(run)

            # 等待前置任务完成
            if task.depends_on:
                dep_result = run.task_results.get(task.depends_on)
                if dep_result and dep_result.status != "completed":
                    result.status = "skipped"
                    result.error = f"前置任务 {task.depends_on} 未成功完成"
                    run.task_results[task.task_id] = result
                    cls._save(run)
                    continue

            # 执行任务（支持重试）
            success = False
            for attempt in range(1, task.max_retries + 1):
                if run._stop_requested:
                    break

                result.attempts = attempt
                cls._save(run)

                try:
                    from services.command_bus import CommandBus
                    cmd_result = CommandBus.dispatch(
                        task.cmd_type, task.accounts,
                        task.params, wait=True
                    )
                    result.command_result = cmd_result

                    if cmd_result.get("status") in ("completed", "accepted"):
                        success = True
                        break
                    else:
                        result.error = cmd_result.get("message", "未知错误")
                        logger.warning(f"  [{chain_id}] {task.task_id} 第{attempt}次失败: {result.error}")
                        if attempt < task.max_retries:
                            time.sleep(5)  # 重试前等待
                except Exception as e:
                    result.error = str(e)
                    logger.warning(f"  [{chain_id}] {task.task_id} 异常: {e}")
                    if attempt < task.max_retries:
                        time.sleep(5)

            # 处理结果
            if success:
                result.status = "completed"
                result.completed_at = datetime.now(timezone.utc).isoformat()
            else:
                result.status = "failed"
                result.completed_at = datetime.now(timezone.utc).isoformat()
                if task.on_failure == "abort":
                    run.status = "failed"
                    run.error = f"任务 {task.task_id} 失败后终止"
                    run.task_results[task.task_id] = result
                    run.completed_at = datetime.now(timezone.utc).isoformat()
                    cls._save(run)
                    return
                elif task.on_failure == "skip":
                    result.status = "skipped"
                    # 继续下一个

            run.task_results[task.task_id] = result
            cls._save(run)

            # 任务间冷却
            if idx < len(run.tasks) - 1:
                time.sleep(3)

        # 完成
        if not run._stop_requested:
            all_completed = all(
                r.status == "completed"
                for r in run.task_results.values()
            )
            run.status = "completed" if all_completed else "failed"
            if not run.error:
                failed = [t.task_id for t in run.tasks
                         if run.task_results.get(t.task_id, ChainTaskResult(t.task_id)).status != "completed"]
                if failed:
                    run.status = "failed"
                    run.error = f"以下任务失败: {', '.join(failed)}"
        else:
            run.status = "cancelled"

        run.completed_at = datetime.now(timezone.utc).isoformat()
        cls._save(run)
        cls._running.pop(chain_id, None)

    @classmethod
    def _save(cls, run: ChainRun):
        """持久化接力链状态"""
        path = CHAINS_DIR / f"{run.chain_id}.json"
        path.write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False))

    @classmethod
    def _load(cls, chain_id: str) -> Optional[ChainRun]:
        """加载接力链"""
        path = CHAINS_DIR / f"{chain_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            run = ChainRun(data["chain_id"], data["name"],
                          [ChainTask.from_dict(t) for t in data["tasks"]])
            run.status = data.get("status", "pending")
            run.current_index = data.get("current_index", -1)
            run.task_results = {}
            for tid, rd in data.get("task_results", {}).items():
                r = ChainTaskResult(tid)
                r.status = rd.get("status", "pending")
                r.attempts = rd.get("attempts", 0)
                r.command_result = rd.get("command_result")
                r.error = rd.get("error", "")
                r.started_at = rd.get("started_at")
                r.completed_at = rd.get("completed_at")
                run.task_results[tid] = r
            run.error = data.get("error", "")
            run.created_at = data.get("created_at", "")
            run.completed_at = data.get("completed_at")
            return run
        except Exception:
            return None
