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

    # 先确保图片加载完成（最多等 12 秒——回退后懒加载新卡片需要时间）
    await wait_for_feed_ready(page, timeout=12)

    # 优先用 section.note-item 获取 bounding rect
    # 只选在当前视口内（y < viewport height）的卡片
    cards = await page.evaluate("""() => {
        const sections = [...document.querySelectorAll('section.note-item')];
        const viewH = window.innerHeight;
        return sections.map((s, i) => {
            const r = s.getBoundingClientRect();
            return {
                index: i,
                href: s.querySelector('a')?.href || '',
                rect: {x: r.x, y: r.y, w: r.width, h: r.height},
                in_viewport: r.y >= 0 && r.y < viewH,
            };
        }).filter(c => c.rect.w >= 10 && c.rect.h >= 10);
    }""")

    if not cards:
        return None

    # 优先从可视区内的卡片中选择
    visible_cards = [c for c in cards if c.get('in_viewport')]
    pool = visible_cards if len(visible_cards) >= 2 else cards

    # 随机选择（优先选可视区的前几卡）
    if index is None:
        max_idx = min(2, len(pool) - 1)  # 只从0-2选
        index = pool[random.randint(0, max_idx)]['index']
    if index >= len(cards):
        index = cards[random.randint(0, len(cards) - 1)]['index']

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
            # 点卡片偏下方（60% 高度处，避开顶部作者区）
            cy = pos['y'] + pos['h'] * 0.6

            await page.mouse.move(cx, cy, steps=random.randint(5, 12))
            await asyncio.sleep(random.uniform(0.3, 0.8))

            # ⚡ 单次单击（XHS 双击触发图片查看器）
            await page.mouse.click(cx, cy)
            await asyncio.sleep(3)

            # 锚点验证
            anchor = await page.evaluate(is_note_detail_mode_js())
            if anchor.get('qr_blocked'):
                # QR 码拦截墙 — 非常用登录触发，导航回首页重试其他卡片
                await goto_home(page)
                await asyncio.sleep(2)
                return 'qr_blocked'
            if anchor.get('is_author_profile'):
                # 打成作者主页了 → ESC 退回再重试
                await page.keyboard.press("Escape")
                await asyncio.sleep(2)
                return 'qr_blocked'  # 让外层走重试逻辑
            if anchor.get('is_detail'):
                return page.url

            # 锚点失败 — fallback 直接导航
            if href:
                await page.goto(href, timeout=15000, wait_until="commit")
                await asyncio.sleep(2)
                anchor = await page.evaluate(is_note_detail_mode_js())
                if anchor.get('qr_blocked'):
                    await goto_home(page)
                    await asyncio.sleep(2)
                    return 'qr_blocked'
                if anchor.get('is_author_profile'):
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(2)
                    return 'qr_blocked'
                if anchor.get('is_detail'):
                    return page.url
            return None

        except Exception:
            # fallback
            if href:
                try:
                    await page.goto(href, timeout=15000, wait_until="commit")
                    await asyncio.sleep(2)
                    anchor = await page.evaluate(is_note_detail_mode_js())
                    if anchor.get('qr_blocked'):
                        await goto_home(page)
                        await asyncio.sleep(2)
                        return 'qr_blocked'
                    if anchor.get('is_author_profile'):
                        await page.keyboard.press("Escape")
                        await asyncio.sleep(2)
                        return 'qr_blocked'
                    if anchor.get('is_detail'):
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
    """鼠标滚轮滚动一小段（真人的滚轮操作，触发 IntersectionObserver）"""
    try:
        dist = distance or random.randint(80, 200)
        await page.mouse.wheel(0, dist)
    except Exception:
        pass
    await asyncio.sleep(random.uniform(0.5, 1.2))
    return distance


async def scroll_feed_human(page, screens: int = 1):
    """
    真人滚轮下滑：鼠标滚轮 × 多次，模拟真实阅读节奏

    - 每次滚 80-200px（≈ 自然滚轮一次）
    - 每次间隔 0.5-1.5s（看内容/等图片加载）
    - 每次滚完后检查卡片是否在视口内
    - 如果滚过头了用 ArrowUp 回正
    """
    for s in range(screens):
        for tick in range(random.randint(3, 6)):
            dist = random.randint(80, 200)
            await page.mouse.wheel(0, dist)
            await asyncio.sleep(random.uniform(0.5, 1.5))

        # 回滚验证：确保至少 2 张卡片在视口
        cards_in_view = await page.evaluate("""() => {
            const vh = window.innerHeight;
            let n = 0;
            for (const c of document.querySelectorAll('section.note-item')) {
                const r = c.getBoundingClientRect();
                if (r.bottom > 0 && r.top < vh && r.width > 10) n++;
                if (n >= 2) break;
            }
            return n;
        }""")
        if cards_in_view < 2:
            for _ in range(15):
                await page.keyboard.press("ArrowUp")
                await asyncio.sleep(0.08)
            await asyncio.sleep(1)

        # 阅读停顿
        await asyncio.sleep(random.uniform(2.0, 4.0))

    return screens


