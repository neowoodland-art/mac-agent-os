#!/usr/bin/env python3
"""
任务调度器 - 按时间规则自动触发蓝图
用法: python task_scheduler.py [--once]
"""
import asyncio
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from local_paths import config_path, data_path, code_dir

BASE_DIR = code_dir()
DB_PATH    = data_path("matrix.db")
CONFIG_DIR = config_path()
TZ_SH      = ZoneInfo("Asia/Shanghai")

# ── 加载任务配置 ──────────────────────────────────────────────────
def load_tasks() -> list[dict]:
    """从 config/tasks.yaml 加载任务计划"""
    tasks_file = CONFIG_DIR / "tasks.yaml"
    if not tasks_file.exists():
        return []
    with open(tasks_file, encoding="utf-8") as f:
        return yaml.safe_load(f).get("tasks", [])

def load_accounts() -> dict[str, dict]:
    """从 accounts.yaml 加载账号配置"""
    accounts_file = CONFIG_DIR / "accounts.yaml"
    if not accounts_file.exists():
        return {}
    with open(accounts_file, encoding="utf-8") as f:
        return {a["id"]: a for a in yaml.safe_load(f).get("accounts", [])}

def next_run(spec: str) -> datetime:
    """简单解析 HH:MM 格式，返回今天/明天的下一次执行时间"""
    now = datetime.now(TZ_SH)
    hour, minute = map(int, spec.split(":"))
    nd = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if nd <= now:
        nd += __import__("datetime").timedelta(days=1)
    return nd

def should_run(task: dict) -> bool:
    """判断任务是否到达执行时间"""
    last_path = BASE_DIR / ".last_run" / f"{task['id']}.txt"
    if last_path.exists():
        last = datetime.fromisoformat(last_path.read_text().strip())
        last = last.replace(tzinfo=TZ_SH)
        now  = datetime.now(TZ_SH)
        # 最少间隔 30 分钟
        if (now - last).total_seconds() < 1800:
            return False
    return True

def mark_run(task_id: str):
    """标记任务已执行"""
    BASE_DIR.joinpath(".last_run").mkdir(exist_ok=True)
    (BASE_DIR / ".last_run" / f"{task_id}.txt").write_text(
        datetime.now(TZ_SH).isoformat()
    )

def record_status(task_id: str, account_id: str, status: str, msg: str = ""):
    now = datetime.now(TZ_SH).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {task_id} [{account_id}] → {status} {msg}")

async def run_task(task: dict, accounts: dict):
    """执行单个任务"""
    bp_name = task.get("blueprint", "")
    if not bp_name:
        return

    import subprocess
    for account_id in task.get("accounts", []):
        acc = accounts.get(account_id, {})
        port = acc.get("port", 9222)
        cmd = [
            sys.executable,
            str(BASE_DIR / "scripts" / "task_engine.py"),
            bp_name,
            "--account", account_id,
            "--port", str(port),
        ]
        print(f"\n📦 触发: {bp_name} @ {account_id}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                record_status(task["id"], account_id, "✅ 成功")
            else:
                record_status(task["id"], account_id, "❌ 失败", result.stderr[:100])
        except subprocess.TimeoutExpired:
            record_status(task["id"], account_id, "⏱ 超时")
        except Exception as e:
            record_status(task["id"], account_id, "💥 异常", str(e)[:80])

async def scheduler_loop(once: bool = False):
    """主调度循环"""
    print(f"\n{'='*50}")
    print(f"Matrix 任务调度器启动 | {datetime.now(TZ_SH).strftime('%Y-%m-%d %H:%M:%S CST')}")
    print(f"{'='*50}")

    while True:
        tasks = load_tasks()
        accounts = load_accounts()
        now = datetime.now(TZ_SH)
        due = []

        for task in tasks:
            if task.get("enabled", True) and should_run(task):
                due.append(task)
                mark_run(task["id"])

        if due:
            print(f"\n📋 本轮待执行: {[t['id'] for t in due]}")
            for task in due:
                await run_task(task, accounts)
        else:
            print(f"\n⏳ {now.strftime('%H:%M:%S')} 无待执行任务，休眠 5 分钟...")

        if once:
            break
        await asyncio.sleep(300)  # 每 5 分钟检查一次

if __name__ == "__main__":
    once = "--once" in sys.argv
    asyncio.run(scheduler_loop(once=once))
