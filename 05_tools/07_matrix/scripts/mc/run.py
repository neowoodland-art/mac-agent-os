"""
run.py — mc run 批量执行引擎

支持:
  - 多账号 + 多蓝图 + 多轮数
  - 混合随机模式 (每轮随机选蓝图)
  - 间隔控制
  - 语料库选择
  - 浏览器生命周期管理
  - 日志输出

执行策略:
  串行 (默认) : A跑完所有 → B跑完所有
  并行 (--parallel) : A + B 同时
  混合随机 (--mix) : 每轮从蓝图中随机选一个执行

每个蓝图 = 步骤序列
每步 = 原子操作 + 参数 + 前后置验证
"""
import asyncio
import importlib.util
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
TOOL_DIR = SCRIPTS_DIR.parent
AGENT_SYNC = Path.home() / "workbuddy-agent-os" / "agent-sync"
AGENT_LOCAL = Path.home() / "workbuddy-agent-os" / "agent-local"
sys.path.insert(0, str(SCRIPTS_DIR))

log = logging.getLogger(__name__)


def load_blueprint(name: str) -> Optional[dict]:
    """从 blueprints/ 或内存定义加载蓝图"""
    bp_dir = TOOL_DIR / "blueprints"
    # 精准匹配
    for f in sorted(bp_dir.glob("*.json")):
        bp = json.loads(f.read_text())
        bid = bp.get("id", "")
        bname = bp.get("name", "")
        if name in (bid, bname, f.stem):
            return bp
    # 模糊匹配 (用户简写 → 完整文件名)
    for f in sorted(bp_dir.glob("*.json")):
        if name in f.stem or f.stem in name:
            return json.loads(f.read_text())
    return None


def load_corpus(categories: List[str]) -> List[str]:
    """从语料库加载评论"""
    from mc.corpus import CorpusManager
    cm = CorpusManager()
    return cm.get_comments(categories, count=50)


def log_step(step_id: int, op: str, status: str, detail: str = ""):
    """步骤日志"""
    icon = {"success": "✅", "failed": "❌", "skip": "⏭️", "running": "▶️"}.get(status, "➡️")
    now = datetime.now().strftime("%H:%M:%S")
    print(f"  {icon} [{now}] [{step_id:2d}] {op:20s} {detail}", flush=True)


def log_round(round_idx: int, total: int):
    """轮次日志"""
    print(f"\n{'─'*45}", flush=True)
    print(f"  🔄 第 {round_idx}/{total} 轮", flush=True)
    print(f"{'─'*45}", flush=True)


class BatchRunner:
    """批量执行引擎"""

    def __init__(
        self,
        accounts: List[str],
        blueprints: List[str],
        rounds: int = 10,
        interval_range: tuple = (30, 60),
        mix: bool = False,
        corpus: List[str] = None,
        engine: str = "auto",
        daemon: bool = False,
    ):
        self.accounts = accounts
        self.blueprints = blueprints
        self.rounds = rounds
        self.interval_min, self.interval_max = interval_range
        self.mix = mix
        self.corpus = corpus or []
        self.engine = engine
        self.daemon = daemon
        self._comments: List[str] = []

        # 预加载语料
        if self.corpus:
            self._comments = load_corpus(self.corpus)
            log.info(f"📚 预加载语料: {len(self._comments)} 条")

    def _get_interval(self) -> float:
        """获取随机间隔"""
        return random.uniform(self.interval_min, self.interval_max)

    def _pick_blueprint(self, round_idx: int) -> str:
        """选择当前轮要执行的蓝图"""
        if self.mix:
            # 混合随机模式：每轮随机选一个蓝图
            return random.choice(self.blueprints)
        else:
            # 顺序模式：按顺序执行
            return self.blueprints[(round_idx - 1) % len(self.blueprints)]

    def _get_comment(self) -> str:
        """获取一条评论"""
        if self._comments:
            return random.choice(self._comments)
        return "好内容"

    async def run_account(self, account: str, round_idx: int, bp_name: str) -> dict:
        """对单个账号执行一轮蓝图

        这层是实际的浏览器操作调用，未来对接 orchestrator/douyin_ops
        当前返回模拟结果，真正的自动化操作需要对接浏览器引擎
        """
        bp = load_blueprint(bp_name)
        steps = bp.get("steps", []) if bp else []

        log.info(f"  📱 {account} → 蓝图: {bp_name} ({len(steps)}步)")

        result = {
            "account": account,
            "blueprint": bp_name,
            "round": round_idx,
            "total_steps": len(steps),
            "success": 0,
            "failed": 0,
            "steps": [],
        }

        for i, step in enumerate(steps):
            op = step.get("op", "unknown")
            args = step.get("args", {})
            step_id = step.get("step_id", i + 1)

            log_step(step_id, op, "running")

            try:
                # 模拟执行（后续对接真�的 atom_ops）
                await asyncio.sleep(random.uniform(0.5, 2.0))

                # 如果参数中有 keyword，替换评论
                if "keyword" in args and self._comments:
                    args["keyword"] = self._get_comment()

                result["steps"].append({
                    "step_id": step_id,
                    "op": op,
                    "status": "success",
                    "duration": random.uniform(1, 3),
                })
                result["success"] += 1
                log_step(step_id, op, "success", f"({result['steps'][-1]['duration']:.1f}s)")

                # 操作间隔（步骤之间）
                if i < len(steps) - 1:
                    wait = self._get_interval() * 0.3  # 步骤间隔比轮次间隔短
                    await asyncio.sleep(wait)

            except Exception as e:
                result["steps"].append({
                    "step_id": step_id,
                    "op": op,
                    "status": "failed",
                    "error": str(e),
                })
                result["failed"] += 1
                log_step(step_id, op, "failed", str(e))

        return result

    async def run(self) -> dict:
        """执行全部任务"""

        # 浏览器生命周期（启动）
        from mc.browser import BrowserManager
        bm = BrowserManager()

        start_time = time.time()
        report = {
            "started_at": datetime.now().isoformat(),
            "accounts": self.accounts,
            "blueprints": self.blueprints,
            "rounds": self.rounds,
            "mix_mode": self.mix,
            "total_steps": 0,
            "success": 0,
            "failed": 0,
            "duration": 0,
            "account_reports": [],
        }

        try:
            with bm:
                for round_idx in range(1, self.rounds + 1):
                    log_round(round_idx, self.rounds)

                    # 为每个账号分配本轮要执行的蓝图
                    for account in self.accounts:
                        bp_name = self._pick_blueprint(round_idx)
                        acct_result = await self.run_account(account, round_idx, bp_name)
                        report["account_reports"].append(acct_result)

                        # 累加统计
                        report["total_steps"] += acct_result["total_steps"]
                        report["success"] += acct_result["success"]
                        report["failed"] += acct_result["failed"]

                    # 轮次间��隔（所有账号完成一轮后）
                    if round_idx < self.rounds:
                        wait = self._get_interval()
                        log.info(f"\n  ⏳ 等待 {wait:.0f} 秒后下一轮...")
                        await asyncio.sleep(wait)

        except Exception as e:
            log.error(f"❌ 执行异常: {e}")
            report["error"] = str(e)

        report["duration"] = time.time() - start_time
        return report
