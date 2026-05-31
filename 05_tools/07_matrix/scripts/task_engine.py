#!/usr/bin/env python3
"""
任务蓝图引擎 - 解析 JSON 蓝图并自动执行
用法: python task_engine.py <blueprint_name> [--account <account_id>] [--dry-run]
"""
import argparse
import asyncio
import json
import random
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ── 路径配置 ──────────────────────────────────────────────────────
from local_paths import data_path, code_dir
BASE_DIR = code_dir()
DB_PATH  = data_path("matrix.db")
BLUEPRINT_DIR = code_dir() / "blueprints"

# ── 原子操作定义 ──────────────────────────────────────────────────
OPERATIONS: dict[str, callable] = {}
_DOYOPS = None  # DouyinOps 实例引用，用于设置 execution_id


def _make_douyin_op(op_name: str, func):
    """包装 DouyinOps 方法，自动注入 step_id"""
    async def wrapper(step_id: int = 0, **kwargs):
        return await func(step_id=step_id, **kwargs)
    return wrapper


def _register_ops(connector, db=None):
    """动态注册异步操作到全局字典"""
    global OPERATIONS, _DOYOPS

    # 基础 CDP 操作
    base_ops = {
        "goto":              connector.goto,
        "click":             lambda **kw: connector.page.click(**kw),
        "swipe_up":          connector.swipe_up,
        "swipe_down":        lambda **kw: connector.swipe_up(distance=-kw.get("distance", 600)),
        "touch_tap":         connector.touch_tap,
        "wait":              lambda **kw: asyncio.sleep(kw.get("seconds", 2)),
        "remove_overlays":   connector.remove_overlays,
        "screenshot":        lambda **kw: connector.page.screenshot(**kw),
        "evaluate":         lambda **kw: connector.page.evaluate(kw.get("script")),
        "fill":             lambda **kw: connector.page.fill(**kw),
        "press":            lambda **kw: connector.page.press(**kw),
    }

    # Douyin 原子操作
    from douyin_ops import DouyinOps
    dyops = DouyinOps(connector.page, db=db)
    _DOYOPS = dyops

    douyin_ops = {}
    for name in dir(dyops):
        if name.startswith("_") or name in ("page", "db", "db_path", "execution_id",
                                             "_action_counts", "_session_start"):
            continue
        attr = getattr(dyops, name)
        if callable(attr):
            douyin_ops[name] = _make_douyin_op(name, attr)

    OPERATIONS = {**base_ops, **douyin_ops}

# ── 熔断器 ──────────────────────────────────────────────────────
class CircuitBreaker:
    """连续失败 N 次后暂停指定时间"""

    def __init__(self, max_failures: int = 3, pause_seconds: int = 1800):
        self.count = 0
        self.max_failures = max_failures
        self.pause_seconds = pause_seconds
        self.pause_until: float | None = None

    def record_success(self):
        self.count = 0
        self.pause_until = None

    def record_failure(self) -> bool:
        """返回 True 表示熔断触发（已暂停）"""
        self.count += 1
        if self.count >= self.max_failures:
            self.pause_until = time.time() + self.pause_seconds
            print(f"⚠️  连续失败 {self.max_failures} 次，熔断触发，暂停 {self.pause_seconds}s")
            return True
        return False

    def is_paused(self) -> bool:
        if self.pause_until and time.time() < self.pause_until:
            remaining = int(self.pause_until - time.time())
            print(f"⏸  熔断中，还剩 {remaining}s...")
            return True
        return False


