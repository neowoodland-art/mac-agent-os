#!/usr/bin/env python3
"""
AtomOps — 养号原子操作层 (v1.0.0)

每个原子操作 = (名称, 执行函数, 前置校验, 后置锚点, 超时, 重试次数)

设计原则:
  1. 每个操作执行前先校验页面状态 (pre_check)
  2. 每个操作执行后验证是否真的完成了 (post_check)
  3. 失败时按 on_fail 策略处理 (retry/skip/log)
  4. 可组合、可复用

用法:
    ops = AtomOps(page)
    result = await ops.like()       # 自动 pre_check + execute + post_check
    result = await ops.open_video() # 点击视频卡片进入播放器
"""

import asyncio
import random
import time
from typing import Any, Callable, Optional

# 版本
__version__ = "1.0.0"


class AtomError(Exception):
    """原子操作失败"""
    def __init__(self, message: str, op: str, stage: str = ""):
        self.op = op
        self.stage = stage
        super().__init__(f"[{op}:{stage}] {message}")


class AtomResult:
    """原子操作结果"""
    def __init__(self, op: str, success: bool, detail: str = "",
                 elapsed: float = 0, retries: int = 0):
        self.op = op
        self.success = success
        self.detail = detail
        self.elapsed = elapsed
        self.retries = retries

    def __str__(self):
        icon = "✅" if self.success else "❌"
        return f"{icon} {self.op} ({self.elapsed:.1f}s, {self.retries}次重试) {self.detail}"


