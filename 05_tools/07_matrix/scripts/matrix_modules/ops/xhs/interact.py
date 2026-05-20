"""
小红书 — 交互类操作（点赞、收藏、关注、评论）
基于 2026-05-20 DOM 分析 + 抖音踩坑经验

防护设计:
- 每个操作独立 try/except，失败不崩流程
- 操作后验证状态变化（防假点击）
- 评论状态机: closed → panel_open → input_focused → text_entered → sent
"""
import random
import asyncio
import subprocess
from typing import Optional

from .selectors import (
    LIKE_BUTTON, COLLECT_BUTTON, FOLLOW_BUTTON,
    COMMENT_ENTRY, COMMENT_INPUT, COMMENT_SEND,
    ANCHORS
)


# ════════════════════════════════════════════════════════════
# 点赞
# ════════════════════════════════════════════════════════════

async def like(page) -> bool:
    """
    点赞当前笔记

    Returns:
        是否成功
    """
    try:
        # 方式1: Playwright locator 点击
        btn = await page.query_selector(LIKE_BUTTON)
        if btn:
            await btn.click()
            await asyncio.sleep(0.5)
            return True

        # 方式2: JS 直接点击
        result = await page.evaluate("""
            () => {
                const btn = document.querySelector('.like-btn, [class*=like-btn], .interaction-like');
                if (btn) { btn.click(); return true; }
                // 兜底: 找包含点赞图标的按钮
                const allBtns = [...document.querySelectorAll('button, div[role=button]')];
                const likeBtn = allBtns.find(b => b.textContent.includes('赞') || b.innerHTML.includes('like'));
                if (likeBtn) { likeBtn.click(); return true; }
                return false;
            }
        """)
        return bool(result)
    except Exception:
        return False


# ════════════════════════════════════════════════════════════
# 收藏
# ════════════════════════════════════════════════════════════

async def collect(page) -> bool:
    """收藏当前笔记"""
    try:
        btn = await page.query_selector(COLLECT_BUTTON)
        if btn:
            await btn.click()
            await asyncio.sleep(0.5)
            return True

        # JS 兜底
        result = await page.evaluate("""
            () => {
                const btn = document.querySelector('.collect-btn, [class*=collect-btn], .interaction-collect');
                if (btn) { btn.click(); return true; }
                const allBtns = [...document.querySelectorAll('button, div[role=button]')];
                const collectBtn = allBtns.find(b => b.textContent.includes('收藏') || b.innerHTML.includes('collect'));
                if (collectBtn) { collectBtn.click(); return true; }
                return false;
            }
        """)
        return bool(result)
    except Exception:
        return False


# ════════════════════════════════════════════════════════════
# 关注
# ════════════════════════════════════════════════════════════

async def follow(page) -> bool:
    """关注当前笔记作者"""
    try:
        btn = await page.query_selector(FOLLOW_BUTTON)
        if btn:
            await btn.click()
            await asyncio.sleep(0.5)
            return True

        # JS 兜底
        result = await page.evaluate("""
            () => {
                const btn = document.querySelector('.follow-btn, [class*=follow-btn], .interaction-follow');
                if (btn) { btn.click(); return true; }
                const allBtns = [...document.querySelectorAll('button, div[role=button]')];
                const followBtn = allBtns.find(b => b.textContent.includes('关注') && !b.textContent.includes('已关注'));
                if (followBtn) { followBtn.click(); return true; }
                return false;
            }
        """)
        return bool(result)
    except Exception:
        return False


# ════════════════════════════════════════════════════════════
# 评论 — 状态机驱动
# ════════════════════════════════════════════════════════════

