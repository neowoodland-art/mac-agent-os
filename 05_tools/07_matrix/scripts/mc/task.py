"""
mc/task.py — 任务调度器 v1.0

智能任务：根据用户意图自动选择蓝图、填充参数、执行。

用法:
  mc task comment --url https://v.douyin.com/xxx --direction 正面
  mc task search --keyword 美食探店 --rounds 3
  mc task collect --keyword 博主名称
  mc task reply --account douyin_test

流程:
  1. 解析任务参数（URL/关键词/方向）
  2. 校验必须参数
  3. 平台识别（抖音/小红书）
  4. 自动选账号（同平台已登录的）
  5. 选蓝图
  6. 填充参数到蓝图
  7. 执行 mc run
"""
import asyncio
import json
import logging
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

PLATFORM_PATTERNS = {
    "douyin": [r"douyin\.com", r"v\.douyin\.com"],
    "xiaohongshu": [r"xiaohongshu\.com", r"xhslink\.com"],
}


def detect_platform(url_or_text: str) -> str:
    """识别平台：douyin / xiaohongshu / unknown"""
    for plat, patterns in PLATFORM_PATTERNS.items():
        for p in patterns:
            if re.search(p, url_or_text.lower()):
                return plat
    return "unknown"


def pick_account(platform: str) -> Optional[str]:
    """从已登录账号中选一个同平台的"""
    try:
        from matrix_mgmt import MatrixManager
        mgr = MatrixManager()
        candidates = []
        for a in mgr.list_accounts():
            if a.get("platform") == platform and a.get("_status") in ("logged_in", "ok"):
                candidates.append(a["id"])
        return random.choice(candidates) if candidates else None
    except Exception:
        return None


@dataclass
class Task:
    """一个待执行的任务"""
    type: str                       # comment / search / collect / reply
    platform: str = ""              # 自动识别的平台
    account: str = ""               # 指定或自动选的账号
    url: str = ""                   # 视频链接（定向评论用）
    keyword: str = ""               # 搜索关键词
    direction: str = ""             # 评论方向（正面/提问/共鸣等）
    comment_text: str = ""          # 具体评论内容（不填则自动生成）
    rounds: int = 1                 # 执行轮数
    blueprint: str = ""             # 自动选的蓝图

    def validate(self) -> list[str]:
        """参数校验，返回错误列表"""
        errors = []
        if self.type == "comment":
            if not self.url:
                errors.append("定向评论必须提供视频链接（--url）")
            self.platform = detect_platform(self.url)
            if self.platform == "unknown" and self.url:
                errors.append(f"无法识别链接平台: {self.url}")
        elif self.type in ("search", "collect"):
            if not self.keyword:
                errors.append("搜索/采集必须提供关键词（--keyword）")
            self.platform = "douyin"  # 默认抖音
        elif self.type == "reply":
            if not self.account:
                errors.append("作者回复必须指定账号（--account）")
            try:
                from matrix_mgmt import MatrixManager
                mgr = MatrixManager()
                acct = mgr.get_account(self.account)
                self.platform = acct.get("platform", "douyin") if acct else "douyin"
            except:
                self.platform = "douyin"
        return errors

    def auto_fill(self):
        """自动填空：选账号、选蓝图、生成评论"""
        # 选账号
        if not self.account and self.platform:
            picked = pick_account(self.platform)
            if picked:
                self.account = picked
                log.info(f"  🤖 自动选账号: {self.account}")
        # 选蓝图
        bp_map = {
            "comment": f"{self.platform}_comment" if self.platform != "unknown" else "douyin_comment",
            "search": f"{self.platform}_search" if self.platform != "unknown" else "douyin_search",
            "collect": f"{self.platform}_collect" if self.platform != "unknown" else "douyin_collect",
            "reply": f"{self.platform}_reply" if self.platform != "unknown" else "douyin_reply",
        }
        self.blueprint = bp_map.get(self.type, "douyin_daily")
        # 方向默认
        if not self.direction:
            self.direction = random.choice(["称赞", "提问", "共鸣", "感慨"])

    def to_task_params(self) -> dict:
        """转为 engine.py 的 task_params 格式"""
        params = {"direction": self.direction}
        if self.url:
            params["url"] = self.url
        if self.keyword:
            params["keyword"] = self.keyword
        if self.comment_text:
            params["comment_text"] = self.comment_text
        return params

    def summary(self) -> str:
        return (f"{self.type.upper():8s} | 平台={self.platform:12s} | "
                f"账号={self.account:20s} | 蓝图={self.blueprint:25s} | "
                f"方向={self.direction}")


async def run_task(task: Task) -> dict:
    """执行任务：校验→填充→跑 mc run"""
    errors = task.validate()
    if errors:
        return {"status": "error", "errors": errors, "task": str(task)}

    task.auto_fill()
    log.info(f"\n{'='*60}")
    log.info(f"  📋 任务: {task.summary()}")
    log.info(f"{'='*60}")

    if not task.account:
        return {"status": "error", "errors": [f"没有可用的{task.platform}账号"], "task": str(task)}

    # 执行
    from mc.engine import BatchEngine, BatchReport
    engine = BatchEngine(
        accounts=[task.account],
        blueprints=[task.blueprint],
        rounds=task.rounds,
        mix=False,
    )
    engine.task_params = task.to_task_params()

    report = await engine.run()
    result = report.to_dict()
    result["task"] = task.summary()
    result["task_params"] = task.to_task_params()
    return result


# ── CLI 入口（供 mc task 命令调用）──

def parse_task_args(args) -> Task:
    """从 argparse 解析 Task"""
    return Task(
        type=args.task_type or "",
        url=getattr(args, "url", ""),
        keyword=getattr(args, "keyword", ""),
        direction=getattr(args, "direction", ""),
        comment_text=getattr(args, "comment", ""),
        account=getattr(args, "account", ""),
        rounds=getattr(args, "rounds", 1),
    )