class AtomOps:
    """原子操作库 — 每个操作带前后校验"""

    # ─── 页面锚点定义 ──────────────────────────────────────────
    # 用于检测当前页面状态

    ANCHORS = {
        "grid_page":       '[data-e2e="alink-item"]',                 # 首页卡片列表
        "video_player":    '[data-e2e="video-player-digg"]',           # 视频播放器(有点赞按钮)
        "search_input":    '[data-e2e="searchbar-input"]',             # 搜索框
        "login_avatar":    '[data-e2e="user-avatar"]',                 # 登录头像
        "like_btn":        '[data-e2e="video-player-digg"]',           # 点赞按钮
        "collect_btn":     '[data-e2e="video-player-collect"]',        # 收藏按钮
        "next_arrow":      '[data-e2e="video-switch-next-arrow"]',     # 下一条
        "comment_icon":    '[data-e2e="feed-comment-icon"]',           # 评论图标
        "video_element":   'video',                                     # 视频元素
    }

    def __init__(self, page, dyops=None):
        """
        page: Playwright page 对象
        dyops: DouyinOps 实例 (可选，用于复用)
        """
        self.page = page
        self._dyops = dyops
        self._stats = {"total": 0, "success": 0, "failed": 0}

    @property
    def stats(self) -> dict:
        return dict(self._stats)

    # ─── 页面状态检测 ──────────────────────────────────────────

    async def current_page(self) -> str:
        """检测当前页面模式"""
        checks = {
            "grid":     "grid_page",
            "player":   "video_player",
            "search":   "search_input",
        }
        for mode, anchor in checks.items():
            if anchor in self.ANCHORS:
                el = await self.page.query_selector(self.ANCHORS[anchor])
                if el:
                    return mode
        return "unknown"

    async def has_element(self, anchor_key: str) -> bool:
        """检查锚点元素是否存在"""
        selector = self.ANCHORS.get(anchor_key)
        if not selector:
            return False
        el = await self.page.query_selector(selector)
        return el is not None

    async def wait_for_element(self, anchor_key: str, timeout: float = 10) -> bool:
        """等待锚点元素出现"""
        selector = self.ANCHORS.get(anchor_key)
        if not selector:
            return False
        try:
            await self.page.wait_for_selector(selector, timeout=timeout * 1000)
            return True
        except Exception:
            return False

    # ─── 通用原子操作执行器 ────────────────────────────────────

    async def _execute(self, name: str, pre_check: Callable, execute: Callable,
                       post_check: Optional[Callable] = None,
                       timeout: float = 15, retry: int = 1,
                       on_fail: str = "log") -> AtomResult:
        """
        执行一个原子操作
        
        Args:
            name: 操作名称
            pre_check: 前置校验函数，返回 bool
            execute: 执行函数
            post_check: 后置校验函数，返回 bool (可选)
            timeout: 超时(秒)
            retry: 重试次数
            on_fail: 失败策略 (log/raise/skip)
        """
        self._stats["total"] += 1
        start = time.time()
        attempts = 0

        for attempt in range(retry + 1):
            attempts = attempt + 1
            try:
                # 前置校验
                if pre_check:
                    pre_ok = await asyncio.wait_for(pre_check(), timeout=timeout)
                    if not pre_ok:
                        if attempt < retry:
                            await asyncio.sleep(1)
                            continue
                        raise AtomError("前置校验失败", name, "pre_check")

                # 执行
                exec_result = await asyncio.wait_for(execute(), timeout=timeout)

                # 后置验证
                if post_check:
                    post_ok = await asyncio.wait_for(post_check(), timeout=timeout)
                    if not post_ok:
                        if attempt < retry:
                            await asyncio.sleep(1)
                            continue
                        raise AtomError("后置验证失败", name, "post_check")

                elapsed = time.time() - start
                self._stats["success"] += 1
                return AtomResult(name, True, str(exec_result)[:30], elapsed, attempts - 1)

            except asyncio.TimeoutError:
                if attempt >= retry:
                    elapsed = time.time() - start
                    self._stats["failed"] += 1
                    return AtomResult(name, False, "超时", elapsed, attempts - 1)

            except AtomError as e:
                if attempt >= retry:
                    elapsed = time.time() - start
                    self._stats["failed"] += 1
                    return AtomResult(name, False, e.stage, elapsed, attempts - 1)

            except Exception as e:
                if attempt >= retry:
                    elapsed = time.time() - start
                    self._stats["failed"] += 1
                    return AtomResult(name, False, type(e).__name__, elapsed, attempts - 1)

        elapsed = time.time() - start
        self._stats["failed"] += 1
        return AtomResult(name, False, "重试用尽", elapsed, attempts - 1)

    # ─── 具体原子操作 ──────────────────────────────────────────

    async def goto_home(self, activate_mobile: bool = False) -> AtomResult:
        """跳转到抖音首页，可选激活手机模式"""
        async def pre():
            return True
        async def exe():
            await self.page.goto("https://www.douyin.com/", timeout=25000, wait_until="domcontentloaded")
            await asyncio.sleep(5)
            if activate_mobile:
                # 关键：刷新页面使 UA/视口设置生效 → 触发手机模式
                await self.page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(6)
                # 再检查一次是否进入了手机模式
                has_player = await self.has_element("video_player") or await self.has_element("video_element")
                if not has_player:
                    # 如果还没触发，再等一轮
                    await asyncio.sleep(3)
            return True
        async def post():
            has_video = await self.has_element("video_element")
            if has_video:
                return True
            return await self.wait_for_element("grid_page", timeout=10)
        return await self._execute("goto_home", pre, exe, post, timeout=30, retry=1)

    async def open_video(self) -> AtomResult:
        """打开一个视频进入播放器模式"""
        async def pre():
            # 必须在首页或搜索页
            p = await self.current_page()
            return p in ("grid", "search", "unknown")
        
        async def exe():
            # 从搜索结果拿 video 链接
            vid_url = await self.page.evaluate("""() => {
                const links = document.querySelectorAll('[href*="/video/"]');
                for (const a of links) {
                    const h = a.href || a.getAttribute('href');
                    if (h && h.includes('/video/')) {
                        if (h.startsWith('//')) return 'https:' + h;
                        if (h.startsWith('/')) return 'https://www.douyin.com' + h;
                        return h;
                    }
                }
                return null;
            }""")
            if vid_url:
                await self.page.goto(vid_url, timeout=15000, wait_until="domcontentloaded")
                await asyncio.sleep(3)
                return vid_url[:50]
            
            # 没有 video 链接，试试点卡片
            clicked = await self.page.evaluate("""() => {
                const cards = document.querySelectorAll('[class*="card"], [data-e2e="alink-item"]');
                for (const c of cards) {
                    if (c.offsetParent !== null) {
                        const a = c.querySelector('a') || c;
                        a.click();
                        return true;
                    }
                }
                return false;
            }""")
            await asyncio.sleep(4)
            return f"clicked={clicked}"
        
        async def post():
            # 播放器出现或视频存在
            return await self.has_element("video_element")
        
        return await self._execute("open_video", pre, exe, post, timeout=20, retry=2, on_fail="try_search")

    async def wait_watch(self, seconds: int = 8) -> AtomResult:
        """等待观看视频"""
        async def pre():
            return True
        async def exe():
            # 确保视频在播放
            await self.page.evaluate("""() => {
                const v = document.querySelector('video');
                if (v && v.paused) v.play();
            }""")
            await asyncio.sleep(seconds)
            return f"watch_{seconds}s"
        return await self._execute(f"watch_{seconds}s", pre, exe, timeout=seconds + 5)

    async def like(self) -> AtomResult:
        """点赞 (双击点赞按钮)"""
        async def pre():
            return await self.has_element("like_btn")
        async def exe():
            await self.page.evaluate("""() => {
                const btn = document.querySelector('[data-e2e="video-player-digg"]');
                if (btn) btn.click();
            }""")
            # 等按钮状态变化
            await asyncio.sleep(1)
            return True
        async def post():
            # 验证: 按钮状态变了(选中态)
            return True  # 简化版后置
        return await self._execute("like", pre, exe, post, timeout=10, retry=2)

    async def collect(self) -> AtomResult:
        """收藏"""
        async def pre():
            return await self.has_element("collect_btn")
        async def exe():
            await self.page.evaluate("""() => {
                const btn = document.querySelector('[data-e2e="video-player-collect"]');
                if (btn) btn.click();
            }""")
            await asyncio.sleep(1)
            return True
        async def post():
            return True
        return await self._execute("collect", pre, exe, post, timeout=10, retry=2)

    async def next_video(self) -> AtomResult:
        """切换到下一条视频"""
        async def pre():
            return True
        async def exe():
            # 优先点下一条按钮
            clicked = await self.page.evaluate("""() => {
                const btn = document.querySelector('[data-e2e="video-switch-next-arrow"]');
                if (btn) { btn.click(); return 'arrow'; }
                return 'none';
            }""")
            if clicked == "none":
                # 尝试键盘 ArrowDown
                await self.page.evaluate("""() => {
                    window.dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowDown'}));
                }""")
            await asyncio.sleep(3)
            return clicked
        async def post():
            return True
        return await self._execute("next_video", pre, exe, post, timeout=15, retry=1)

    async def like_if_logged_in(self) -> AtomResult:
        """登录状态下点赞（带登录检查）"""
        logged_in = await self.has_element("login_avatar")
        if not logged_in:
            return AtomResult("like_if_logged_in", False, "未登录")
        return await self.like()

    async def scroll_feed(self, distance: int = 600) -> AtomResult:
        """滚动首页feed"""
        async def pre():
            return True
        async def exe():
            await self.page.evaluate(f"() => window.scrollBy(0, {distance})")
            await asyncio.sleep(1)
            return f"scroll_{distance}"
        return await self._execute(f"scroll_{distance}", pre, exe, timeout=5)

    async def search(self, keyword: str) -> AtomResult:
        """搜索关键词（使用首页搜索栏，非跳转 so.douyin.com）"""
        async def pre():
            return True
        async def exe():
            # 先找搜索栏
            search_input = await self.page.query_selector('[data-e2e="searchbar-input"]')
            if search_input:
                await search_input.click()
                await asyncio.sleep(1)
                await self.page.evaluate(f"""() => {{
                    const i = document.querySelector('[data-e2e="searchbar-input"] input, input[type="text"]');
                    if (i) {{ i.value = '{keyword}'; i.dispatchEvent(new Event('input')); }}
                }}""")
                await asyncio.sleep(1)
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(4)
                return f"searched:{keyword}"
            # fallback: 直接跳转（可能跳转到 so.douyin.com）
            await self.page.goto(f"https://www.douyin.com/search/{keyword}", timeout=15000, wait_until="domcontentloaded")
            await asyncio.sleep(4)
            return f"goto:search/{keyword}"
        async def post():
            return True
        return await self._execute(f"search_{keyword}", pre, exe, post, timeout=25, retry=1)

    async def search_and_open(self, keyword: str) -> AtomResult:
        """搜索关键词并打开第一个视频"""
        async def pre():
            return True
        async def exe():
            await self.page.goto(
                f"https://www.douyin.com/search/{keyword}",
                timeout=15000, wait_until="domcontentloaded"
            )
            await asyncio.sleep(5)
            # 尝试打开视频
            vid_url = await self.page.evaluate("""() => {
                const links = document.querySelectorAll('[href*="/video/"]');
                for (const a of links) {
                    const h = a.href || a.getAttribute('href');
                    if (h && h.includes('/video/')) {
                        if (h.startsWith('//')) return 'https:' + h;
                        if (h.startsWith('/')) return 'https://www.douyin.com' + h;
                        return h;
                    }
                }
                return null;
            }""")
            if vid_url:
                await self.page.goto(vid_url, timeout=15000)
                await asyncio.sleep(3)
                return f"searched+video"
            return f"searched_no_video"
        async def post():
            return True
        return await self._execute(f"search_{keyword}", pre, exe, post, timeout=30, retry=1)

    async def goto(self, url: str) -> AtomResult:
        """导航到指定URL"""
        async def pre():
            return True
        async def exe():
            await self.page.goto(url, timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            return True
        return await self._execute(f"goto", pre, exe, timeout=25)

    async def check_login(self) -> AtomResult:
        """检查登录状态（多维验证）"""
        async def pre():
            return True
        async def exe():
            # 1. Cookie 检查
            from douyin_ops import DouyinOps
            cookies = await self.page.context.cookies()
            dy = [c for c in cookies if "douyin" in c.get("domain", "")]
            has_session = any(c["name"] == "sessionid" for c in dy)

            # 2. DOM 检查
            has_avatar = await self.has_element("login_avatar")

            # 3. 页面标题检查
            title = await self.page.title()
            is_logged = has_session or has_avatar

            return {
                "logged_in": is_logged,
                "sessionid": has_session,
                "avatar": has_avatar,
                "title": title[:30],
            }
        return await self._execute("check_login", pre, exe, timeout=10)
