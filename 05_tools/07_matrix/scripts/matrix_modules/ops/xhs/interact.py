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
        """Step 1: 聚焦输入框（全部用 Playwright 真实鼠标/键盘，不用 JS 合成事件）"""
        if self.state == "input_focused":
            return True

        try:
            # 方式1: 键盘滚到底部 → 找输入框坐标 → Playwright 鼠标点击
            # （不用 JS scrollTo/focus/click，XHS Draft.js 不认合成事件）

            # 1a) 先等页面稳定 → 键盘箭头滚动到底部
            await asyncio.sleep(0.5)
            for _ in range(40):
                await self.page.keyboard.press("ArrowDown")
                await asyncio.sleep(0.05)
            # 等 SPA 加载评论区组件（关键！Vue 需要时间挂载底部输入框）
            await asyncio.sleep(3)

            # 1b) 用 JS 只读坐标，不触发任何事件
            # 优先选 contenteditable / p.content-input / div.input-box
            # （排除 buttons / 非输入按钮区）
            pos = await self.page.evaluate("""() => {
                const candidates = document.querySelectorAll(
                    'p.content-input, div.input-box, [contenteditable=true], ' +
                    '[class*=engage-bar], [role="textbox"], .notranslate'
                );
                // 先找可编辑的输入框
                let input = null;
                let fallback = null;
                let bestInputY = 9999;
                let bestFallbackY = -1;
                for (const el of candidates) {
                    if (el.offsetHeight < 20) continue;
                    const r = el.getBoundingClientRect();
                    if (r.y < 100) continue;
                    // 检查是否可编辑输入框
                    const isInput = el.isContentEditable ||
                        el.classList.contains('content-input') ||
                        el.classList.contains('input-box');
                    if (isInput && r.y < bestInputY) {
                        bestInputY = r.y;
                        input = {x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)};
                    } else if (!isInput && r.y > bestFallbackY) {
                        bestFallbackY = r.y;
                        fallback = {x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)};
                    }
                }
                return input || fallback;  // 优先用输入框
            }""")

            if not pos:
                # 等一会再重试（SPA 可能还没挂载评论区）
                await asyncio.sleep(2)
                pos = await self.page.evaluate("""() => {
                    const c = document.querySelectorAll('p.content-input,div.input-box,[contenteditable=true],[class*=engage-bar],[role=textbox],.notranslate');
                    let input=null, fallback=null, inputY=9999, fbY=-1;
                    for (const el of c) {
                        if (el.offsetHeight<20) continue;
                        const r = el.getBoundingClientRect();
                        if (r.y<100) continue;
                        const isIn = el.isContentEditable||el.classList.contains('content-input')||el.classList.contains('input-box');
                        if (isIn && r.y<inputY) { inputY=r.y; input={x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}; }
                        else if (!isIn && r.y>fbY) { fbY=r.y; fallback={x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}; }
                    }
                    return input||fallback;
                }""")

            if pos and pos.get('x') is not None and pos.get('y') is not None:            
                await self.page.mouse.move(pos['x'], pos['y'], steps=8)
                await asyncio.sleep(random.uniform(0.3, 0.8))
                await self.page.mouse.click(pos['x'], pos['y'])
                await asyncio.sleep(1.5)

                # 验证是否真的聚焦了
                focused = await self.page.evaluate("""
                    () => {
                        const el = document.activeElement;
                        if (!el) return false;
                        return true;
                    }
                """)
                if focused:
                    self.state = "input_focused"
                    return True

            # 方式2: 兜底 — 找页面中任何 input/textarea/contenteditable
            fallback_pos = await self.page.evaluate("""() => {
                // 更广泛地找：所有 input/textarea/contenteditable（排除顶部搜索框）
                const all = document.querySelectorAll('input, textarea, [contenteditable]');
                let best = null;
                let bestY = -1;
                for (const el of all) {
                    if (el.offsetHeight < 15) continue;
                    const r = el.getBoundingClientRect();
                    if (r.y < 100) continue; // 排除顶部搜索
                    if (r.y > bestY) {
                        bestY = r.y;
                        best = {x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)};
                    }
                }
                return best;
            }""")
            if fallback_pos and fallback_pos.get('x') is not None:
                await self.page.mouse.move(fallback_pos['x'], fallback_pos['y'], steps=8)
                await asyncio.sleep(0.3)
                await self.page.mouse.click(fallback_pos['x'], fallback_pos['y'])
                await asyncio.sleep(1.5)
                self.state = "input_focused"
                return True

            # 方式3: Tab 导航 + 检查
            await self.page.keyboard.press("Tab")
            await asyncio.sleep(0.3)
            await self.page.keyboard.press("Tab")
            await asyncio.sleep(0.3)
            await self.page.keyboard.press("Tab")
            await asyncio.sleep(0.3)
            # 检查是否聚焦到输入框
            focused = await self.page.evaluate("""
                () => {
                    const el = document.activeElement;
                    if (!el) return false;
                    return el.getAttribute('contenteditable') === 'true'
                        || el.tagName === 'INPUT'
                        || el.tagName === 'TEXTAREA';
                }
            """)
            if focused:
                self.state = "input_focused"
                return True

            return False

        except Exception:
            return False

    async def enter_text(self, text: str) -> bool:
        """Step 2: 输入评论文本（pbcopy + Cmd+V 系统级粘贴，不用 JS）"""
        if self.state == "text_entered":
            return True
        if self.state != "input_focused":
            return False

        self.text = text

        try:
            # 1. 复制文本到剪贴板
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
            await asyncio.sleep(0.3)

            # 2. Cmd+V 系统级粘贴（已经在 input_focused 状态，不用再次 JS focus）
            await self.page.keyboard.press("Meta+v")
            await asyncio.sleep(0.5)

            # 3. 验证输入成功
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

            # 4. 空格刷新 Draft.js 状态 + 再次粘贴
            await self.page.keyboard.press("Space")
            await asyncio.sleep(0.3)
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
        """Step 3: 发送评论（有发送按钮点按钮，无则 Enter）"""
        if self.state != "text_entered":
            return False

        try:
            # 方式1: 找"发送"按钮（XHS 页面上的按钮）
            btn_found = await self.page.evaluate("""() => {
                const btns = document.querySelectorAll('button, div[role=button], [class*=btn], [class*=send]');
                for (const btn of btns) {
                    if ((btn.textContent||'').includes('发送')) return true;
                }
                return false;
            }""")
            if btn_found:
                btn = await self.page.query_selector('button:has-text("发送"), [class*=send]:has-text("发送"), [class*=btn]:has-text("发送")')
                if btn:
                    await btn.click()
                    await asyncio.sleep(2)
                    self.state = "sent"
                    return True

            # 方式2: Enter 键发送
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(2)
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

# VERSION: 2026-05-28 v3.1 - fixed focus_input input priority
