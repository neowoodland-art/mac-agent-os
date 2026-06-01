"""
engine.py — mc run 真实执行引擎适配层

将 mc run 的参数映射到真实的 orchestrator / douyin_ops 调用。

流程:
  mc run --accounts X --blueprints Y
    → BatchEngine.run()
      → for each account:
          → BrowserManager.launch(account)
          → orchestrator.run(account, blueprint)
          → 收集结果
          → BrowserManager.close()
      → 返回汇总报告

支持:
  - 多账号串行执行
  - 混合随机模式 (每轮随机选蓝图)
  - Provider/语料注入
  - 超时控制
  - 浏览器生命周期管理 (auto_cleanup)
"""
import asyncio
import importlib
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
TOOL_DIR = SCRIPTS_DIR.parent
AGENT_SYNC = Path.home() / "workbuddy-agent-os" / "agent-sync"
AGENT_LOCAL = Path.home() / "workbuddy-agent-os" / "agent-local"
sys.path.insert(0, str(SCRIPTS_DIR))


def resolve_account(account_id: str) -> dict:
    """解析账号信息，从 registry 获取配置"""
    from matrix_mgmt import MatrixManager
    mgr = MatrixManager()
    accounts = mgr.list_accounts()
    for a in accounts:
        if a["id"] == account_id:
            return a
    raise ValueError(f"账号不存在: {account_id}")


def resolve_blueprint(name: str) -> Optional[dict]:
    """解析蓝图"""
    for f in sorted((TOOL_DIR / "blueprints").glob("*.json")):
        bp = json.loads(f.read_text())
        bid = bp.get("id", "")
        bname = bp.get("name", "")
        if name in (bid, bname, f.stem):
            return bp
        if name in f.stem or f.stem in name:
            return json.loads(f.read_text())
    return None


class StepResult:
    """单步执行结果"""
    def __init__(self, op: str, step_id: int, success: bool = True,
                 duration: float = 0, error: str = ""):
        self.op = op
        self.step_id = step_id
        self.success = success
        self.duration = duration
        self.error = error

    def __str__(self):
        icon = "✅" if self.success else "❌"
        return f"{icon} [{self.step_id:2d}] {self.op:20s} ({self.duration:.1f}s) {self.error}"


class AccountRunReport:
    """单账号执行报告"""
    def __init__(self, account: str, blueprint: str, round_idx: int):
        self.account = account
        self.blueprint = blueprint
        self.round = round_idx
        self.steps: List[StepResult] = []
        self.start = time.time()
        self.success = 0
        self.failed = 0

    @property
    def duration(self) -> float:
        return time.time() - self.start

    def add_step(self, result: StepResult):
        self.steps.append(result)
        if result.success:
            self.success += 1
        else:
            self.failed += 1

    def to_dict(self) -> dict:
        return {
            "account": self.account,
            "blueprint": self.blueprint,
            "round": self.round,
            "success": self.success,
            "failed": self.failed,
            "duration": round(self.duration, 1),
            "steps": [{"op": s.op, "step_id": s.step_id, "success": s.success,
                       "duration": round(s.duration, 1), "error": s.error} for s in self.steps],
        }


class BatchReport:
    """批量执行汇总报告"""
    def __init__(self):
        self.accounts: List[str] = []
        self.blueprints: List[str] = []
        self.rounds_total = 0
        self.mix_mode = False
        self.start = time.time()
        self.account_reports: List[AccountRunReport] = []
        self.error: Optional[str] = None

    @property
    def duration(self) -> float:
        return time.time() - self.start

    @property
    def success(self) -> int:
        return sum(r.success for r in self.account_reports)

    @property
    def failed(self) -> int:
        return sum(r.failed for r in self.account_reports)

    def to_dict(self) -> dict:
        return {
            "accounts": self.accounts,
            "blueprints": self.blueprints,
            "rounds": self.rounds_total,
            "mix_mode": self.mix_mode,
            "duration": round(self.duration, 1),
            "total_steps": self.success + self.failed,
            "success": self.success,
            "failed": self.failed,
            "account_reports": [r.to_dict() for r in self.account_reports],
            "error": self.error,
        }


