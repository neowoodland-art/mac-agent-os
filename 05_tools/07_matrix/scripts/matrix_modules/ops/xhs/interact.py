"""
小红书 — 交互类操作（点赞、收藏、关注、评论）
基于 2026-05-20/2026-05-27 DOM 分析 + Playwright mouse API + L 形鼠标路径

v2 更新 (2026-05-27):
- 点赞/收藏改用 Playwright page.mouse API（非 JS dispatchEvent / element.click()）
- 鼠标移动采用 L 形路径（先上移→再水平→再下移），避开评论区输入框
- 使用 get_bottom_bar_buttons_js() 获取精确按钮位置
- 操作前后锚点验证

核心设计:
- 每个操作独立 try/except，失败不崩流程
- 操作后验证状态变化（防假点击）
- 评论状态机: closed → panel_open → input_focused → text_entered → sent
"""
import json
import random
import asyncio
import subprocess
from typing import Optional

from .selectors import (
    LIKE_BUTTON, COLLECT_BUTTON, FOLLOW_BUTTON,
    COMMENT_ENTRY, COMMENT_INPUT, COMMENT_SEND,
    ANCHORS, get_bottom_bar_buttons_js
)


# ════════════════════════════════════════════════════════════
# 辅助: L 形鼠标路径
# ════════════════════════════════════════════════════════════