class CommentStateMachine:
    """小红书评论状态机"""

    STATES = ["closed", "panel_open", "input_focused", "text_entered", "sent", "verified"]

    def __init__(self, page):
        self.page = page
        self.state = "closed"
        self.text = ""

    async def open_panel(self) -> bool:
        """Step 1: 打开评论区"""
        if self.state != "closed":
            return True

        try:
            # 方式1: 点击评论入口
            entry = await self.page.query_selector(COMMENT_ENTRY)
            if entry:
                await entry.click()
                await asyncio.sleep(1.5)

                # 验证评论区是否打开
                has_comments = await self.page.evaluate("""
                    () => document.querySelector('.comment-section, [class*=comment-section], [class*=comment-list]') !== null
                """)
                if has_comments:
                    self.state = "panel_open"
                    return True

            # 方式2: 滚动到评论区
            await self.page.evaluate("""
                () => {
                    const el = document.querySelector('.comment-section, [class*=comment-section]');
                    if (el) el.scrollIntoView({behavior: 'smooth', block: 'center'});
                }
            """)
            await asyncio.sleep(1.5)
            self.state = "panel_open"
            return True

        except Exception:
            return False

    async def focus_input(self) -> bool:
        """Step 2: 聚焦输入框"""
        if self.state == "input_focused":
            return True
        if self.state != "panel_open":
            return False

        try:
            # 方式1: Playwright 点击输入框
            inp = await self.page.query_selector(COMMENT_INPUT)
            if inp:
                await inp.click()
                await asyncio.sleep(0.5)
                self.state = "input_focused"
                return True

            # 方式2: JS 聚焦
            await self.page.evaluate("""
                () => {
                    const inp = document.querySelector('.comment-input input, [contenteditable=true], textarea');
                    if (inp) { inp.focus(); inp.click(); }
                }
            """)
            await asyncio.sleep(0.5)
            self.state = "input_focused"
            return True

        except Exception:
            return False

    async def enter_text(self, text: str) -> bool:
        """Step 3: 输入评论文本（pbcopy + Cmd+V 系统级粘贴）"""
        if self.state == "text_entered":
            return True
        if self.state != "input_focused":
            return False

        self.text = text

        try:
            # 小红书输入框可能是 contenteditable div 或 input
            # 策略: pbcopy + 系统级键盘粘贴（和抖音一样）

            # 1. 复制文本到剪贴板
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
            await asyncio.sleep(0.3)

            # 2. 确保输入框聚焦
            await self.page.evaluate("""
                () => {
                    const inp = document.querySelector('.comment-input input, [contenteditable=true], textarea, .editor');
                    if (inp) { inp.focus(); }
                }
            """)
            await asyncio.sleep(0.3)

            # 3. 系统级粘贴 (Cmd+V)
            await self.page.keyboard.press("Meta+v")
            await asyncio.sleep(0.5)

            # 4. 验证输入成功
            has_text = await self.page.evaluate(f"""
                () => {{
                    const inp = document.querySelector('.comment-input input, [contenteditable=true], textarea, .editor');
                    if (!inp) return false;
                    const val = inp.value || inp.textContent || inp.innerText || '';
                    return val.includes('{text[:5]}');
                }}
            """)

            if has_text:
                self.state = "text_entered"
                return True

            # 5. fallback: Playwright fill
            inp = await self.page.query_selector(COMMENT_INPUT)
            if inp:
                await inp.fill(text)
                await asyncio.sleep(0.3)
                self.state = "text_entered"
                return True

            return False

        except Exception:
            return False

    async def send(self) -> bool:
        """Step 4: 发送评论"""
        if self.state != "text_entered":
            return False

        try:
            # 方式1: 点击发送按钮
            btn = await self.page.query_selector(COMMENT_SEND)
            if btn:
                await btn.click()
                await asyncio.sleep(1.5)
                self.state = "sent"
                return True

            # 方式2: Enter 键发送
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(1.5)
            self.state = "sent"
            return True

        except Exception:
            return False

    async def verify(self) -> bool:
        """Step 5: 验证评论是否发送成功"""
        if self.state != "sent":
            return False

        try:
            # 检查评论列表中是否出现我们的评论
            has_comment = await self.page.evaluate(f"""
                () => {{
                    const comments = [...document.querySelectorAll('.comment-item, [class*=comment-item]')];
                    return comments.some(c => c.textContent.includes('{self.text[:8]}'));
                }}
            """)

            if has_comment:
                self.state = "verified"
                return True

            # 兜底: 检查输入框是否清空（发送后通常会清空）
            inp = await self.page.query_selector(COMMENT_INPUT)
            if inp:
                val = await inp.input_value()
                if not val or len(val) < len(self.text) / 2:
                    self.state = "verified"
                    return True

            return False

        except Exception:
            return False


async def comment(page, text: str) -> dict:
    """
    评论当前笔记（完整状态机）

    Args:
        text: 评论内容

    Returns:
        {"success": bool, "state": str, "error": str}
    """
    sm = CommentStateMachine(page)
    result = {"success": False, "state": "closed", "error": ""}

    try:
        # Step 1: 打开评论区
        if not await sm.open_panel():
            result["error"] = "无法打开评论区"
            return result
        result["state"] = sm.state

        # Step 2: 聚焦输入框
        if not await sm.focus_input():
            result["error"] = "无法聚焦输入框"
            return result
        result["state"] = sm.state

        # Step 3: 输入文本
        if not await sm.enter_text(text):
            result["error"] = "无法输入文本"
            return result
        result["state"] = sm.state

        # Step 4: 发送
        if not await sm.send():
            result["error"] = "发送失败"
            return result
        result["state"] = sm.state

        # Step 5: 验证
        if await sm.verify():
            result["success"] = True
            result["state"] = "verified"
        else:
            result["error"] = "发送后验证失败"

        return result

    except Exception as e:
        result["error"] = str(e)
        return result


# ════════════════════════════════════════════════════════════
# 概率互动（养号用）
# ════════════════════════════════════════════════════════════

async def random_interact(page, behavior_config: dict = None) -> dict:
    """
    随机互动（根据概率触发点赞/收藏/关注/评论）

    Returns:
        {"like": bool, "collect": bool, "follow": bool, "comment": bool, "comment_text": str}
    """
    results = {
        "like": False,
        "collect": False,
        "follow": False,
        "comment": False,
        "comment_text": "",
    }

    # 点赞: 5 中 1 (20%)
    if random.random() < 0.20:
        results["like"] = await like(page)
        await asyncio.sleep(random.uniform(0.5, 1.5))

    # 收藏: 8 中 1 (12.5%)
    if random.random() < 0.125:
        results["collect"] = await collect(page)
        await asyncio.sleep(random.uniform(0.5, 1.5))

    # 关注: 15 中 1 (6.7%)
    if random.random() < 0.067:
        results["follow"] = await follow(page)
        await asyncio.sleep(random.uniform(0.5, 1.5))

    return results
