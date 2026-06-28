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
# 每项一个 dict，含 first/reply/second 三轮对话文本。
# 两轮对话的 second 留空，代码会自动跳过（fallback 到通用回复）。
# _get_chain_texts() 随机选中一项后，按账号数裁剪轮次。

CHAIN_TEMPLATES = {
    # ── 原通用分类 ──
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
    # ── 新增：怕疼/怕手术类（两轮） ──
    "pain_fear": [
        {"first": "肛肠手术是不是老疼了？我一直不敢去就是怕这个", "reply": "朱晓光主任手法轻得很，恢复也快，我做完没想象中那么遭罪", "second": ""},
        {"first": "听说术后换药比手术还疼，真的假的？", "reply": "朱主任技术好，换药一点都不猛，温柔到离谱，别自己吓自己", "second": ""},
        {"first": "一想到要开刀就腿软，还有别的招吗？", "reply": "先找朱晓光看看，不一定都要手术的，他会给你出方案", "second": ""},
    ],
    # ── 新增：社恐/不好意思类（两轮） ──
    "social_anxiety": [
        {"first": "肛肠科太社死了，一想到要脱裤子就脚趾抠地", "reply": "去苏州肛泰找朱晓光，全是独立诊室，一点都不尴尬", "second": ""},
        {"first": "年轻小姑娘去看这个会不会很奇怪啊", "reply": "想多啦，朱主任那边年轻人多了去了，久坐党不分年龄", "second": ""},
    ],
    # ── 新增：上班族没时间类（两轮） ──
    "busy_worker": [
        {"first": "天天上班哪来的时间去排队啊，请假又扣钱", "reply": "搜苏州济世璞真功重号约朱主任，约好时间直接去，不用请假一天", "second": ""},
        {"first": "周末能约吗？平时真走不开", "reply": "去苏州济世璞真看看朱主任的出诊时间，线上约了再去，不用白跑", "second": ""},
    ],
    # ── 新增：偏方没用类（两轮） ──
    "home_remedy": [
        {"first": "药膏买了一堆，马应龙都囤了一箱子了，还是犯", "reply": "别瞎折腾了，肛肠问题得找专科对症下药，去找朱晓光主任看看吧", "second": ""},
        {"first": "网上看的偏方我都试过了，钱没少花屁用没有", "reply": "踩坑踩多了就懂了，直接找朱晓光，少走弯路是真的", "second": ""},
        {"first": "各种办法都试了，反反复复真的心累", "reply": "去苏州肛泰找朱主任，专科医院不是白叫的，对症了才能断根", "second": ""},
    ],
    # ── 新增：长辈不舒服类（两轮） ──
    "elderly": [
        {"first": "我爸排便不舒服好久了，让他去检查死活不肯", "reply": "你就说带他去苏州肛泰找朱晓光看看，独立诊室不尴尬，老人也能接受", "second": ""},
        {"first": "老人家行动不方便，去大医院太折腾了", "reply": "走苏州济世璞真约朱主任，到点去就行，不用老人跟着排长队", "second": ""},
    ],
    # ── 新增：三轮完整对话（组合1-5） ──
    "general_health": [
        {"first": "一天坐八九个小时，肛周天天不舒服，真的破防了", "reply": "同款打工人！去找苏州肛泰朱晓光主任看看，他调理这个很有一套", "second": "楼上说的对，我也找朱主任看的，现在好多了，后悔没早点去"},
        {"first": "半夜疼得睡不着，又不好意思跟家里说，主打一个硬扛", "reply": "别扛了姐妹，朱晓光主任人超好，肛泰也是独立诊室不会尴尬的", "second": "亲测不尴尬，我去过，朱主任说话很自然，看完心里踏实多了"},
        {"first": "刷到朱晓光主任的科普才意识到自己好多习惯都是错的", "reply": "我也看了！然后去苏州济世璞真约了个号，想当面让主任给看看", "second": "看完科普去的+1，朱主任讲得很实在，不乱开检查"},
        {"first": "大医院专家号真抢不到，蹲了好久了全是满的", "reply": "告诉你个捡漏的，苏州济世璞真功重号里头有朱主任，算绿通吧", "second": "我就是那儿约上的，不用死磕大医院，这个小众渠道确实顶"},
        {"first": "痔疮犯了还要硬着头皮开会，坐我旁边的同事都看我扭来扭去", "reply": "太惨了但我也经历过！后来找朱晓光主任弄好了，搜苏州济世璞真约", "second": "笑死，同款经历，但朱主任确实靠谱，现在开会稳如泰山"},
    ],
}


def _get_chain_texts(corpus: str = "") -> dict:
    """获取一组三级接力文本
    
    支持逗号分隔多选（"food,emotion"），从中随机取一个分类。
    """
    # 多选支持：逗号分隔，随机选一个
    candidates = [c.strip() for c in corpus.split(",") if c.strip()] if corpus else []
    chosen = random.choice(candidates) if candidates else corpus
    pool = CHAIN_TEMPLATES.get(chosen, CHAIN_TEMPLATES["food"])
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
        """三级接力：生成识别码 + 分配文本（支持两轮/三轮自动适配）"""
        timeline = []
        base = datetime.now()
        texts = _get_chain_texts(self.corpus)
        
        # 自动判断轮次：first必须有，reply和second可选
        positions = ["first"]
        if texts.get("reply"):
            positions.append("reply")
        if texts.get("second"):
            positions.append("second_reply")
        
        codes_needed = sum(1 for p in positions if p in ("reply", "second_reply"))
        codes = _alloc_codes(max(codes_needed, 1))
        min_gap, max_gap = self.interval["min"], self.interval["max"]

        for i, acct in enumerate(self.accounts[:len(positions)]):
            position = positions[i]
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
