"""
小红书 — 浏览类操作
基于 2026-05-20 DOM 分析 + 2026-05-27 Playwright mouse API 验证

v2 更新 (2026-05-27):
- click_note_card 默认使用 Playwright page.mouse API（真人鼠标模拟）
- 单次单击（避免双击触发图片查看器）
- 点击后 is_note_detail_mode 锚点验证
- 使用 section.note-item 定位（避免 a 标签 zero-bounding-rect bug）

核心差异（vs 抖音）:
- 双列瀑布流 → 需要定位具体卡片
- 笔记详情页 → 图文为主，可能有视频
- 搜索发现 → 顶部搜索框
"""
import random
import asyncio
from typing import List, Optional

from .selectors import (
    NOTE_CARD, NOTE_CARD_COVER, NOTE_CARD_IMG,
    SEARCH_INPUT, SEARCH_BUTTON,
    ANCHORS, get_note_links_js, get_note_cards_js, dismiss_login_modal_js
)


# ════════════════════════════════════════════════════════════
# 首页浏览
# ════════════════════════════════════════════════════════════

async def goto_home(page):
    """回到小红书首页/发现页（锚点等待 + 超时兜底）"""
    try:
        await page.goto("https://www.xiaohongshu.com/explore", timeout=20000, wait_until="commit")
        # 锚点等待: 等 #app 出现（SPA 水合）
        try:
            await page.wait_for_selector("#app", timeout=8000)
        except Exception:
            pass
        await asyncio.sleep(2)  # 额外等待渲染稳定
    except Exception:
        # 兜底: 直接导航，不抛异常
        await page.goto("https://www.xiaohongshu.com/explore", timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(5)
    return "home"


async def dismiss_login_modal(page):
    """关闭登录弹窗（未登录状态下浏览需要）"""
    try:
        result = await page.evaluate(dismiss_login_modal_js())
        await asyncio.sleep(0.5)
        return result
    except Exception:
        return None


async def get_note_cards(page) -> List[dict]:
    """获取当前页面所有笔记卡片信息"""
    try:
        cards = await page.evaluate(get_note_cards_js())
        return [c for c in cards if c.get("href")]
    except Exception:
        return []


async def click_note_card(page, index: int = None, use_mouse_api: bool = True) -> Optional[str]:
    """
    点击笔记卡片进入详情页

    v2 变更 (2026-05-27):
    - 默认使用 Playwright page.mouse API（真人鼠标模拟）
    - 单次单击（非双击，XHS 双击会触发图片查看器）
    - 点击后锚点验证（is_note_detail_mode）
    - 使用 section.note-item 定位（避免 a 标签 zero-bounding-rect bug）

    Args:
        index: 卡片索引（0-based），None 时随机选择
        use_mouse_api: True 用 page.mouse API，False 用 element.click()

    Returns:
        笔记 URL，失败返回 None
    """
    from .selectors import is_note_detail_mode_js

    # 优先用 section.note-item 获取 bounding rect
    cards = await page.evaluate("""() => {
        const sections = [...document.querySelectorAll('section.note-item')];
        return sections.map((s, i) => {
            const r = s.getBoundingClientRect();
            return {
                index: i,
                href: s.querySelector('a')?.href || '',
                rect: {x: r.x, y: r.y, w: r.width, h: r.height},
            };
        }).filter(c => c.rect.w >= 10 && c.rect.h >= 10);
    }""")

    if not cards:
        return None

    # 随机选择
    if index is None:
        max_idx = min(3, len(cards) - 1)
        index = random.randint(0, max_idx)
    if index >= len(cards):
        index = random.randint(0, len(cards) - 1)

    card = cards[index]
    href = card.get("href")
    if not href:
        return None

    if use_mouse_api:
        # ── Playwright page.mouse API（单次单击） ──
        try:
            # scrollIntoView
            await page.evaluate(f"""
                () => {{
                    const s = document.querySelectorAll('section.note-item')[{index}];
                    if (s) s.scrollIntoView({{block: 'center'}});
                }}
            """)
            await asyncio.sleep(0.5)

            # 重新获取位置
            pos = await page.evaluate(f"""
                () => {{
                    const s = document.querySelectorAll('section.note-item')[{index}];
                    if (!s) return null;
                    const r = s.getBoundingClientRect();
                    return {{x: r.x, y: r.y, w: r.width, h: r.height}};
                }}
            """)
            if not pos or pos['w'] < 10:
                return None

            cx = pos['x'] + pos['w'] / 2
            cy = pos['y'] + pos['h'] / 2

            await page.mouse.move(cx, cy, steps=random.randint(5, 12))
            await asyncio.sleep(random.uniform(0.3, 0.8))

            # ⚡ 单次单击（XHS 双击触发图片查看器）
            await page.mouse.click(cx, cy)
            await asyncio.sleep(3)

            # 锚点验证
            anchor = await page.evaluate(is_note_detail_mode_js())
            if anchor.get('is_detail'):
                return page.url

            # 锚点失败 — fallback 直接导航
            if href:
                await page.goto(href, timeout=15000, wait_until="commit")
                await asyncio.sleep(2)
                anchor = await page.evaluate(is_note_detail_mode_js())
                if anchor.get('is_detail'):
                    return page.url
            return None

        except Exception:
            # fallback
            if href:
                try:
                    await page.goto(href, timeout=15000, wait_until="commit")
                    await asyncio.sleep(2)
                    return page.url
                except Exception:
                    pass
            return None
    else:
        # ── 传统 element.click() 方式 ──
        try:
            cards_els = await page.query_selector_all(NOTE_CARD)
            if index < len(cards_els):
                await cards_els[index].click()
                await asyncio.sleep(2)
                return page.url
        except Exception:
            pass

        # fallback: 直接导航
        try:
            await page.goto(href, timeout=15000, wait_until="commit")
            await asyncio.sleep(2)
            return page.url
        except Exception:
            return None


async def scroll_feed(page, distance: int = None):
    """
    滚动瀑布流（单方式: 鼠标滚轮，避免双重滚动）

    Args:
        distance: 滚动距离(px)，None 时随机
    """
    dist = distance or random.randint(300, 800)

    # 鼠标滚轮（拟人）
    try:
        await page.mouse.wheel(0, dist)
        await asyncio.sleep(random.uniform(0.5, 1.5))
    except Exception:
        # fallback: JS 滚动
        await page.evaluate(f"window.scrollBy(0, {dist})")
        await asyncio.sleep(random.uniform(0.5, 1.5))

    return dist


async def scroll_feed_human(page, screens: int = 2):
    """
    拟人化滚动：分多次小滚动，中间随机停顿

    Args:
        screens: 滚动几屏
    """
    for _ in range(screens):
        # 每次滚动一小段
        dist = random.randint(200, 500)
        await scroll_feed(page, dist)

        # 随机停顿（模拟阅读）
        if random.random() < 0.4:
            pause = random.uniform(1.0, 3.0)
            await asyncio.sleep(pause)

    return screens


# ════════════════════════════════════════════════════════════
# 笔记详情页浏览
# ════════════════════════════════════════════════════════════

async def browse_note_detail(page, duration: float = None):
    """
    在笔记详情页浏览内容（图文/视频自适应）

    Args:
        duration: 浏览时长(秒)，None 时随机 4~12 秒

    Returns:
        实际浏览秒数
    """
    watch = duration or random.uniform(4, 12)

    # 检测是否是视频笔记
    has_video = await page.evaluate("""
        () => {
            const v = document.querySelector('video');
            if (!v) return false;
            const rect = v.getBoundingClientRect();
            return rect.width > 100 && rect.height > 100;
        }
    """)

    if has_video:
        # 视频笔记：看视频，不滚动
        # 等待视频加载
        await asyncio.sleep(random.uniform(1, 2))
        return watch
    else:
        # 图文笔记：缓慢滚动模拟阅读
        steps = int(watch / 2)
        for _ in range(steps):
            await page.evaluate(f"window.scrollBy(0, {random.randint(50, 150)})")
            await asyncio.sleep(random.uniform(1.0, 2.5))
        return watch


async def go_back_to_home(page):
    """从详情页返回首页"""
    try:
        # 方式1: 浏览器返回
        await page.go_back(timeout=10000, wait_until="commit")
        await asyncio.sleep(2)

        # 验证是否回到首页
        cards = await get_note_cards(page)
        if cards:
            return True

        # 方式2: 直接导航
        await goto_home(page)
        return True
    except Exception:
        # 兜底: 直接导航
        await goto_home(page)
        return True


# ════════════════════════════════════════════════════════════
# 搜索发现
# ════════════════════════════════════════════════════════════

# 小红书搜索关键词池（生活方式相关）
SEARCH_KEYWORDS = [
    "穿搭", "美食", "旅行", "护肤", "家居", "健身",
    "书单", "电影", "咖啡", "探店", "拍照", "收纳",
    "早餐", "减脂", "美甲", "发型", "礼物", "周末",
    "自律", "效率", "省钱", "租房", "装修", "宠物",
]


async def search(page, keyword: str = None) -> str:
    """
    搜索关键词

    Args:
        keyword: 搜索词，None 时随机选择

    Returns:
        实际搜索的关键词
    """
    kw = keyword or random.choice(SEARCH_KEYWORDS)

    try:
        # 定位搜索框
        search_input = await page.query_selector(SEARCH_INPUT)
        if search_input:
            await search_input.click()
            await asyncio.sleep(0.5)
            await search_input.fill(kw)
            await asyncio.sleep(0.3)

            # 按回车搜索
            await search_input.press("Enter")
            await asyncio.sleep(3)
            return kw
    except Exception:
        pass

    # fallback: URL 直接搜索
    try:
        encoded_kw = kw.replace(" ", "%20")
        await page.goto(
            f"https://www.xiaohongshu.com/search_result?keyword={encoded_kw}",
            timeout=15000, wait_until="commit"
        )
        await asyncio.sleep(3)
        return kw
    except Exception:
        return ""


async def click_search_result(page, index: int = None) -> Optional[str]:
    """
    点击搜索结果中的笔记

    Args:
        index: 结果索引，None 时随机

    Returns:
        笔记 URL
    """
    try:
        results = await page.query_selector_all(".note-item, [class*=search-result] a")
        if not results:
            return None

        idx = index if index is not None else random.randint(0, min(3, len(results) - 1))
        if idx < len(results):
            await results[idx].click()
            await asyncio.sleep(2)
            return page.url
    except Exception:
        pass

    return None


# ════════════════════════════════════════════════════════════
# 锚点验证
# ════════════════════════════════════════════════════════════

async def check_anchor(page, anchor_type: str, timeout: float = 3.0) -> bool:
    """检测页面锚点状态"""
    try:
        selector = ANCHORS.get(anchor_type)
        if not selector:
            return False

        el = await page.query_selector(selector)
        return el is not None
    except Exception:
        return False
