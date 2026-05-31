#!/usr/bin/env python3
"""
PageState — 页面状态管理 (v1.0.0)

功能:
  - 检测当前页面模式 (grid/player/search/unknown)
  - 验证登录态 (Cookie + DOM + 标题多维检测)
  - 提供状态切换建议 (下一步该做什么)

用法:
    state = PageState(page)
    mode = await state.detect()      # → "grid" | "player" | "search"
    ok   = await state.check_login()
    next = await state.suggest()     # → 建议下一步操作
"""

import asyncio
from typing import Optional

__version__ = "1.0.0"


# 各模式的特征元素
MODE_SIGNATURES = {
    "grid": {
        "name": "首页卡片列表",
        "anchors": ['[data-e2e="alink-item"]'],
        "description": "显示视频卡片的推荐/精选页",
    },
    "player": {
        "name": "视频播放器",
        "anchors": ['[data-e2e="video-player-digg"]', '[data-e2e="video-player-collect"]'],
        "description": "单个视频播放页，有点赞/收藏按钮",
    },
    "search": {
        "name": "搜索结果",
        "anchors": ['[data-e2e="searchbar-input"]', '.search-container'],
        "description": "搜索结果页，显示视频列表",
    },
}


class PageState:
    """页面状态管理器"""

    def __init__(self, page):
        self.page = page
        self._mode = "unknown"
        self._last_check = 0

    async def detect(self) -> str:
        """检测当前页面模式"""
        for mode, sig in MODE_SIGNATURES.items():
            for anchor in sig["anchors"]:
                try:
                    el = await self.page.query_selector(anchor)
                    if el:
                        self._mode = mode
                        self._last_check = asyncio.get_event_loop().time()
                        return mode
                except Exception:
                    pass

        # Fallback: 通过 URL 判断
        url = self.page.url
        if "/video/" in url:
            self._mode = "player"
        elif "/search/" in url:
            self._mode = "search"
        elif "/jingxuan" in url or url.endswith("/douyin.com/"):
            self._mode = "grid"
        else:
            self._mode = "unknown"

        self._last_check = asyncio.get_event_loop().time()
        return self._mode

    @property
    def mode(self) -> str:
        """当前模式（可能过期，建议先调用 detect()）"""
        return self._mode

    @property
    def description(self) -> str:
        """当前模式的中文描述"""
        sig = MODE_SIGNATURES.get(self._mode)
        return sig["description"] if sig else "未知页面"

    async def check_login(self) -> dict:
        """多维登录验证

        返回:
            {"logged_in": bool, "method": str, "detail": str}
        """
        results = []

        # 1. Cookie 检查
        try:
            cookies = await self.page.context.cookies()
            dy = [c for c in cookies if "douyin" in c.get("domain", "")]
            has_session = any(c["name"] == "sessionid" for c in dy)
            has_sid = any(c["name"] == "sid_guard" for c in dy)
            if has_session:
                results.append(("cookie", True, "sessionid 存在"))
            elif has_sid:
                results.append(("cookie", True, "sid_guard 存在"))
            else:
                results.append(("cookie", False, "无登录态 Cookie"))
        except Exception:
            results.append(("cookie", False, "读取失败"))

        # 2. DOM 检查
        try:
            avatar = await self.page.query_selector('[data-e2e="user-avatar"]')
            detail = await self.page.query_selector('[data-e2e="user-detail"]')
            if avatar or detail:
                results.append(("dom", True, "用户头像可见"))
            else:
                results.append(("dom", False, "无头像元素"))
        except Exception:
            results.append(("dom", False, "检查失败"))

        # 3. 标题检查
        try:
            title = await self.page.title()
            if "登录" in title:
                results.append(("title", False, "标题含登录字样"))
            else:
                results.append(("title", True, f"标题：{title[:30]}"))
        except Exception:
            results.append(("title", False, "读取失败"))

        # 综合判断: 任意一个方法确认即可
        positive = [r for r in results if r[1]]
        logged_in = len(positive) >= 1

        return {
            "logged_in": logged_in,
            "detail": results,
            "methods_checked": len(results),
            "methods_passed": len(positive),
        }

    async def suggest(self) -> list:
        """根据当前状态建议下一步操作"""
        mode = await self.detect()
        login_info = await self.check_login()

        suggestions = []

        if mode == "unknown":
            suggestions.append({
                "action": "goto_home",
                "reason": "无法识别当前页面，跳转首页",
            })
        elif mode == "grid":
            suggestions.append({
                "action": "open_video",
                "reason": "在首页，可以打开一个视频",
            })
            suggestions.append({
                "action": "scroll_feed",
                "reason": "浏览推荐内容",
            })
            # 如果未登录
            if not login_info["logged_in"]:
                decisions = "、".join(
                    [f"{r[0]}:{'✅' if r[1] else '❌'}" for r in login_info.get("detail", [])]
                )
                suggestions.append({
                    "action": "notify_login",
                    "reason": f"可能未登录 ({decisions})",
                })
        elif mode == "player":
            suggestions.append({
                "action": "like",
                "reason": "在播放器，可以点赞",
            })
            suggestions.append({
                "action": "collect",
                "reason": "可以收藏",
            })
            suggestions.append({
                "action": "next_video",
                "reason": "可以看下一条",
            })
            suggestions.append({
                "action": "wait_watch",
                "reason": "观看一段时间",
            })
        elif mode == "search":
            suggestions.append({
                "action": "open_video",
                "reason": "在搜索结果页，打开视频",
            })

        return suggestions