async def mouse_move_l_shape(page, target_x: int, target_y: int,
                              safe_y: int = 100, steps: int = 8):
    """L 形鼠标路径 — 避开评论区输入框

    三段式: 当前位置 → (cx, safe_y) → (target_x, safe_y) → (target_x, target_y)

    Args:
        safe_y: 安全 Y 坐标（输入框上方区域）
        steps: 每段的 steps 数（实际三段总和）
    """
    cx, cy = await page.evaluate("""() => {
        // Playwright 不暴露鼠标位置，从视口中心估算
        return {x: Math.round(window.innerWidth / 2), y: Math.round(window.innerHeight / 2)};
    }""")

    # Segment 1: 垂直上移到安全区
    await page.mouse.move(cx, safe_y, steps=max(3, steps // 3))
    await asyncio.sleep(random.uniform(0.08, 0.15))

    # Segment 2: 水平移动到目标 X
    await page.mouse.move(target_x, safe_y, steps=max(3, steps // 3))
    await asyncio.sleep(random.uniform(0.08, 0.15))

    # Segment 3: 垂直下移到目标
    await page.mouse.move(target_x, target_y, steps=max(3, steps // 3))
    await asyncio.sleep(random.uniform(0.15, 0.3))


# ════════════════════════════════════════════════════════════
# 点赞 (Playwright page.mouse API)
# ════════════════════════════════════════════════════════════

async def like(page) -> bool:
    """
    点赞当前笔记 — Playwright page.mouse API（L 形路径）

    Returns:
        是否成功
    """
    try:
        # 1. 获取底部栏按钮位置
        btns = await page.evaluate(get_bottom_bar_buttons_js())
        like_btn = btns.get('like') if btns else None

        if not like_btn:
            return False

        # 2. 如果已点赞，跳过
        if like_btn.get('isActive'):
            return True

        # 3. 确保按钮可见
        if not like_btn.get('visible'):
            await page.evaluate("""() => {
                const btns = document.querySelectorAll('span.like-wrapper, [class*="like-wrapper"]');
                for (const btn of btns) {
                    const r = btn.getBoundingClientRect();
                    if (r.left > window.innerWidth * 0.3) {
                        btn.scrollIntoView({behavior: 'instant', block: 'center'});
                        break;
                    }
                }
            }""")
            await asyncio.sleep(1)
            # 重新获取位置
            btns = await page.evaluate(get_bottom_bar_buttons_js())
            like_btn = btns.get('like') if btns else None
            if not like_btn:
                return False

        # 4. L 形路径移动 + Playwright mouse.click
        await mouse_move_l_shape(page, like_btn['x'], like_btn['y'], safe_y=100)
        await asyncio.sleep(random.uniform(0.2, 0.4))

        await page.mouse.click(like_btn['x'], like_btn['y'])
        await asyncio.sleep(random.uniform(1.5, 2.5))

        # 5. 验证点赞状态
        btns_after = await page.evaluate(get_bottom_bar_buttons_js())
        if btns_after and btns_after.get('like', {}).get('isActive'):
            return True

        # 重试一次
        like_btn2 = btns_after.get('like') if btns_after else like_btn
        if like_btn2:
            await mouse_move_l_shape(page, like_btn2['x'], like_btn2['y'], safe_y=100)
            await asyncio.sleep(0.2)
            await page.mouse.click(like_btn2['x'], like_btn2['y'])
            await asyncio.sleep(2)

            btns_after2 = await page.evaluate(get_bottom_bar_buttons_js())
            if btns_after2 and btns_after2.get('like', {}).get('isActive'):
                return True

        return False
    except Exception:
        return False


# ════════════════════════════════════════════════════════════
# 收藏
# ════════════════════════════════════════════════════════════

async def collect(page) -> bool:
    """
    收藏当前笔记 — Playwright page.mouse API（L 形路径）

    Returns:
        是否成功
    """
    try:
        # 1. 获取底部栏按钮位置
        btns = await page.evaluate(get_bottom_bar_buttons_js())
        collect_btn = btns.get('collect') if btns else None

        if not collect_btn:
            return False

        # 2. 如果已收藏，跳过
        if collect_btn.get('isActive'):
            return True

        # 3. 确保按钮可见
        if not collect_btn.get('visible'):
            await page.evaluate("""() => {
                const btns = document.querySelectorAll('span.collect-wrapper, [class*="collect-wrapper"]');
                for (const btn of btns) {
                    const r = btn.getBoundingClientRect();
                    if (r.left > window.innerWidth * 0.3) {
                        btn.scrollIntoView({behavior: 'instant', block: 'center'});
                        break;
                    }
                }
            }""")
            await asyncio.sleep(1)
            btns = await page.evaluate(get_bottom_bar_buttons_js())
            collect_btn = btns.get('collect') if btns else None
            if not collect_btn:
                return False

        # 4. L 形路径移动 + Playwright mouse.click
        await mouse_move_l_shape(page, collect_btn['x'], collect_btn['y'], safe_y=100)
        await asyncio.sleep(random.uniform(0.2, 0.4))

        await page.mouse.click(collect_btn['x'], collect_btn['y'])
        await asyncio.sleep(random.uniform(1.5, 2.5))

        # 5. 验证收藏状态
        btns_after = await page.evaluate(get_bottom_bar_buttons_js())
        if btns_after and btns_after.get('collect', {}).get('isActive'):
            return True

        # 重试一次
        collect_btn2 = btns_after.get('collect') if btns_after else collect_btn
        if collect_btn2:
            await mouse_move_l_shape(page, collect_btn2['x'], collect_btn2['y'], safe_y=100)
            await asyncio.sleep(0.2)
            await page.mouse.click(collect_btn2['x'], collect_btn2['y'])
            await asyncio.sleep(2)

            btns_after2 = await page.evaluate(get_bottom_bar_buttons_js())
            if btns_after2 and btns_after2.get('collect', {}).get('isActive'):
                return True

        return False
    except Exception:
        return False


# ════════════════════════════════════════════════════════════
# 关注
# ════════════════════════════════════════════════════════════

async def follow(page) -> bool:
    """关注当前笔记作者（含状态验证）"""
    try:
        # 检查是否已关注
        was_followed = await page.evaluate("""
            () => {
                const btn = document.querySelector('.follow-btn, [class*=follow-btn], .interaction-follow');
                if (!btn) return 'not_found';
                const txt = btn.textContent || '';
                return txt.includes('已关注') ? 'followed' : 'not_followed';
            }
        """)
        if was_followed == 'followed':
            return True

        btn = await page.query_selector(FOLLOW_BUTTON)
        if btn:
            await btn.click()
            await asyncio.sleep(0.5)
            # 验证关注成功
            now_followed = await page.evaluate("""
                () => {
                    const btn = document.querySelector('.follow-btn, [class*=follow-btn], .interaction-follow');
                    if (!btn) return false;
                    const txt = btn.textContent || '';
                    return txt.includes('已关注');
                }
            """)
            return bool(now_followed)

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
    """小红书评论状态机（v2: XHS 输入框直接可见于详情页底部，无需打开面板）

    状态迁移:
        closed → input_focused → text_entered → sent → verified
    """

    STATES = ["closed", "input_focused", "text_entered", "sent", "verified"]

    def __init__(self, page):
        self.page = page
        self.state = "closed"
        self.text = ""

    async def focus_input(self) -> bool:
        """Step 1: 聚焦输入框（XHS 输入框在详情页底部直接可见）"""
        if self.state == "input_focused":
            return True

        try:
            # 方式1: 找评论区底部输入框（优先用 p.content-input / div.input-box）
            selectors = [
                "p.content-input",           # 实际 typing 区域
                "div.input-box",             # 输入框容器
                "[class*=engage-bar]",       # 底部互动栏
                "[contenteditable=true]",    # 任何可编辑元素
            ]
            for sel in selectors:
                el = await self.page.query_selector(sel)
                if el:
                    # 滚动到可视区域
                    try:
                        await el.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                    except Exception:
                        pass
                    await el.click()
                    await asyncio.sleep(1)
                    self.state = "input_focused"
                    return True

            # 方式2: JS 暴力聚焦
            await self.page.evaluate("""
                () => {
                    const inp = document.querySelector('p.content-input, div.input-box, [contenteditable=true]');
                    if (inp) { inp.focus(); inp.click(); }
                }
            """)
            await asyncio.sleep(1)
            self.state = "input_focused"
            return True

        except Exception:
            return False

    async def enter_text(self, text: str) -> bool:
        """Step 2: 输入评论文本（pbcopy + Cmd+V 系统级粘贴）"""
        if self.state == "text_entered":
            return True
        if self.state != "input_focused":
            return False

        self.text = text

        try:
            # 1. 复制文本到剪贴板
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
            await asyncio.sleep(0.3)

            # 2. 确保输入框聚焦（JS 兜底）
            await self.page.evaluate("""
                () => {
                    const inp = document.querySelector('p.content-input, [contenteditable=true]');
                    if (inp) inp.focus();
                }
            """)
            await asyncio.sleep(0.3)

            # 3. 系统级粘贴 (Cmd+V)
            await self.page.keyboard.press("Meta+v")
            await asyncio.sleep(0.5)

            # 4. 验证输入成功
            needle = json.dumps(text[:10])
            has_text = await self.page.evaluate(f"""
                () => {{
                    const inp = document.querySelector('p.content-input, [contenteditable=true], div.input-box');
                    if (!inp) return false;
                    const val = inp.textContent || inp.innerText || '';
                    return val.includes({needle});
                }}
            """)

            if has_text:
                self.state = "text_entered"
                return True

            # 5. 空格刷新 Draft.js 状态 + 再次粘贴
            await self.page.keyboard.press("Space")
            await asyncio.sleep(0.2)
            await self.page.evaluate("""
                () => {
                    const inp = document.querySelector('p.content-input, [contenteditable=true]');
                    if (inp) inp.focus();
                }
            """)
            await asyncio.sleep(0.2)
            await self.page.keyboard.press("Meta+v")
            await asyncio.sleep(0.5)

            has_text2 = await self.page.evaluate(f"""
                () => {{
                    const inp = document.querySelector('p.content-input, [contenteditable=true], div.input-box');
                    if (!inp) return false;
                    const val = inp.textContent || inp.innerText || '';
                    return val.includes({needle});
                }}
            """)
            if has_text2:
                self.state = "text_entered"
                return True

            return False

        except Exception:
            return False

    async def send(self) -> bool:
        """Step 3: 发送评论"""
        if self.state != "text_entered":
            return False

        try:
            # 方式1: Enter 键发送
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(1.5)
            self.state = "sent"
            return True

        except Exception:
            return False

    async def verify(self) -> bool:
        """Step 4: 验证评论是否发送成功"""
        if self.state != "sent":
            return False

        try:
            # 检查输入框是否清空（发送后通常清空）
            needle = json.dumps(self.text[:8])
            inp_clear = await self.page.evaluate(f"""
                () => {{
                    const inp = document.querySelector('p.content-input, [contenteditable=true], div.input-box');
                    if (!inp) return false;
                    const val = inp.textContent || inp.innerText || '';
                    return !val.includes({needle}) || val.trim().length < 3;
                }}
            """)

            if inp_clear:
                self.state = "verified"
                return True

            # 兜底：等待 + 再检查一次
            await asyncio.sleep(2)
            inp_clear2 = await self.page.evaluate(f"""
                () => {{
                    const inp = document.querySelector('p.content-input, [contenteditable=true], div.input-box');
                    if (!inp) return false;
                    return (inp.textContent || inp.innerText || '').trim().length < 3;
                }}
            """)
            if inp_clear2:
                self.state = "verified"
                return True

            return False

        except Exception:
            return False


async def comment(page, text: str) -> dict:
    """
    评论当前笔记（完整状态机 v2 - XHS 版）

    区别抖音: XHS 的评论输入框在详情页底部直接显示，
    无需先打开评论区面板。

    Args:
        text: 评论内容

    Returns:
        {"success": bool, "state": str, "error": str}
    """
    sm = CommentStateMachine(page)
    result = {"success": False, "state": "closed", "error": ""}

    try:
        # Step 1: 聚焦输入框（XHS 版直接聚��，无需打开面板）
        if not await sm.focus_input():
            result["error"] = "无法聚焦输入框"
            return result
        result["state"] = sm.state

        # Step 2: 输入文本
        if not await sm.enter_text(text):
            result["error"] = "无法输入文本"
            return result
        result["state"] = sm.state

        # Step 3: 发送
        if not await sm.send():
            result["error"] = "发送失败"
            return result
        result["state"] = sm.state

        # Step 4: 验证
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

    # 点赞: 3 中 1 (~33%)
    if random.random() < 0.33:
        results["like"] = await like(page)
        await asyncio.sleep(random.uniform(0.5, 1.5))

    # 收藏: 5 中 1 (20%)
    if random.random() < 0.20:
        results["collect"] = await collect(page)
        await asyncio.sleep(random.uniform(0.5, 1.5))

    # 关注: 10 中 1 (10%)
    if random.random() < 0.10:
        results["follow"] = await follow(page)
        await asyncio.sleep(random.uniform(0.5, 1.5))

    return results