class BatchEngine:
    """批量执行引擎 — 实际对接浏览器操作"""

    def __init__(self, accounts: List[str], blueprints: List[str],
                 rounds: int = 10, mix: bool = False,
                 corpus: List[str] = None):
        self.accounts = accounts
        self.blueprints = blueprints
        self.rounds_total = rounds
        self.mix = mix
        self.corpus = corpus or []
        self._comments: List[str] = []
        self._preloaded = False
        self._tmp_accounts = {}  # 缓存已解析的账号信息

    def _pick_blueprint(self, round_idx: int) -> str:
        """选择本轮蓝图"""
        if self.mix:
            return random.choice(self.blueprints)
        return self.blueprints[(round_idx - 1) % len(self.blueprints)]

    async def run_single(self, account_id: str, blueprint_name: str,
                         round_idx: int, comments: List[str] = None) -> AccountRunReport:
        """对单个账号执行一轮蓝图（真实浏览器操作）"""
        report = AccountRunReport(account_id, blueprint_name, round_idx)

        # 解析蓝图步骤
        bp = resolve_blueprint(blueprint_name)
        if not bp:
            log.warning(f"  ⚠️ 蓝图未找到: {blueprint_name}")
            return report
        steps = bp.get("steps", [])
        log.info(f"  📱 {account_id} → {blueprint_name} ({len(steps)}步)")

        try:
            # ── 使用 orchestrator 执行真实操作 ──
            from orchestrator import YanghaoOrchestrator
            orch = YanghaoOrchestrator()

            # 调用 orchestrator 执行
            orch_report = await orch.run(account_id, blueprint_name)

            # 将 orchestrator 报告转换为我们的格式
            for s in orch_report.steps:
                sr = StepResult(
                    op=s.op if hasattr(s, 'op') else str(getattr(s, 'step_id', '?')),
                    step_id=getattr(s, 'step_id', 0),
                    success=getattr(s, 'atom_result', None) and s.atom_result.success,
                    duration=getattr(s.atom_result, 'elapsed', 0) if hasattr(s, 'atom_result') else 0,
                    error=str(s.atom_result) if hasattr(s, 'atom_result') and not s.atom_result.success else "",
                )
                report.add_step(sr)

            # 打印步骤摘要
            for s in report.steps:
                log.info(f"    {s}")

        except Exception as e:
            log.error(f"  ❌ {account_id} 执行异常: {e}")
            report.failed = len(steps)
            report.error = str(e)

        return report

    async def run(self) -> BatchReport:
        """执行全部任务"""
        from mc.browser import BrowserManager

        report = BatchReport()
        report.accounts = self.accounts
        report.blueprints = self.blueprints
        report.rounds_total = self.rounds_total
        report.mix_mode = self.mix

        # 浏览器生命周期
        bm = BrowserManager()

        try:
            with bm:
                for round_idx in range(1, self.rounds_total + 1):
                    log.info(f"\n{'─'*45}")
                    log.info(f"  🔄 第 {round_idx}/{self.rounds_total} 轮")
                    log.info(f"{'─'*45}")

                    for account_id in self.accounts:
                        bp_name = self._pick_blueprint(round_idx)

                        # 浏览器准备
                        acct_info = resolve_account(account_id)
                        identity_hint = acct_info.get("identity_hint", account_id)
                        bm.prepare(identity_hint)

                        # 执行
                        acct_report = await self.run_single(account_id, bp_name, round_idx)
                        report.account_reports.append(acct_report)

                    # 轮次间隔
                    if round_idx < self.rounds_total:
                        wait = random.uniform(30, 60)
                        log.info(f"\n  ⏳ 等待 {wait:.0f}s 后下一轮...")
                        await asyncio.sleep(wait)

        except Exception as e:
            log.error(f"❌ 批量执行异常: {e}")
            report.error = str(e)

        return report
