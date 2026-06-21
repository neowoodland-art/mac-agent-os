"""
PageInspector — 三层页面状态检测

L1: 页面类型 (grid/player/search/profile) — URL pattern + DOM特征
L2: 鼠标所在区域 (feed/video/comment/bottom_bar) — 坐标区间判断
L3: 鼠标指向元素详情 — tag/class/text/position

基于 ghai 的人类视角判断逻辑:
  1. 先看URL + 页面大结构 → 确定在什么页面
  2. 再看鼠标周围区域 → 确定操作上下文
  3. 最后看鼠标指向的具体元素 → 确定要操作什么

Usage:
  inspector = PageInspector(page, platform="douyin")
  state = await inspector.inspect()
  print(state.page_type)  # "player_modal"
  print(state.has_video)  # True
  print(state.nearby_elements)  # [element at cursor...]
"""
import asyncio
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PageState:
    """完整页面状态快照"""
    platform: str = ""
    url: str = ""
    title: str = ""

    # L1: 页面类型
    page_type: str = "unknown"          # grid/player_modal/player_full/search/profile/unknown
    page_type_confidence: float = 0.0

    # L1: DOM特征
    video_count: int = 0
    card_count: int = 0
    has_search_bar: bool = False
    has_nav: bool = False
    has_comment_list: bool = False
    is_self_page: bool = False          # 是否自己的主页
    author_id: str = ""

    # L2: 鼠标区域
    mouse_x: int = 0
    mouse_y: int = 0
    mouse_region: str = "unknown"       # feed_area/video_area/bottom_bar/comment_area/nav_area

    # L3: 附近元素
    nearby_elements: list = field(default_factory=list)  # [{tag, class, text, x, y, ...}]
    element_at_point: Optional[dict] = None

    # 验证
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class PageInspector:
    """三层页面状态检测器"""

    def __init__(self, page, platform: str = "douyin"):
        self.page = page
        self.platform = platform

    async def inspect(self, mouse_x: int = 0, mouse_y: int = 0) -> PageState:
        """执行完整三层检测"""
        state = PageState(platform=self.platform)

        try:
            # L1: 页面基本信息
            state.url = self.page.url
            state.title = await self.page.title()

            # L1: DOM特征
            dom = await self._capture_dom()
            state.video_count = dom["video_count"]
            state.card_count = dom["card_count"]
            state.has_search_bar = dom["has_search_bar"]
            state.has_nav = dom["has_nav"]
            state.has_comment_list = dom["has_comment_list"]
            state.author_id = dom["author_id"]
            state.is_self_page = dom["is_self"]

            # L1: 页面类型判定
            state.page_type = self._classify_page_type(state)

            # L2: 鼠标区域
            if mouse_x > 0 and mouse_y > 0:
                state.mouse_x = mouse_x
                state.mouse_y = mouse_y
                size = await self.page.evaluate(
                    "() => ({ w: window.innerWidth, h: window.innerHeight })"
                )
                state.mouse_region = self._classify_region(
                    mouse_x, mouse_y, size["w"], size["h"]
                )

            # L3: 鼠标处元素
            if mouse_x > 0 and mouse_y > 0:
                el_info = await self.page.evaluate(
                    f"""() => {{
                        const el = document.elementFromPoint({mouse_x}, {mouse_y});
                        if (!el) return null;
                        const rect = el.getBoundingClientRect();
                        return {{
                            tag: el.tagName,
                            class: el.className || '',
                            text: (el.textContent || '').trim().slice(0, 50),
                            x: Math.round(rect.left), y: Math.round(rect.top),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                            visible: el.offsetParent !== null
                        }};
                    }}"""
                )
                state.element_at_point = el_info

            # L3: 附近区域元素（鼠标周围200px内的可交互元素）
            if mouse_x > 0 and mouse_y > 0:
                nearby = await self.page.evaluate(
                    f"""() => {{
                        const mx = {mouse_x}, my = {mouse_y};
                        const els = document.querySelectorAll(
                            'a, button, span, div, input, textarea, svg')
                        const results = [];
                        for (const el of els) {{
                            if (!el.offsetParent) continue;
                            const r = el.getBoundingClientRect();
                            const cx = r.left + r.width/2;
                            const cy = r.top + r.height/2;
                            const dist = Math.sqrt((cx-mx)**2 + (cy-my)**2);
                            if (dist < 200) {{
                                results.push({{
                                    tag: el.tagName,
                                    class: (el.className || '').slice(0, 40),
                                    text: (el.textContent || '').trim().slice(0, 30),
                                    cx: Math.round(cx), cy: Math.round(cy), dist: Math.round(dist)
                                }});
                            }}
                        }}
                        return results.sort((a,b) => a.dist - b.dist).slice(0, 10);
                    }}"""
                )
                state.nearby_elements = nearby

        except Exception as e:
            state.errors.append(str(e))

        return state

    async def _capture_dom(self) -> dict:
        """捕获DOM特征"""
        try:
            return await self.page.evaluate("""() => {
                const u = location.href;
                const vc = document.querySelectorAll('video').length;

                // cards: 视频卡片/笔记卡片
                const cards = document.querySelectorAll(
                    '.discover-video-card-item, [class*="video-card"], ' +
                    'section.note-item, a[href*="/explore/"], [class*="note-item"]'
                ).length;

                // 搜索栏
                const searchBar = document.querySelector(
                    '[data-e2e="searchbar-input"], input[placeholder*="搜索"], textarea.textarea'
                );

                // 导航
                const nav = document.querySelector(
                    '[data-e2e="douyin-navigation"], [class*="nav"], .ulxic5B4'
                );

                // 评论列表
                const commentList = document.querySelector(
                    '[data-e2e="comment-list"], [class*="comment-list"]'
                );

                // 作者ID (从URL或个人信息区获取)
                let authorId = '';
                const userMatch = u.match(/\/user\/(\\d+)/);
                if (userMatch) authorId = userMatch[1];
                const exploreMatch = u.match(/\/explore\/(\\w+)/);
                if (exploreMatch) authorId = exploreMatch[1];

                // 是否自己的页面
                const isSelf = u.includes('/user/self') ||
                    !!document.querySelector('[data-e2e="user-info"]');

                return {
                    video_count: vc,
                    card_count: cards,
                    has_search_bar: !!searchBar,
                    has_nav: !!nav,
                    has_comment_list: !!commentList,
                    author_id: authorId,
                    is_self: isSelf
                };
            }""")
        except:
            return {"video_count":0, "card_count":0, "has_search_bar":False,
                    "has_nav":False, "has_comment_list":False, "author_id":"", "is_self":False}

    def _classify_page_type(self, state: PageState) -> str:
        """L1: 页面类型判定"""
        u = state.url.lower()

        # 个人主页
        if '/user/' in u:
            return 'profile'

        # 搜索页
        if '/search' in u:
            return 'search'

        # 播放页: 有video
        if state.video_count > 0:
            if '/video/' in u and 'modal_id' not in u:
                return 'player_full'
            if 'modal_id' in u:
                return 'player_modal'
            return 'player'

        # 笔记详情页 (小红书)
        if '/explore/' in u and u.count('/') >= 4:
            return 'note_detail'

        # 首页/grid
        if state.card_count > 0 or '/jingxuan' in u or '/explore' in u:
            return 'grid'

        return 'unknown'

    def _classify_region(self, x: int, y: int, w: int, h: int) -> str:
        """L2: 鼠标区域判定（基于百分比位置）"""
        x_pct = x / w
        y_pct = y / h

        # 视频播放区（中央上部区域）
        if 0.2 < x_pct < 0.8 and 0.1 < y_pct < 0.5:
            return 'video_area'

        # 底部互动按钮区
        if 0.2 < x_pct < 0.8 and y_pct > 0.8:
            return 'bottom_bar'

        # 评论区（底部大区域）
        if y_pct > 0.7:
            return 'comment_area'

        # 左侧导航区
        if x_pct < 0.2:
            return 'nav_area'

        # 右侧推荐区
        if x_pct > 0.8:
            return 'sidebar'

        # 内容feed区（中下部）
        if 0.2 < x_pct < 0.8 and 0.5 < y_pct < 0.8:
            return 'feed_area'

        return 'unknown'


async def demo(page):
    """快速演示"""
    inspector = PageInspector(page, "douyin")

    # 全量检测
    state = await inspector.inspect()
    print(f"[{state.page_type}] v={state.video_count} c={state.card_count}")

    # 带鼠标位置的检测（模拟鼠标在右下角互动区）
    state2 = await inspector.inspect(mouse_x=479, mouse_y=687)
    print(f"鼠标区域: {state2.mouse_region}")
    print(f"指向元素: {state2.element_at_point}")
    print(f"附近元素: {len(state2.nearby_elements)}个")
    for el in state2.nearby_elements[:3]:
        print(f"  {el['tag']} dist={el['dist']} {el['class'][:20]}")
    return state2