# ════════════════════════════════════════════════════════════
# 笔记详情页浏览
# ════════════════════════════════════════════════════════════

async def browse_note_detail(page, duration: float = None):
    """
    在笔记详情页浏览内容（图文/视频自适应）
    操作后验证：仍在详情页

    Args:
        duration: 浏览时长(秒)，None 时随机 4~12 秒

    Returns:
        实际浏览秒数，或 -1（页面不在详情页）
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
        await asyncio.sleep(random.uniform(1, 2))
    else:
        # 图文笔记：键盘箭头↓模拟真人阅读
        steps = max(2, int(watch / 2))
        for _ in range(steps):
            for _ in range(random.randint(2, 5)):
                await page.keyboard.press("ArrowDown")
                await asyncio.sleep(random.uniform(0.1, 0.3))
            await asyncio.sleep(random.uniform(1.0, 2.5))

    # 锚点验证：确认仍在详情页（浏览过程中可能误触导致跳转）
    from .selectors import is_note_detail_mode_js
    anchor = await page.evaluate(is_note_detail_mode_js())
    if anchor.get('is_detail'):
        return watch
    elif anchor.get('is_author_profile'):
        return -1  # 误触到作者主页
    elif anchor.get('qr_blocked'):
        return -1
    else:
        # 不在详情页（退回首页了或其他）
        return -1


async def check_page_health(page) -> dict:
    """诊断页面渲染状态（黑屏/滚动过头/CSS隐藏/正常）"""
    try:
        return await page.evaluate("""() => {
            const body = document.body;
            if (!body) return {alive: false, reason: 'no body'};

            const cards = [...document.querySelectorAll('section.note-item')];
            const imgs = [...document.querySelectorAll('img')];
            const loadedImgs = imgs.filter(i => i.complete && i.naturalWidth > 0);
            const noteDetail = document.querySelector('.note-detail-mask, [class*=note-detail]');
            const vh = window.innerHeight;
            const scrollY = window.scrollY;

            let inView = 0, offScreenAbove = 0, offScreenBelow = 0, cssHidden = 0;
            for (const c of cards.slice(0, 10)) {
                const style = window.getComputedStyle(c);
                const r = c.getBoundingClientRect();
                if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) < 0.1) {
                    cssHidden++; continue;
                }
                if (r.bottom > 0 && r.top < vh && r.width > 10) { inView++; }
                else if (r.bottom <= 0) { offScreenAbove++; }
                else if (r.top >= vh) { offScreenBelow++; }
                else { offScreenAbove++; }
            }

            let blackScreen = false, reason = '', scrollIssue = '';
            if (cards.length === 0 && !noteDetail) {
                blackScreen = true; reason = 'empty page - no cards or detail';
            } else if (cards.length > 0 && inView === 0 && offScreenBelow > 0) {
                blackScreen = true; scrollIssue = 'below';
                reason = `scrolled too far down - ${offScreenBelow} cards below viewport (scrollY=${scrollY})`;
            } else if (cards.length > 0 && inView === 0 && offScreenAbove > 0) {
                blackScreen = true; scrollIssue = 'above';
                reason = `scrolled too far up - ${offScreenAbove} cards above viewport (scrollY=${scrollY})`;
            } else if (cards.length > 0 && inView === 0 && cssHidden > 0) {
                blackScreen = true; scrollIssue = 'css_hidden';
                reason = `${cssHidden}/10 cards CSS-hidden (display:none/opacity:0)`;
            } else if (cards.length > 0 && inView > 0 && loadedImgs.length === 0 && imgs.length > 5) {
                blackScreen = true; scrollIssue = 'no_images';
                reason = `${inView} cards visible but 0/${imgs.length} images loaded`;
            }

            return {
                alive: !blackScreen, black_screen: blackScreen, reason: reason,
                scroll_issue: scrollIssue, scroll_y: scrollY,
                cards_total: cards.length, cards_in_view: inView,
                cards_above: offScreenAbove, cards_below: offScreenBelow, cards_hidden: cssHidden,
                total_images: imgs.length, loaded_images: loadedImgs.length,
                in_detail_mode: !!noteDetail, vp_h: vh,
            };
        }""")
    except Exception as e:
        return {"alive": False, "error": str(e)}


async def wait_for_feed_ready(page, timeout: float = 8.0) -> bool:
    """等待首页瀑布流图片加载完成"""
    try:
        for _ in range(int(timeout * 2)):
            ready = await page.evaluate("""() => {
                const cards = document.querySelectorAll('section.note-item');
                if (cards.length < 5) return 'no_cards';
                const imgs = [...cards].map(c => c.querySelector('img')).filter(Boolean).slice(0, 5);
                if (imgs.length === 0) return 'no_images';
                const loaded = imgs.filter(img => img.complete && img.naturalWidth > 0);
                if (loaded.length >= 3) return 'ready';
                return 'loading';
            }""")
            if ready == 'ready':
                return True
            await asyncio.sleep(0.5)
        return False
    except Exception:
        return False


async def go_back_to_home(page):
    """从详情页返回首页（ESC 键关闭 SPA 遮罩，保留 feed 状态）

    XHS 笔记详情是 SPA overlay (.note-detail-mask)，ESC 键关闭它。
    - 底下的首页完全保留，包括已加载的图片
    - 不需要重新导航或等待图片加载
    - 完全真人操作，最接近真实用户行为
    """
    try:
        # ESC 键关闭详情遮罩（SPA 原生支持）
        await page.keyboard.press("Escape")
        await asyncio.sleep(2)

        # 验证是否回到首页（遮罩消失 + 瀑布流可见）
        back = await page.evaluate("""() => {
            const mask = document.querySelector('.note-detail-mask, [class*=note-detail]');
            const cards = document.querySelectorAll('section.note-item');
            return {mask_gone: !mask, cards: cards.length};
        }""")
        if back.get('mask_gone', True) and back.get('cards', 0) > 5:
            return True

        # 再按一次 ESC（有时候需要两次）
        await page.keyboard.press("Escape")
        await asyncio.sleep(1.5)

        back2 = await page.evaluate("""() => {
            const mask = document.querySelector('.note-detail-mask, [class*=note-detail]');
            const cards = document.querySelectorAll('section.note-item');
            return {mask_gone: !mask, cards: cards.length};
        }""")
        if back2.get('mask_gone', True) and back2.get('cards', 0) > 5:
            return True

        # 检测页面健康度（ESC 可能没触发，或页面异常）
        health = await check_page_health(page)
        if health.get('alive'):
            return True

        # 兜底: goto_home + 键盘滚动恢复
        await goto_home(page)
        await asyncio.sleep(2)
        for _ in range(15):
            await page.keyboard.press("ArrowDown")
            await asyncio.sleep(0.15)
        await wait_for_feed_ready(page, timeout=8)
        return bool(await get_note_cards(page))

    except Exception:
        await goto_home(page)
        await asyncio.sleep(3)
        return True
        await asyncio.sleep(3)
        images_ok = await wait_for_feed_ready(page, timeout=5)
        return bool(images_ok or await get_note_cards(page))

    except Exception:
        # 兜底: 直接导航
        await goto_home(page)
        await asyncio.sleep(3)
        await wait_for_feed_ready(page, timeout=5)
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
    搜索关键词（兼容标准版 + AI-layout 版）

    Args:
        keyword: 搜索词，None 时随机选择

    Returns:
        实际搜索的关键词
    """
    kw = keyword or random.choice(SEARCH_KEYWORDS)

    # ── 方式1: 标准搜索框 ──
    try:
        search_input = await page.query_selector(SEARCH_INPUT)
        if search_input:
            await search_input.click()
            await asyncio.sleep(0.5)
            await search_input.fill(kw)
            await asyncio.sleep(0.3)
            await search_input.press("Enter")
            await asyncio.sleep(3)
            return kw
    except Exception:
        pass

    # ── 方式2: AI 布局备用搜索框 ──
    try:
        from .selectors import SEARCH_INPUT_ALT
        search_input = await page.query_selector(SEARCH_INPUT_ALT)
        if search_input:
            await search_input.click()
            await asyncio.sleep(0.5)
            await search_input.fill(kw)
            await asyncio.sleep(0.3)
            await search_input.press("Enter")
            await asyncio.sleep(3)
            return kw
    except Exception:
        pass

    # ── 方式3: URL 直接搜索 ──
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
    点击搜索结果中的笔记（兼容标准版 + AI-layout 版）

    Args:
        index: 结果索引，None 时随机

    Returns:
        笔记 URL
    """
    # ── 方式1: 标准搜索结果选择器 ──
    try:
        results = await page.query_selector_all(".note-item, [class*=search-result] a")
        if results:
            idx = index if index is not None else random.randint(0, min(3, len(results) - 1))
            if idx < len(results):
                await results[idx].click()
                await asyncio.sleep(2)
                return page.url
    except Exception:
        pass

    # ── 方式2: 通用链接点击（找任何包含笔记 ID 的链接）──
    try:
        links = await page.evaluate("""() => {
            const links = [...document.querySelectorAll('a[href*="/explore/"]')];
            return links.map(a => a.href).filter(h => /\\/explore\\/[a-f0-9]{20,}/.test(h));
        }""")
        if links:
            target = random.choice(links)
            await page.goto(target, timeout=15000, wait_until="commit")
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