# ── 蓝图执行器 ───────────────────────────────────────────────────
class BlueprintRunner:
    """解析并执行任务蓝图"""

    def __init__(self, conn, db: sqlite3.Connection):
        self.conn = conn
        self.db = db
        self.circuit = CircuitBreaker()

    def _log_exec(self, blueprint_id: str, account_id: str,
                  status: str, duration: float, error: str = ""):
        cur = self.db.cursor()
        cur.execute("""
            INSERT INTO executions (blueprint_id, account_id, status, duration_sec, error_msg)
            VALUES (?, ?, ?, ?, ?)
        """, (blueprint_id, account_id, status, round(duration, 2), error))
        self.db.commit()

    async def run_step(self, step: dict) -> bool:
        """执行单个步骤，返回成功/失败"""
        op = step.get("op") or step.get("operation")
        if not op:
            print(f"  ⚠️  步骤缺少 op 字段: {step}")
            return False

        handler = OPERATIONS.get(op)
        if not handler:
            print(f"  ⚠️  未知操作: {op}")
            return False

        args = step.get("args", {})
        wait_after = step.get("wait_after", 1.5)
        wait_jitter = step.get("wait_jitter", 0.5)
        retry = step.get("retry", 1)
        step_id = step.get("step_id", 0)

        for attempt in range(retry):
            try:
                # DouyinOps 方法签名: func(step_id=0, **kwargs)
                # 先传 step_id，再传其他参数
                import inspect
                sig = inspect.signature(handler)
                params = list(sig.parameters.keys())
                if params and params[0] in ("step_id", "stepId"):
                    await handler(step_id=step_id, **args)
                else:
                    await handler(**args)
                await asyncio.sleep(wait_after + random.uniform(-wait_jitter, wait_jitter))
                return True
            except Exception as e:
                if attempt < retry - 1:
                    print(f"  ⚠️  [{op}] 重试 {attempt + 1}/{retry}: {e}")
                    await asyncio.sleep(2 ** attempt)
                else:
                    print(f"  ❌ [{op}] 失败: {e}")
                    return False
        return False

    async def run_blueprint(
        self,
        blueprint: dict,
        account_id: str,
        connector,
        dry_run: bool = False
    ) -> tuple[bool, float]:
        """执行完整蓝图，返回 (是否成功, 耗时秒)"""
        bp_id  = blueprint["id"]
        steps  = blueprint.get("steps", [])
        start  = time.time()

        # 生成本次执行的 execution_id，供 DouyinOps 记录操作日志
        exec_id = str(uuid.uuid4())
        if _DOYOPS:
            _DOYOPS.execution_id = exec_id

        print(f"\n{'='*50}")
        print(f"🚀 执行蓝图: {bp_id} | 账号: {account_id} | {'[DRY-RUN]' if dry_run else ''}")
        print(f"{'='*50}")

        if dry_run:
            for i, step in enumerate(steps, 1):
                print(f"  {i}. {step.get('op')} → {step.get('args', {})}")
            return True, time.time() - start

        for i, step in enumerate(steps, 1):
            if self.circuit.is_paused():
                return False, time.time() - start

            print(f"  [{i}/{len(steps)}] {step.get('op')}")
            ok = await self.run_step(step)
            if not ok:
                error = f"step {i} failed: {step.get('op')}"
                self._log_exec(bp_id, account_id, "failed", time.time() - start, error)
                self.circuit.record_failure()
                return False, time.time() - start

        self.circuit.record_success()
        self._log_exec(bp_id, account_id, "success", time.time() - start)
        print(f"✅ 蓝图 {bp_id} 执行完成，耗时 {time.time() - start:.1f}s")
        return True, time.time() - start


# ── 主程序 ───────────────────────────────────────────────────────
async def main():
    parser = argparse.ArgumentParser(description="Matrix 任务蓝图引擎")
    parser.add_argument("blueprint", help="蓝图名称（不含 .json）")
    parser.add_argument("--account", default="account_01", help="账号 ID")
    parser.add_argument("--dry-run", action="store_true", help="仅打印步骤，不执行")
    parser.add_argument("--port", type=int, default=9222, help="CDP 端口")
    args = parser.parse_args()

    # 加载蓝图
    bp_path = BLUEPRINT_DIR / f"{args.blueprint}.json"
    if not bp_path.exists():
        # 尝试找 docs 目录
        bp_path = BASE_DIR / "docs" / "blueprints" / f"{args.blueprint}.json"
    if not bp_path.exists():
        print(f"❌ 蓝图不存在: {bp_path}")
        sys.exit(1)

    with open(bp_path, encoding="utf-8") as f:
        blueprint = json.load(f)

    # 连接数据库
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    db.execute("CREATE TABLE IF NOT EXISTS executions (id INTEGER PRIMARY KEY AUTOINCREMENT, blueprint_id TEXT, account_id TEXT, status TEXT, duration_sec REAL, error_msg TEXT, created_at TEXT DEFAULT (datetime('now')))")

    if args.dry_run:
        # dry-run：只打印步骤
        for i, step in enumerate(blueprint.get("steps", []), 1):
            print(f"  {i}. {step.get('op')} → {step.get('args', {})}")
        print(f"\n✅ 蓝图 {blueprint['id']} dry-run 完成")
        db.close()
        sys.exit(0)

    # 连接浏览器
    from cdp_connector import CDPConnector
    connector = CDPConnector(port=args.port)
    _register_ops(connector, db=db)

    try:
        await connector.connect()
        await connector.init_anti_detection()
        runner = BlueprintRunner(connector, db)
        ok, duration = await runner.run_blueprint(blueprint, args.account, connector, dry_run=False)
        sys.exit(0 if ok else 1)
    finally:
        await connector.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
