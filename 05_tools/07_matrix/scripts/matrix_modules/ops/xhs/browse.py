"""
小红书 — 浏览类操作
基于 2026-05-20 DOM 分析结果

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
    ANCHORS, get_note_links_js, get_note_cards_js, dismiss_login_modal_js,
    find_refresh_button_js, find_qr_wall_back_button_js
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


async def click_note_card(page, index: int = None, max_retries: int = 3) -> Optional[str]:
    """
    点击笔记卡片进入详情页

    Args:
        index: 卡片索引（0-based），None 时随机选择
        max_retries: 误触作者主页时最大重试次数

    Returns:
        笔记 URL，失败返回 None
    """
    for attempt in range(max_retries):
        cards = await get_note_cards(page)
        if not cards:
            return None

        # 随机选择卡片（避免总是点第一个）
        if index is None:
            # 优先选前 4 个，避免滚动到底部
            max_idx = min(3, len(cards) - 1)
            idx = random.randint(0, max_idx)
        else:
            idx = index

        if idx >= len(cards):
            idx = random.randint(0, len(cards) - 1)

        card = cards[idx]
        href = card.get("href")
        if not href:
            return None

        # 记录点击前 tab 数量
        context = page.context
        tabs_before = len(context.pages)
        original_page = page

        # 使用 Playwright 点击（模拟真人）
        try:
            # 先尝试通过索引定位元素
            cards_els = await page.query_selector_all(NOTE_CARD)
            if idx < len(cards_els):
                await cards_els[idx].click()
                await asyncio.sleep(2)

                # 检测是否误触作者主页（新标签页）
                tabs_after = len(context.pages)
                if tabs_after > tabs_before:
                    # 新 tab 打开了作者主页 — 关闭新 tab，回到原 tab
                    new_tab = context.pages[-1]
                    new_url = new_tab.url
                    await new_tab.close()
                    print(f"  [browse] 误触作者主页（新标签页已关闭）: {new_url[:50]}")
                    # 切回原 tab
                    page = original_page
                    if attempt < max_retries - 1:
                        print(f"  [browse] 重试点击笔记 ({attempt + 2}/{max_retries})...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        return None

                return page.url
        except Exception:
            pass

    # fallback: 直接导航到链接
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
# 物理按钮操作（鼠标模拟）
# ════════════════════════════════════════════════════════════

async def _l_shaped_click(page, target_x: int, target_y: int, desc: str = "") -> bool:
    """
    L 型鼠标路径点击 — 模拟真人鼠标移动轨迹

    轨迹: 起点(随机偏移) → 水平移动到目标 x → 垂直移动到目标 y → 点击
    """
    import random
    try:
        viewport = page.viewport_size or {"width": 702, "height": 783}
        # 起点随机偏移
        start_x = target_x + random.randint(-150, 150)
        start_y = target_y + random.randint(-100, 50)
        # 限制在视口内
        start_x = max(50, min(start_x, viewport["width"] - 50))
        start_y = max(50, min(start_y, viewport["height"] - 50))

        # 移动鼠标到起点
        await page.mouse.move(start_x, start_y)
        await asyncio.sleep(random.uniform(0.05, 0.15))

        # L 型路径: 先水平移到目标 x
        steps = random.randint(5, 10)
        dx = (target_x - start_x) / steps
        for i in range(steps):
            await page.mouse.move(start_x + dx * (i + 1), start_y)
            await asyncio.sleep(random.uniform(0.01, 0.03))

        # 再垂直移到目标 y
        steps_v = random.randint(3, 8)
        dy = (target_y - start_y) / steps_v
        for i in range(steps_v):
            await page.mouse.move(target_x, start_y + dy * (i + 1))
            await asyncio.sleep(random.uniform(0.01, 0.03))

        # 微抖动（模拟手指不稳）
        jitter_x = target_x + random.randint(-2, 2)
        jitter_y = target_y + random.randint(-2, 2)
        await page.mouse.move(jitter_x, jitter_y)
        await asyncio.sleep(random.uniform(0.05, 0.1))

        # 点击
        await page.mouse.click(jitter_x, jitter_y)
        return True
    except Exception as e:
        if desc:
            pass  # 静默失败
        return False


async def click_refresh_button(page) -> bool:
    """
    点击小红书瀑布流页面右下角的刷新 FAB 按钮

    Returns:
        True=点击成功, False=未找到按钮
    """
    try:
        result = await asyncio.wait_for(
            page.evaluate(find_refresh_button_js()),
            timeout=10
        )
        if not result or not result.get("found"):
            return False

        x, y = result["x"], result["y"]
        return await _l_shaped_click(page, x, y, desc="refresh")
    except asyncio.TimeoutError:
        return False
    except Exception:
        return False


async def click_qr_wall_back_button(page) -> bool:
    """
    检测 QR 检测墙并点击"返回首页"按钮

    Returns:
        True=检测到QR墙并成功点击返回, False=未检测到QR墙或点击失败
    """
    try:
        result = await asyncio.wait_for(
            page.evaluate(find_qr_wall_back_button_js()),
            timeout=10
        )
        if not result or not result.get("found"):
            return False

        x, y = result["x"], result["y"]
        btn_text = result.get("text", "")
        success = await _l_shaped_click(page, x, y, desc="qr_back")
        return success
    except asyncio.TimeoutError:
        return False
    except Exception:
        return False


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
