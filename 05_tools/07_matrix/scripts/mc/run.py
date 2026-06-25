"""
run.py — mc run 批量执行引擎 (v1.1 - 真实引擎)

使用 mc/engine.py 的 BatchEngine 实际启动浏览器执行原子操作，
而非模拟步骤。

支持:
  - 多账号 + 多蓝图 + 多轮数
  - 混合随机模式
  - 浏览器生命周期管理
  - 日志输出

委派给:
  → mc/engine.BatchEngine.run_single() → orchestrator.YanghaoOrchestrator()
    → BrowserManager.launch() → AtomOps.execute() → 真实浏览器操作
"""
import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

log = logging.getLogger(__name__)


class BatchRunner:
    """批量执行引擎 — 封装 BatchEngine 提供 CLI 友好接口"""

    def __init__(self, accounts, blueprints, rounds=10,
                 interval_range=(30, 60), mix=False,
                 corpus=None, engine="auto", daemon=False,
                 stagger="15-30", keep_open=False,
                 max_browsers=3, url="", comment_text="",
                 reply_text=""):
        self.accounts = accounts
        self.blueprints = blueprints
        self.rounds = rounds
        self.mix = mix
        self.interval_min, self.interval_max = interval_range
        self.corpus = corpus or []
        self.engine_type = engine
        self.daemon = daemon
        self.stagger = stagger
        self.keep_open = keep_open
        self.max_browsers = max_browsers
        self.url = url
        self.comment_text = comment_text
        self.reply_text = reply_text

    async def run(self) -> dict:
        """执行 — 委托给 BatchEngine"""
        from mc.engine import BatchEngine

        log.info(f"  🚀 使用真实浏览器引擎执行")
        log.info(f"     账号: {self.accounts}")
        log.info(f"     蓝图: {self.blueprints}")
        log.info(f"     轮数: {self.rounds} | 模式: {'混合随机' if self.mix else '顺序'}")
        log.info(f"     浏览器上限: {self.max_browsers} | 错峰: {self.stagger}s | keep_open: {self.keep_open}")

        engine = BatchEngine(
            accounts=self.accounts,
            blueprints=self.blueprints,
            rounds=self.rounds,
            mix=self.mix,
            corpus=self.corpus,
            stagger=self.stagger,
            keep_open=self.keep_open,
            max_browsers=self.max_browsers,
            task_params={
                "url": self.url,
                "comment_text": self.comment_text,
                "reply_text": self.reply_text,
                "direction": "",
            },
        )

        report = await engine.run()
        return report.to_dict()
