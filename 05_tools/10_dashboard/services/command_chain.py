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

    # ── 并行执行引擎 ──

    @classmethod
    def _build_levels(cls, run: ChainRun):
        """将任务按依赖关系分组为层级

        Level 0: 无 depends_on，并行启动
        Level 1: 依赖 Level 0 任务
        Level N: 依赖 Level N-1 任务
        """
        task_map = {t.task_id: t for t in run.tasks}
        levels = []
        remaining = set(task_map.keys())

        while remaining:
            # 找到所有前置任务都已完成的剩余任务
            ready = set()
            for tid in remaining:
                task = task_map[tid]
                if not task.depends_on or task.depends_on not in remaining:
                    ready.add(tid)
            if not ready:
                # 死锁：剩余的都有未满足的依赖
                break
            levels.append(list(ready))
            remaining -= ready

        return levels

    @classmethod
    def _execute_task(cls, run: ChainRun, task: ChainTask):
        """执行单个任务（线程安全）"""
        result = ChainTaskResult(task.task_id)
        result.status = "running"
        result.started_at = datetime.now(timezone.utc).isoformat()

        # 检查前置任务状态
        if task.depends_on:
            dep_result = run.task_results.get(task.depends_on)
            if dep_result and dep_result.status != "completed":
                result.status = "skipped"
                result.error = f"前置任务 {task.depends_on} 未成功完成"
                run.task_results[task.task_id] = result
                cls._save(run)
                return

        # 跳过空账号
        if not task.accounts:
            result.status = "skipped"
            result.error = "账号列表为空"
            result.completed_at = datetime.now(timezone.utc).isoformat()
            run.task_results[task.task_id] = result
            cls._save(run)
            return

        # 执行并重试
        success = False
        for attempt in range(1, task.max_retries + 1):
            if run._stop_requested:
                break
            result.attempts = attempt
            run.task_results[task.task_id] = result
            cls._save(run)

            try:
                from services.command_bus import CommandBus
                cmd_result = CommandBus.dispatch(
                    task.cmd_type, task.accounts,
                    task.params, wait=True
                )
                result.command_result = cmd_result

                # 检查各个机器的子任务状态
                sub_statuses = cmd_result.get("per_machine", {})
                machine_statuses = {m: s.get("status", "unknown") for m, s in sub_statuses.items()}
                all_sub_ok = all(s == "completed" or s == "accepted" or s == "started"
                                for s in machine_statuses.values())

                if cmd_result.get("status") in ("completed", "accepted") or all_sub_ok:
                    success = True
                    break
                else:
                    result.error = cmd_result.get("message", "") or f"机器状态: {machine_statuses}"
                    logger.warning(f"  [{run.chain_id}] {task.task_id} 第{attempt}次失败: {result.error}")
                    if attempt < task.max_retries:
                        time.sleep(5)
            except Exception as e:
                result.error = str(e)
                logger.warning(f"  [{run.chain_id}] {task.task_id} 异常: {e}")
                if attempt < task.max_retries:
                    time.sleep(5)

        # 结果
        if success:
            result.status = "completed"
        else:
            result.status = "failed"
        result.completed_at = datetime.now(timezone.utc).isoformat()
        run.task_results[task.task_id] = result
        cls._save(run)

    @classmethod
    def _execute(cls, chain_id: str):
        """执行接力链（按依赖层级并行执行）"""
        run = cls._load(chain_id)
        if not run:
            return

        run.status = "running"
        cls._save(run)

        # 构建依赖层级
        task_map = {t.task_id: t for t in run.tasks}
        levels = cls._build_levels(run)

        for level_idx, level_tasks in enumerate(levels):
            if run._stop_requested:
                break

            run.current_index = level_idx
            logger.info(f"  [{chain_id}] 执行层级 {level_idx+1}/{len(levels)}: {level_tasks}")
            cls._save(run)

            # 同一层级并行执行
            threads = []
            for tid in level_tasks:
                task = task_map[tid]
                t = threading.Thread(
                    target=cls._execute_task,
                    args=(run, task),
                    daemon=True
                )
                threads.append(t)
                t.start()

            # 等待本层级所有任务完成
            for t in threads:
                t.join()

            # 检查是否有任务失败需要终止
            if not run._stop_requested:
                for tid in level_tasks:
                    tr = run.task_results.get(tid)
                    if tr and tr.status == "failed":
                        task = task_map[tid]
                        if task.on_failure == "abort":
                            run.status = "failed"
                            run.error = f"任务 {tid} 失败后终止"
                            run.completed_at = datetime.now(timezone.utc).isoformat()
                            cls._save(run)
                            cls._running.pop(chain_id, None)
                            return
                # 层间冷却
                if level_idx < len(levels) - 1:
                    time.sleep(3)

        # 最终状态
        if not run._stop_requested:
            all_ok = all(
                run.task_results.get(t.task_id, ChainTaskResult(t.task_id)).status == "completed"
                for t in run.tasks if t.accounts  # 空账号skipped不计入失败
            )
            run.status = "completed" if all_ok else "failed"
            if not run.error:
                failed = [t.task_id for t in run.tasks
                         if run.task_results.get(t.task_id, ChainTaskResult(t.task_id)).status not in ("completed", "skipped")]
                if failed:
                    run.status = "failed"
                    run.error = f"以下任务失败: {', '.join(failed)}"
        else:
            run.status = "cancelled"

        run.completed_at = datetime.now(timezone.utc).isoformat()
        cls._save(run)
        cls._running.pop(chain_id, None)

        # 链完成后自动触发联邦采集器拉取最新数据
        if run.status == "completed":
            try:
                from services.fleet_collector import collect_all
                logger.info(f"  [{chain_id}] 链完成，自动触发联邦采集...")
                collect_all()
            except Exception as e:
                logger.warning(f"  [{chain_id}] 联邦采集自动触发失败: {e}")

    _save_locks: dict = {}

    @classmethod
    def _get_save_lock(cls, chain_id: str) -> threading.Lock:
        """按 chain_id 获取锁，确保同一链的写入串行化"""
        if chain_id not in cls._save_locks:
            cls._save_locks[chain_id] = threading.Lock()
        return cls._save_locks[chain_id]

    @classmethod
    def _save(cls, run: ChainRun):
        """持久化接力链状态（按chain_id加锁，原子写入）"""
        with cls._get_save_lock(run.chain_id):
            path = CHAINS_DIR / f"{run.chain_id}.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False))
            tmp.replace(path)

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
        except Exception as e:
            logger.warning(f"  ⚠️ 接力链加载失败 [{chain_id}]: {e}")
            # 尝试修复：删除最后一行非JSON内容
            try:
                path = CHAINS_DIR / f"{chain_id}.json"
                raw = path.read_text()
                # 找到第一个完整的 JSON 对象
                import re as _re
                m = _re.search(r'^(\{[^{}]*(\{[^{}]*\})*[^{}]*\})', raw, _re.DOTALL)
                if m:
                    data = json.loads(m.group(1))
                    path.write_text(m.group(1))
                    logger.info(f"  ✅ 接力链文件已修复 [{chain_id}]")
                    return cls._load(chain_id)
            except Exception:
                pass
            return None
