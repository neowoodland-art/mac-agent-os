"""
interact.py — 互动编排引擎 (InteractOrchestrator)

负责:
  1. 解析互动策略
  2. 生成识别码（三级接力用）
  3. 生成时间线
  4. 分配 chain_position 和 target_code
  5. 依次执行（含步间等待）

识别码系统（三级接力）:
  first账号 发评时末尾加 "🌸XX"
  reply账号 搜 "🌸XX" → 找到 → 回复（末尾加"🌸YY"）
  second账号 搜 "🌸YY" → 找到 → 回复

  识别码格式: 🌸 + 两位数字 (如 🌸42)
  - 看起来像自然emoji，不触发风控
  - 100个组合，一轮接力用2个
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger("interact")

# ── 识别码系统 ──────────────────────────────────────────

_CODE_POOL = list(range(10, 100))  # 10-99

def _alloc_codes(count: int = 2) -> list[int]:
    """分配不重复的识别码"""
    random.shuffle(_CODE_POOL)
    return _CODE_POOL[:count]

def _fmt_code(n: int) -> str:
    """🌸 + 两位数字"""
    return f"🌸{n:02d}"

def _strip_code(text: str) -> str:
    """去除末尾的识别码"""
    import re
    return re.sub(r'\s*🌸\d{2}\s*$', '', text).strip()


# ── 互动策略定义 ──────────────────────────────────────────

STRATEGIES = {
    "comment": {
        "label": "定向评论", "blueprint": "interact_comment",
        "description": "给指定视频发评论",
    },
    "chain": {
        "label": "三级接力", "blueprint": "interact_chain",
        "description": "A评→B回复→C再回复",
    },
    "like": {
        "label": "点赞互动", "blueprint": "interact_like",
        "description": "点赞视频+评论+关注",
    },
    "hot": {
        "label": "热评互动", "blueprint": "interact_hot",
        "description": "在热评下回复提升曝光",
    },
}


# ── 三级接力语料 ─────────────────────────────────────────

CHAIN_TEMPLATES = {
    "food": [
        {"first": "看着就很有食欲，周末去试试", "reply": "同意！上次去吃过一次确实不错", "second": "我也去过，他家那个招牌菜绝了"},
        {"first": "这个做法收藏了，回家就做", "reply": "做了好几次了，家人都说好吃", "second": "按着做了一次很成功，谢谢分享"},
    ],
    "travel": [
        {"first": "这个地方太美了，已加入旅行清单", "reply": "去年去过，风景确实好，值得二刷", "second": "求攻略！准备下个月去打卡"},
        {"first": "这个机位太绝了，拍得真好", "reply": "早上五点去占的位置，值得", "second": "太卷了哈哈哈，不过效果确实好"},
    ],
    "tech": [
        {"first": "分析得很透彻，学到了很多", "reply": "第三点之前完全没想到，受教了", "second": "按这个方法试了，效果很好"},
    ],
    "lifestyle": [
        {"first": "这就是我理想的生活状态", "reply": "同款生活！每天都很充实", "second": "羡慕了，我也要这样过"},
    ],
    "emotion": [
        {"first": "太真实了，完全说到心坎里", "reply": "是啊，经历过的人才懂", "second": "抱抱，都会好起来的"},
    ],
}


def _get_chain_texts(corpus: str = "") -> dict:
    """获取一组三级接力文本"""
    pool = CHAIN_TEMPLATES.get(corpus, CHAIN_TEMPLATES["food"])
    return random.choice(pool)


class InteractOrchestrator:
    """互动编排器"""

    def __init__(self, accounts: list, params: dict):
        self.accounts = accounts
        self.params = params
        self.url = params.get("url", "")
        self.strategy = params.get("strategy", "comment")
        self.direction = params.get("direction", "")
        self.corpus = params.get("corpus", "")
        self.blueprint = params.get("blueprint", "")
        self.rounds = params.get("rounds", 1)
        self.interval = params.get("interval", {"min": 300, "max": 600})
        self.dry_run = params.get("dry_run", False)

        if not self.blueprint:
            self.blueprint = STRATEGIES.get(self.strategy, STRATEGIES["comment"])["blueprint"]

        self.timeline: list[dict] = []
        self.results: list[dict] = []

    # ── 公开接口 ────────────────────────────────────────

    def plan(self) -> dict:
        """生成执行计划"""
        self.timeline = self._generate_timeline()
        return {
            "strategy": self.strategy,
            "label": STRATEGIES.get(self.strategy, {}).get("label", "未知"),
            "blueprint": self.blueprint,
            "url": self.url,
            "total_accounts": len(self.accounts),
            "timeline": self.timeline,
            "steps": len(self.timeline),
        }

    async def run(self) -> dict:
        """执行互动计划"""
        self.timeline = self._generate_timeline()
        if self.dry_run:
            return {"status": "plan", "plan": self.plan()}

        log.info(f"🚀 InteractOrchestrator | 策略={self.strategy} 账号={len(self.accounts)}")
        for step in self.timeline:
            if step.get("scheduled_at"):
                wait_sec = (step["scheduled_at"] - datetime.now()).total_seconds()
                if wait_sec > 0:
                    log.info(f"⏳ 等待 {wait_sec:.0f}s → {step['label']}")
                    await asyncio.sleep(wait_sec)

            result = await self._execute_step(step)
            self.results.append(result)

            if step != self.timeline[-1]:
                gap = random.randint(self.interval["min"], self.interval["max"])
                log.info(f"⏳ 步间间隔 {gap}s")
                await asyncio.sleep(gap)

        return {
            "status": "completed",
            "total_steps": len(self.timeline),
            "success": sum(1 for r in self.results if r.get("ok")),
            "failed": sum(1 for r in self.results if not r.get("ok")),
            "results": self.results,
        }

    # ── 时间线生成 ──────────────────────────────────────

    def _generate_timeline(self) -> list[dict]:
        if self.strategy == "chain":
            return self._gen_chain_timeline()
        elif self.strategy == "hot":
            return self._gen_hot_timeline()
        elif self.strategy == "like":
            return self._gen_like_timeline()
        else:
            return self._gen_comment_timeline()

    def _gen_comment_timeline(self) -> list[dict]:
        timeline = []
        base = datetime.now()
        for i, acct in enumerate(self.accounts):
            offset = i * random.randint(self.interval["min"], self.interval["max"])
            timeline.append({
                "step": i, "account": acct["id"],
                "platform": acct.get("platform", "douyin"),
                "machine": acct.get("machine", ""),
                "blueprint": self.blueprint,
                "label": f"评论 {acct['id']}",
                "url": self.url,
                "scheduled_at": base + timedelta(seconds=offset) if offset > 0 else None,
            })
        return timeline

    def _gen_chain_timeline(self) -> list[dict]:
        """三级接力：生成识别码 + 分配文本"""
        timeline = []
        base = datetime.now()
        codes = _alloc_codes(2)  # 分配两个识别码
        texts = _get_chain_texts(self.corpus)
        min_gap, max_gap = self.interval["min"], self.interval["max"]

        for i, acct in enumerate(self.accounts[:3]):  # 最多3个
            position = ["first", "reply", "second_reply"][i]
            offset = i * random.randint(min_gap, max_gap)

            step = {
                "step": i,
                "account": acct["id"],
                "platform": acct.get("platform", "douyin"),
                "machine": acct.get("machine", ""),
                "blueprint": "interact_chain",
                "label": f"{['一级评论','二级回复','三级再回复'][i]} {acct['id']}",
                "url": self.url,
                "chain_position": position,
                "scheduled_at": base + timedelta(seconds=offset) if offset > 0 else None,
            }

            if position == "first":
                step["comment_text"] = f"{texts['first']} {_fmt_code(codes[0])}"
                step["my_code"] = _fmt_code(codes[0])
            elif position == "reply":
                step["target_code"] = _fmt_code(codes[0])
                step["reply_text"] = f"{texts['reply']} {_fmt_code(codes[1])}"
                step["my_code"] = _fmt_code(codes[1])
            elif position == "second_reply":
                step["target_code"] = _fmt_code(codes[1])
                step["reply_text"] = texts["second"]

            timeline.append(step)

        return timeline

    def _gen_like_timeline(self) -> list[dict]:
        timeline = []
        base = datetime.now()
        for i, acct in enumerate(self.accounts):
            offset = i * random.randint(self.interval["min"] // 2, self.interval["max"] // 2)
            timeline.append({
                "step": i, "account": acct["id"],
                "platform": acct.get("platform", "douyin"),
                "machine": acct.get("machine", ""),
                "blueprint": self.blueprint,
                "label": f"点赞 {acct['id']}",
                "url": self.url,
                "scheduled_at": base + timedelta(seconds=offset) if offset > 0 else None,
            })
        return timeline

    def _gen_hot_timeline(self) -> list[dict]:
        timeline = []
        base = datetime.now()
        for i, acct in enumerate(self.accounts):
            offset = i * random.randint(self.interval["min"], self.interval["max"])
            timeline.append({
                "step": i, "account": acct["id"],
                "platform": acct.get("platform", "douyin"),
                "machine": acct.get("machine", ""),
                "blueprint": "interact_hot",
                "label": f"热评 {acct['id']}",
                "url": self.url,
                "scheduled_at": base + timedelta(seconds=offset) if offset > 0 else None,
            })
        return timeline

    # ── 单步执行 ──────────────────────────────────────────

    async def _execute_step(self, step: dict) -> dict:
        """
        执行时间线中的一步。
        
        实际 DOM 操作由你录制的原子操作完成（占位）。
        当前实现：输出要执行的命令到日志，供后续挂接。
        """
        log.info(f"▶ {step['label']}")
        log.info(f"  蓝图={step['blueprint']} url={step.get('url','')[:50]}")

        if self.strategy == "chain":
            pos = step.get("chain_position", "")
            if pos == "first":
                log.info(f"  → 发评: {step.get('comment_text','')}")
                log.info(f"    需要原子操作: post_comment_with_code(text, code)")
            elif pos in ("reply", "second_reply"):
                log.info(f"  → 搜识别码: {step.get('target_code','')}")
                log.info(f"  → 回复: {step.get('reply_text','')}")
                log.info(f"    需要原子操作: find_comment_by_code(code)")
                log.info(f"    需要原子操作: reply_comment(text)")

        return {
            "step": step["step"],
            "account": step["account"],
            "ok": True,
            "blueprint": step["blueprint"],
            "label": step["label"],
            "chain_position": step.get("chain_position", ""),
            "code": step.get("my_code", ""),
            "target_code": step.get("target_code", ""),
        }
