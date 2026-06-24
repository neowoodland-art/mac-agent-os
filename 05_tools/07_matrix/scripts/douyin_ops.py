#!/usr/bin/env python3
"""
抖音原子操作库 v2.0 — PlatformOps 接口实现
"""
import asyncio
import json
import random
import time
from pathlib import Path
from typing import Optional

from ops._base import PlatformOps, OpResult, Condition

# ════════════════════════════════════════════════════════════
# 持久化路径
# ════════════════════════════════════════════════════════════
_HOME = Path.home()
PROFILES_JSON = _HOME / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "data" / "profiles.json"

# ── 抖音 Web 选择器常量 ──────────────────────────────────────────
SELECTORS = {
    # 全局
    "search_input":         '[data-e2e="searchbar-input"]',
    "search_button":        '[data-e2e="searchbar-button"]',
    "nav_recommend":        '[data-e2e="douyin-navigation"] a:has-text("推荐")',
    "avatar":               '[data-e2e="live-avatar"]',

    # 视频互动
    "digg":                 '[data-e2e="video-player-digg"]',
    "comment_icon":         '[data-e2e="feed-comment-icon"]',
    "collect":              '[data-e2e="video-player-collect"]',
    "share":                '[data-e2e="video-player-share"]',
    "follow":               '[data-e2e="feed-follow-icon"]',
    "prev_arrow":           '[data-e2e="video-switch-prev-arrow"]',
    "next_arrow":           '[data-e2e="video-switch-next-arrow"]',
    "more":                 '[data-e2e="video-play-more"]',

    # 评论区
    "comment_list":         '[data-e2e="comment-list"]',
    "comment_editor":       '.public-DraftEditor-content',
    "comment_send":         '.commentInput-right-ct .WFB7wUOX',
    "comment_emoji":        '.commentInput-right-ct .BVMl8WNl',  # 第2个
    "comment_more":         '[data-e2e="video-comment-more"]',

    # 搜索结果
    "search_card":          '.search-result-card',
    "tab_active":           '.NiqGqBbw',
    "tab_inactive":         '.t3OsOj2N',
    "sub_filter":           '.neT9xRMd.vZeqhI2r',

    # 关注页
    "follow_user":          '.ILK2RAD5',

    # 个人主页
    "user_detail":          '[data-e2e="user-detail"]',
    "user_info":            '[data-e2e="user-info"]',
    "user_post_list":       '[data-e2e="user-post-list"]',

    # 头像悬停菜单
    "hover_menu":           '.userMenuPanelShadowAnimation',
    "hover_menu_item":      '.uz1VJwFY.espXX7re',

    # 验证码
    "verify_mask":          '.second-verify-mask',
    "verify_panel":         '.second-verify-panel',
    "verify_input":         '.uc-ui-verify_sms-verify_input',
    "verify_confirm":       '.uc-ui-verify_sms-verify_button.primary',
    "verify_cancel":        '.uc-ui-verify_sms-verify_button.second',
}

# 键盘快捷键
KEYS = {
    "like":       "z",
    "comment":    "x",
    "follow":     "g",
    "danmaku":    "b",
    "play_pause": "Space",
    "prev":       "ArrowUp",
    "next":       "ArrowDown",
    "enter":      "Enter",
}

# 起始 URL
HOME_URL = "https://www.douyin.com/"

# 频率安全阈值
RATE_LIMITS = {
    "likes_per_hour":    20,
    "comments_per_hour": 5,
    "follows_per_hour":  10,
    "collects_per_hour": 15,
    "searches_per_hour": 10,
}


class DouyinOps(PlatformOps):
    """抖音原子操作库 v2.0 — 实现 PlatformOps 接口"""

    name = "douyin"
    retry_count = 1

    def __init__(self, page, db=None, execution_id=None):
        self.page = page
        self.db = db
        self.execution_id = execution_id
        self._account_id = None
        self._action_counts = {
            "like": 0, "comment": 0, "follow": 0,
            "collect": 0, "search": 0,
        }
        self._session_start = time.time()

    def set_account_id(self, aid: str):
        print(f"[set_account_id] id(self)={id(self)}, aid={aid}")
        self._account_id = aid

    def _save_profiles_json(self):
        """保存主页信息到 profiles.json（供 Dashboard 读取）"""
        if not self._account_id:
            print(f"[douyin_ops] _save_profiles_json: _account_id 为空，跳过")
            return
        try:
            if PROFILES_JSON.exists():
                all_p = json.loads(PROFILES_JSON.read_text())
            else:
                all_p = {}
            prof = getattr(self, '_profile', {})
            PROFILES_JSON.parent.mkdir(parents=True, exist_ok=True)
            all_p[self._account_id] = {
                "nickname": prof.get("nickname", "?"),
                "user_id": prof.get("user_id", "?"),
                "following": prof.get("following", "?"),
                "fans": prof.get("fans", "?"),
                "likes": prof.get("likes", "?"),
                "posts": prof.get("posts", "?"),
                "bio": prof.get("bio", "?"),
                "platform": "douyin",
                "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            PROFILES_JSON.write_text(json.dumps(all_p, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"[douyin_ops] _save_profiles_json 失败: {e}")

    def supported_ops(self) -> list:
        return ["goto_home", "goto_url", "like", "collect", "follow",
                "open_comments", "close_comments", "post_comment",
                "next_video", "prev_video", "search", "wait_watch",
                "scroll_feed", "open_video", "wait", "go_back",
                "goto_profile", "read_profile_field", "read_my_comments",
                "reply_comment", "search_browse", "sms_login",
                "click_search_result",
                "dy_goto_profile",
                "dy_read_nickname", "dy_read_douyin_id",
                "dy_read_following", "dy_read_fans",
                "dy_read_likes", "dy_read_posts", "dy_read_bio"]

    # ── 三段式操作模型 v2.0 ──────────────────────────────────

    # 状态采集时检查的关键选择器
    STATE_SELECTORS = [
        '[data-e2e="video-player-digg"]',        # 点赞按钮
        '[data-e2e="video-player-collect"]',      # 收藏按钮
        '[data-e2e="feed-comment-icon"]',         # 评论图标
        '[data-e2e="feed-follow-icon"]',          # 关注按钮
        '[data-e2e="searchbar-input"]',           # 搜索框
        'video',                                   # 视频元素
    ]

    def _get_pre_conditions(self, op: str) -> list[Condition]:
        """每个操作的前置条件（三段式 v2.0）"""
        conds = {
            # ── 视频播放页操作 ──
            "like": [
                Condition("page_mode", "page_mode", "player", message="需要在视频播放页"),
                Condition("selector", '[data-e2e="video-player-digg"]', True,
                          message="需要点赞按钮可见"),
            ],
            "collect": [
                Condition("page_mode", "page_mode", "player", message="需要在视频播放页"),
                Condition("selector", '[data-e2e="video-player-collect"]', True,
                          message="需要收藏按钮可见"),
            ],
            "follow": [
                Condition("page_mode", "page_mode", "player", message="需要在视频播放页"),
                Condition("selector", '[data-e2e="feed-follow-icon"]', True,
                          message="需要关注按钮可见"),
            ],
            "open_comments": [
                Condition("page_mode", "page_mode", "player", message="需要在视频播放页"),
            ],
            "close_comments": [
                Condition("page_mode", "page_mode", "player", message="需要在视频播放页"),
            ],
            "next_video": [
                Condition("page_mode", "page_mode", "player", message="需要在视频播放页"),
            ],
            "prev_video": [
                Condition("page_mode", "page_mode", "player", message="需要在视频播放页"),
            ],
            "post_comment": [
                Condition("page_mode", "page_mode", "player", message="需要在视频播放页"),
            ],

            # ── Feed 流页操作 ──
            "scroll_feed": [
                Condition("page_mode", "page_mode", "grid", message="需要在 feed 流页"),
            ],
            "click_search_result": [
                Condition("page_mode", "page_mode", "search", message="需要在搜索结果页"),
            ],

            # ── 导航操作 ──
            "goto_home": [],
            "goto_url": [],
            "search": [
                Condition("selector", '[data-e2e="searchbar-input"]', True,
                          message="需要搜索框可见"),
            ],
            "open_video": [
                Condition("page_mode", "page_mode", "grid", message="需要在 feed 流页"),
            ],
            "search_browse": [
                Condition("selector", '[data-e2e="searchbar-input"]', True,
                          message="需要搜索框可见"),
            ],

            # ── 读操作（任何页面都能执行，失败不计）──
            "dy_read_nickname": [],
            "dy_read_douyin_id": [],
            "dy_read_following": [],
            "dy_read_fans": [],
            "dy_read_likes": [],
            "dy_read_posts": [],
            "dy_read_bio": [],

            # ── 无需条件的操作 ──
            "wait_watch": [],
            "wait": [],
            "go_back": [],
            "goto_profile": [],
            "read_profile_field": [],
            "read_my_comments": [],
            "reply_comment": [],
            "sms_login": [],
        }
        return conds.get(op, [])

    def _get_post_conditions(self, op: str) -> list[Condition]:
        """每个操作的后置验证条件（三段式 v2.0）"""
        conds = {
            "like": [
                Condition("selector", '[data-e2e="video-player-digg"]', True,
                          message="点赞按钮应仍在页面"),
            ],
            "goto_home": [
                Condition("page_mode", "page_mode", "grid",
                          message="应回到 feed 首页"),
            ],
            "search": [
                Condition("selector", '[data-e2e="searchbar-input"]', True,
                          message="搜索框应仍可见"),
            ],
        }
        return conds.get(op, [])

    async def _do_execute(self, op: str, args: dict, step_id: int) -> Optional[OpResult]:
        """实现 PlatformOps._do_execute — 操作分发"""
        t0 = time.time()

        if op == "goto_home":
            await self.page.goto(HOME_URL, timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            return OpResult(op, step_id, True, "home", time.time()-t0)

        if op == "goto_url":
            url = args.get("url", HOME_URL)
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(5)
            return OpResult(op, step_id, True, f"goto {url[:30]}", time.time()-t0)

        if op == "like":
            ok = await self.like(step_id=step_id, probability=args.get("probability", 1.0))
            if not ok:
                # KeyZ fallback
                video = self.page.locator('video')
                if await video.count() > 0:
                    box = await video.first.bounding_box()
                    if box:
                        await self.page.mouse.click(box['x']+box['width']//2, box['y']+box['height']//3)
                        await asyncio.sleep(0.5)
                await self.page.keyboard.press("z")
                await asyncio.sleep(1.5)
                ok = await self.like(step_id=step_id)
            return OpResult(op, step_id, ok, "👍" if ok else "-", time.time()-t0)

        if op == "collect":
            ok = await self.collect(step_id=step_id)
            return OpResult(op, step_id, ok, "⭐" if ok else "-", time.time()-t0)

        if op == "follow":
            ok = await self.follow(step_id=step_id)
            return OpResult(op, step_id, ok, "➕" if ok else "-", time.time()-t0)

        if op == "open_comments":
            state = await self._detect_page_state()
            # 只检查 player 相关状态
            if state not in ('player', 'player_full', 'player_modal'):
                # 不在播放页 → 无法打开评论区
                return OpResult(op, step_id, False, f"not_player({state})", time.time()-t0)
            # x 键打开（旧版成功的方法）
            ok = await self.open_comments(step_id=step_id)
            await asyncio.sleep(3)
            return OpResult(op, step_id, ok, "opened" if ok else "not_found", time.time()-t0)

        if op == "post_comment":
            text = args.get("text", "太棒了")
            ok = await self.post_comment(text, step_id=step_id)
            return OpResult(op, step_id, ok, "sent" if ok else "fail", time.time()-t0)

        if op == "close_comments":
            page_url = self.page.url
            is_full = "/video/" in page_url and "modal_id" not in page_url
            if is_full:
                await self.page.evaluate("() => window.scrollTo(0, 0)")
            else:
                await self.page.keyboard.press("Escape")
            await asyncio.sleep(1)
            return OpResult(op, step_id, True, "closed", time.time()-t0)

        if op == "next_video":
            ok = await self.next_video(step_id=step_id)
            return OpResult(op, step_id, ok, "⬇️" if ok else "-", time.time()-t0)

        if op == "prev_video":
            await self.page.keyboard.press("ArrowUp")
            await asyncio.sleep(2)
            return OpResult(op, step_id, True, "⬆️", time.time()-t0)

        if op == "search":
            kw = args.get("keyword", "热门推荐")
            if kw == "@random":
                import random as _r
                kw = _r.choice(["穿搭推荐","美食日常","旅行攻略","电影解说","科技数码",
                                "宠物搞笑","健身教程","音乐推荐","美妆教程","家居好物"])
            ok = await self.search(kw, step_id=step_id)
            return OpResult(op, step_id, ok, f"{kw[:10]}", time.time()-t0)

        if op == "wait_watch":
            seconds = args.get("seconds", random.randint(5, 12))
            await self.wait_watch(seconds=seconds, step_id=step_id)
            return OpResult(op, step_id, True, f"{seconds}s", time.time()-t0)

        if op == "scroll_feed":
            await self.page.evaluate("() => window.scrollBy(0, 600)")
            await asyncio.sleep(1)
            return OpResult(op, step_id, True, "scroll", time.time()-t0)

        if op == "open_video":
            """进入视频播放页"""
            t0 = time.time()
            # 先查：已在播放页则跳过
            if await self.page.locator('video').count() > 0:
                await self._ensure_video_focused()
                return OpResult(op, step_id, True, "already_player", time.time()-t0)
            
            # 导航到首页
            await self.page.goto("https://www.douyin.com/?recommend=1", timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(4)
            
            # 找卡片双击
            for attempt in range(3):
                card = self.page.locator('.discover-video-card-item, a[href*="/video/"], [class*="video-card"]').first
                for _ in range(10):
                    if await card.count() > 0:
                        break
                    await asyncio.sleep(1)
                    card = self.page.locator('.discover-video-card-item, a[href*="/video/"], [class*="video-card"]').first
                if await card.count() == 0:
                    continue
                await card.click()
                await asyncio.sleep(1)
                await card.click()
                await asyncio.sleep(3)
                if await self.page.locator('video').count() > 0:
                    await self._ensure_video_focused()
                    return OpResult(op, step_id, True, "video_detail", time.time()-t0)
                await self.page.goto("https://www.douyin.com/?recommend=1", timeout=15000, wait_until="domcontentloaded")
                await asyncio.sleep(3)
            return OpResult(op, step_id, False, "no_card", time.time()-t0)

        if op == "wait":
            await asyncio.sleep(args.get("seconds", 2))
            return OpResult(op, step_id, True, f"{args.get('seconds',2)}s", time.time()-t0)

        if op == "go_back":
            await self.page.go_back()
            await asyncio.sleep(2)
            return OpResult(op, step_id, True, "back", time.time()-t0)

        if op == "goto_profile":
            d = await self.goto_profile(step_id=step_id)
            return OpResult(op, step_id, True, d.get("nickname","ok"), time.time()-t0)

        if op == "read_profile_field":
            v = await self.read_profile_field(args.get("field","nickname"), step_id=step_id)
            return OpResult(op, step_id, True, str(v)[:20], time.time()-t0)

        if op == "read_my_comments":
            c = await self.read_my_comments(step_id=step_id)
            return OpResult(op, step_id, True, f"{len(c)}条", time.time()-t0)

        if op == "reply_comment":
            ok = await self.reply_comment(args.get("text","谢谢支持"), step_id=step_id)
            return OpResult(op, step_id, ok, "replied" if ok else "no_btn", time.time()-t0)

        if op == "search_browse":
            kw = args.get("keyword", "热门推荐")
            await self.search(kw, step_id=step_id)
            await self.click_search_result(step_id=step_id)
            await self.wait_watch(seconds=random.randint(5, 12), step_id=step_id)
            import random as _rnd
            if _rnd.random() < 0.6: await self.like(step_id=step_id)
            if _rnd.random() < 0.2: await self.collect(step_id=step_id)
            return OpResult(op, step_id, True, "searched+browsed", time.time()-t0)

        if op == "click_search_result":
            index = args.get("index", 0)
            ok = await self.click_search_result(index=index, step_id=step_id)
            return OpResult(op, step_id, ok, "clicked" if ok else "no_result", time.time()-t0)

        # dy_* 系列操作（read_profile 蓝图用）
        if op == "dy_goto_profile":
            await self.page.goto("https://www.douyin.com/user/self", timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(5)
            return OpResult(op, step_id, True, "profile", time.time()-t0)

        if op.startswith("dy_read_"):
            field_map = {
                "dy_read_nickname": "nickname",
                "dy_read_douyin_id": "user_id",
                "dy_read_following": "following",
                "dy_read_fans": "fans",
                "dy_read_likes": "likes",
                "dy_read_posts": "posts",
                "dy_read_bio": "bio",
            }
            field = field_map.get(op, op.replace("dy_read_", ""))
            val = await self.read_profile_field(field, step_id=step_id)
            # dy_read_bio 是最后一步，读完后保存 profiles.json
            if op == "dy_read_bio":
                print(f"[dy_read_bio] id(self)={id(self)}, _account_id={self._account_id}, _profile keys={list((self._profile or {}).keys())}")
                self._save_profiles_json()
            return OpResult(op, step_id, True, f"{field}={val}", time.time()-t0)

        return OpResult(op, step_id, False, f"unknown_op:{op}", time.time()-t0)
        self.account_id = ""
        self._profile = {}
        self._last_comments = []

    def set_account_id(self, aid: str):
        self._account_id = aid

    # ── 内部工具 ──────────────────────────────────────────────

    def _elapsed_hours(self) -> float:
        return (time.time() - self._session_start) / 3600

    def _check_rate(self, action: str) -> bool:
        key = f"{action}s_per_hour"
        limit = RATE_LIMITS.get(key, 999)
        rate = self._action_counts.get(action, 0) / max(self._elapsed_hours(), 0.01)
        return rate < limit

    async def _log_op(self, step_id: int, op_name: str, locator: str,
                      success: bool, duration_ms: int, error: str = ""):
        """记录操作日志到数据库"""
        if not self.db:
            return
        import uuid
        self.db.execute("""
            INSERT INTO operation_logs
            (id, execution_id, step_id, atomic_operation, execution_success,
             locator_used, duration_ms, error_detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            str(uuid.uuid4()), self.execution_id, step_id, op_name,
            1 if success else 0, locator, duration_ms, error
        ))
        self.db.commit()

    async def _wait(self, base: float, jitter: float = 0):
        """带随机抖动的等待"""
        await asyncio.sleep(base + random.uniform(-jitter, jitter))

    async def _click_selector(self, selector: str, timeout: int = 5000) -> bool:
        """安全点击选择器 — 先用 Playwright 原生点击，失败后 JS 兜底"""
        try:
            # 策略1: Playwright 原生点击（实时鼠标事件）
            el = self.page.locator(selector)
            if await el.count() > 0:
                await el.first.click(timeout=timeout)
                return True
        except Exception:
            pass
        # 策略2: JS click 兜底（绕过可见性检查）
        try:
            clicked = await self.page.evaluate(f"""() => {{
                var el = document.querySelector('{selector.replace("'", "\\'")}');
                if (el) {{ el.click(); return true; }}
                return false;
            }}""")
            return clicked
        except Exception:
            pass
        return False

    async def _ensure_video_focused(self):
        """确保焦点在视频区域"""
        video = self.page.locator('video')
        if await video.count() > 0:
            box = await video.first.bounding_box()
            if box:
                await self.page.mouse.click(
                    box['x'] + box['width'] // 2,
                    box['y'] + box['height'] // 3
                )
                await asyncio.sleep(0.2)

    # ── 状态检测 ──────────────────────────────────────────────

    async def _detect_page_state(self) -> str:
        """检测当前页面状态（参考旧版 _detect_page_state + _check_anchor）
        
        Returns:
            'grid' — 首页feed（有卡片列表）
            'player_modal' — 弹窗播放（jingxuan?modal_id=xxx）
            'player_full' — 独立播放页（/video/xxx）
            'search' — 搜索页
            'profile' — 个人主页
            'unknown' — 未知
        """
        try:
            url = self.page.url
            vc = await self.page.evaluate("document.querySelectorAll('video').length")
            cards = await self.page.evaluate(
                "document.querySelectorAll('.discover-video-card-item, [class*=\"video-card\"], "
                "[data-e2e=\"alink-item\"]').length"
            )
            has_search = '/search/' in url
            
            if vc > 0 and '/video/' in url:
                return 'player_full'
            if vc > 0 and 'modal_id' in url:
                return 'player_modal'
            if vc > 0:
                return 'player'
            if has_search:
                return 'search'
            if '/user/' in url:
                return 'profile'
            if cards > 0 or '/jingxuan' in url:
                return 'grid'
            return 'unknown'
        except:
            return 'unknown'

    async def _check_anchor(self, anchor_type: str, timeout: float = 3.0) -> bool:
        """检测页面锚点（参考旧版 _check_anchor）"""
        try:
            import asyncio
            if anchor_type == 'video_page':
                vc = await asyncio.wait_for(
                    self.page.evaluate("document.querySelectorAll('video').length"),
                    timeout=timeout
                )
                return vc > 0
            elif anchor_type == 'home_page':
                has_cards = await asyncio.wait_for(
                    self.page.evaluate(
                        "document.querySelectorAll('.discover-video-card-item, "
                        "[class*=\"video-card\"]').length > 0"
                    ), timeout=timeout
                )
                return has_cards
            elif anchor_type == 'has_videos':
                links = await asyncio.wait_for(
                    self.page.evaluate(
                        "document.querySelectorAll('a[href*=\"/video/\"], "
                        "[href*=\"modal_id\"]').length > 0"
                    ), timeout=timeout
                )
                return links
        except:
            pass
        return False

    async def goto_home(self, step_id: int = 0) -> bool:
        """AO_NAV: 回到推荐页（固定起点）"""
        t0 = time.time()
        try:
            await self.page.goto(HOME_URL, wait_until='domcontentloaded')
            await self._wait(2)

            # 检查是否在精选页（无视频feed），点击推荐导航
            video = self.page.locator('video')
            if await video.count() == 0 or not await self.page.evaluate(
                '() => { const v = document.querySelector("video"); return v && v.duration > 0; }'
            ):
                rec = self.page.locator(SELECTORS['nav_recommend'])
                if await rec.count() > 0:
                    await rec.first.click()
                    await self._wait(3)

            # 等待视频加载
            for _ in range(15):
                if await self.page.evaluate(
                    '() => { const v = document.querySelector("video"); return v && v.duration > 0 && v.readyState >= 2; }'
                ):
                    dur = int((time.time() - t0) * 1000)
                    await self._log_op(step_id, "AO_NAV", HOME_URL, True, dur)
                    return True
                await asyncio.sleep(1)

            await self._log_op(step_id, "AO_NAV", HOME_URL, False, int((time.time()-t0)*1000), "视频加载超时")
            return False
        except Exception as e:
            await self._log_op(step_id, "AO_NAV", HOME_URL, False, int((time.time()-t0)*1000), str(e))
            return False

    async def goto_url(self, url: str, step_id: int = 0) -> bool:
        """AO_NAV: 导航到指定URL"""
        t0 = time.time()
        try:
            await self.page.goto(url, wait_until='domcontentloaded')
            await self._wait(2)
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_NAV", url, True, dur)
            return True
        except Exception as e:
            await self._log_op(step_id, "AO_NAV", url, False, int((time.time()-t0)*1000), str(e))
            return False

    async def go_back(self, step_id: int = 0) -> bool:
        """AO_NAV: 浏览器后退"""
        t0 = time.time()
        try:
            await self.page.go_back()
            await self._wait(1.5)
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_NAV", "go_back", True, dur)
            return True
        except Exception as e:
            await self._log_op(step_id, "AO_NAV", "go_back", False, int((time.time()-t0)*1000), str(e))
            return False

    # ── 互动类原子操作 ──────────────────────────────────────────

    async def like(self, step_id: int = 0, probability: float = 1.0) -> bool:
        """AO_LIKE: 点赞当前视频 — 键盘 z + DOM 双击兜底
        probability: 概率控制，0-1之间，默认1.0（必定执行）
        """
        if not self._check_rate("like"):
            return True
        if probability < 1.0 and random.random() > probability:
            return True
        t0 = time.time()
        try:
            # 策略1: 键盘 Z（抖音 feed 流/详情页通用）
            await self._ensure_video_focused()
            await self.page.keyboard.press(KEYS['like'])
            await self._wait(0.5 + random.uniform(0, 1))
            self._action_counts["like"] += 1
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_LIKE", "keyboard_z", True, dur)
            return True
        except Exception as e:
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_LIKE", "keyboard_z", False, dur, str(e))
            return False

    async def collect(self, step_id: int = 0, probability: float = 1.0) -> bool:
        """AO_COLLECT: 收藏当前视频（DOM+JS+坐标3层兜底）"""
        if not self._check_rate("collect"):
            return True
        if probability < 1.0 and random.random() > probability:
            return True
        t0 = time.time()
        # 策略1: DOM选择器
        selector = SELECTORS['collect']
        try:
            ok = await self._click_selector(selector)
            if ok:
                self._action_counts["collect"] += 1
                await self._wait(0.5 + random.uniform(0, 1))
                dur = int((time.time() - t0) * 1000)
                await self._log_op(step_id, "AO_COLLECT", selector, True, dur)
                return True
        except:
            pass
        # 策略2: JS找包含"收藏"文字或collect/save类名的元素
        try:
            clicked = await self.page.evaluate("""() => {
                const all = document.querySelectorAll('button, span, div, [class*="collect"], [class*="save"]');
                for (const el of all) {
                    const t = el.textContent || '';
                    const c = el.className || '';
                    if ((t.includes('收藏') || c.includes('collect') || c.includes('save')) && el.offsetParent) {
                        el.click(); return true;
                    }
                }
                return false;
            }""")
            if clicked:
                self._action_counts["collect"] += 1
                dur = int((time.time() - t0) * 1000)
                await self._log_op(step_id, "AO_COLLECT", "js_search", True, dur)
                return True
        except:
            pass
        # 策略3: 坐标兜底（点赞右边70px）
        try:
            like = self.page.locator('[data-e2e="video-player-digg"]')
            if await like.count() > 0:
                box = await like.first.bounding_box()
                if box:
                    await self.page.mouse.click(box['x'] + 70, box['y'])
                    await self._wait(0.5)
                    self._action_counts["collect"] += 1
                    dur = int((time.time() - t0) * 1000)
                    await self._log_op(step_id, "AO_COLLECT", "coordinate", True, dur)
                    return True
        except:
            pass
        return False

    async def follow(self, step_id: int = 0) -> bool:
        """AO_FOLLOW: 关注当前视频作者（DOM点击+键盘g兜底）"""
        if not self._check_rate("follow"):
            return True
        t0 = time.time()
        # 策略1: DOM点击
        selector = SELECTORS['follow']
        try:
            ok = await self._click_selector(selector)
            if ok:
                self._action_counts["follow"] += 1
                await self._wait(1 + random.uniform(0, 1))
                dur = int((time.time() - t0) * 1000)
                await self._log_op(step_id, "AO_FOLLOW", selector, True, dur)
                return True
        except:
            pass
        # 策略2: 键盘 g（录制发现用户用 g 键关注）
        try:
            await self._ensure_video_focused()
            await self.page.keyboard.press(KEYS['follow'])
            await self._wait(1 + random.uniform(0, 1))
            self._action_counts["follow"] += 1
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_FOLLOW", "keyboard_g", True, dur)
            return True
        except Exception as e:
            await self._log_op(step_id, "AO_FOLLOW", selector, False, int((time.time()-t0)*1000), str(e))
            return False

    async def next_video(self, step_id: int = 0) -> bool:
        """AO_SWIPE: 下翻到下一个视频"""
        t0 = time.time()
        selector = SELECTORS['next_arrow']
        try:
            # 优先点击箭头（比键盘更可靠）
            ok = await self._click_selector(selector)
            if not ok:
                # fallback: 键盘
                await self._ensure_video_focused()
                await self.page.keyboard.press(KEYS['next'])
            await self._wait(2 + random.uniform(0, 1))
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_SWIPE", selector, True, dur)
            return True
        except Exception as e:
            await self._log_op(step_id, "AO_SWIPE", selector, False, int((time.time()-t0)*1000), str(e))
            return False

    async def prev_video(self, step_id: int = 0) -> bool:
        """AO_SWIPE: 上翻到上一个视频"""
        t0 = time.time()
        selector = SELECTORS['prev_arrow']
        try:
            ok = await self._click_selector(selector)
            if not ok:
                await self._ensure_video_focused()
                await self.page.keyboard.press(KEYS['prev'])
            await self._wait(2 + random.uniform(0, 1))
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_SWIPE", selector, True, dur)
            return True
        except Exception as e:
            await self._log_op(step_id, "AO_SWIPE", selector, False, int((time.time()-t0)*1000), str(e))
            return False

    async def toggle_play(self, step_id: int = 0) -> bool:
        """播放/暂停切换"""
        t0 = time.time()
        try:
            await self._ensure_video_focused()
            await self.page.keyboard.press(KEYS['play_pause'])
            await self._wait(0.5)
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_CLICK", "keyboard:Space", True, dur)
            return True
        except Exception as e:
            await self._log_op(step_id, "AO_CLICK", "keyboard:Space", False, int((time.time()-t0)*1000), str(e))
            return False

    # ── 搜索类原子操作 ──────────────────────────────────────────

    async def search(self, keyword: str, step_id: int = 0) -> bool:
        """AO_SEARCH: 搜索关键词"""
        if not self._check_rate("search"):
            return True
        t0 = time.time()
        selector = SELECTORS['search_input']
        try:
            el = self.page.locator(selector)
            if await el.count() == 0:
                dur = int((time.time() - t0) * 1000)
                await self._log_op(step_id, "AO_SEARCH", selector, False, dur, "搜索框未找到")
                return False

            await el.click()
            await self._wait(0.3)
            await el.fill('')
            await el.press_sequentially(keyword, delay=random.uniform(60, 120))
            await self._wait(0.3)
            await el.press('Enter')
            self._action_counts["search"] += 1
            await self._wait(3)

            # 验证：URL 包含 search
            url = self.page.url
            ok = 'search' in url
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_SEARCH", f"{selector}:{keyword}", ok, dur)
            return ok
        except Exception as e:
            await self._log_op(step_id, "AO_SEARCH", selector, False, int((time.time()-t0)*1000), str(e))
            return False

    async def click_search_result(self, index: int = 0, step_id: int = 0) -> bool:
        """AO_CLICK: 点击第N个搜索结果（0-indexed）"""
        t0 = time.time()
        selector = SELECTORS['search_card']
        try:
            cards = self.page.locator(selector)
            count = await cards.count()
            if index >= count:
                dur = int((time.time() - t0) * 1000)
                await self._log_op(step_id, "AO_CLICK", selector, False, dur, f"只有{count}个结果，第{index+1}个不存在")
                return False

            await cards.nth(index).click()
            await self._wait(3)

            # 验证：URL 包含 modal_id
            url = self.page.url
            ok = 'modal_id' in url
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_CLICK", f"{selector}[{index}]", ok, dur)
            return ok
        except Exception as e:
            await self._log_op(step_id, "AO_CLICK", selector, False, int((time.time()-t0)*1000), str(e))
            return False

    # ── 评论类原子操作 ──────────────────────────────────────────

    async def open_comments(self, step_id: int = 0) -> bool:
        """打开评论区"""
        t0 = time.time()
        try:
            await self._ensure_video_focused()
            await self.page.keyboard.press(KEYS['comment'])
            await self._wait(1.5)

            # 验证评论列表出现
            ok = await self.page.locator(SELECTORS['comment_list']).count() > 0
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_CLICK", "keyboard:x", ok, dur)
            return ok
        except Exception as e:
            await self._log_op(step_id, "AO_CLICK", "keyboard:x", False, int((time.time()-t0)*1000), str(e))
            return False

    async def close_comments(self, step_id: int = 0) -> bool:
        """关闭评论区"""
        t0 = time.time()
        try:
            await self._ensure_video_focused()
            await self.page.keyboard.press(KEYS['comment'])
            await self._wait(1)
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_CLICK", "keyboard:x", True, dur)
            return True
        except Exception as e:
            await self._log_op(step_id, "AO_CLICK", "keyboard:x", False, int((time.time()-t0)*1000), str(e))
            return False

    async def post_comment(self, text: str, step_id: int = 0) -> str:
        """AO_COMMENT: 发表评论。返回 'ok' / 'verify_needed' / 'failed'"""
        if not self._check_rate("comment"):
            return 'ok'
        t0 = time.time()
        try:
            # 1. 确保评论区打开
            if await self.page.locator(SELECTORS['comment_list']).count() == 0:
                await self.open_comments(step_id)
                await self._wait(1.5)

            # 2. 点击输入框
            editor = self.page.locator(SELECTORS['comment_editor'])
            if await editor.count() == 0:
                dur = int((time.time() - t0) * 1000)
                await self._log_op(step_id, "AO_COMMENT", SELECTORS['comment_editor'], False, dur, "评论输入框未找到")
                return 'failed'

            await editor.click()
            await self._wait(0.5)

            # 3. 输入评论（Draft.js 编辑器）
            await editor.press_sequentially(text, delay=random.uniform(50, 100))
            await self._wait(0.3 + random.uniform(0, 0.5))

            # 4. 发送（先找发送按钮，失败则Enter）
            sent = False
            for attempt in range(3):
                send_btn = await self.page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button, [class*="send"], [class*="submit"]'));
                    const btn = btns.find(b =>
                        (b.textContent || '').includes('发送')
                        || (b.textContent || '').includes('发布')
                        || b.className.includes('send')
                        || b.className.includes('submit')
                        || (b.querySelector('svg') && b.className.includes('arrow'))
                    );
                    if (btn) { btn.click(); return true; }
                    return false;
                }""")
                if send_btn:
                    sent = True
                    break
                await self.page.keyboard.press('Enter')
                await self._wait(1)
                # 验证：评论是否出现在列表
                appeared = await self.page.evaluate(
                    f"() => {{ const l = document.querySelector('[data-e2e=\"comment-list\"]'); return l ? l.textContent.includes('{text[:10]}') : false; }}"
                )
                if appeared:
                    sent = True
                    break
                await self._wait(1)
            
            if not sent:
                dur = int((time.time() - t0) * 1000)
                await self._log_op(step_id, "AO_COMMENT", "send_fallback", False, dur, "所有发送方式均失败")
                return 'failed'
            
            self._action_counts["comment"] += 1
            await self._wait(1.5)

            # 5. 检查验证码
            if await self.page.locator(SELECTORS['verify_panel']).count() > 0:
                dur = int((time.time() - t0) * 1000)
                await self._log_op(step_id, "AO_COMMENT", SELECTORS['comment_editor'], True, dur, "触发验证码")
                return 'verify_needed'

            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_COMMENT", f"{SELECTORS['comment_editor']}:{text[:20]}", True, dur)
            return 'ok'
        except Exception as e:
            await self._log_op(step_id, "AO_COMMENT", SELECTORS['comment_editor'], False, int((time.time()-t0)*1000), str(e))
            return 'failed'

    async def cancel_verify(self, step_id: int = 0) -> bool:
        """取消验证码弹窗"""
        t0 = time.time()
        selector = SELECTORS['verify_cancel']
        try:
            ok = await self._click_selector(selector)
            await self._wait(1)
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_CLICK", selector, ok, dur)
            return ok
        except Exception as e:
            await self._log_op(step_id, "AO_CLICK", selector, False, int((time.time()-t0)*1000), str(e))
            return False

    # ── 等待类原子操作 ──────────────────────────────────────────

    async def wait_watch(self, seconds: float = None, step_id: int = 0) -> bool:
        """AO_WAIT: 模拟观看视频，随机 5-30 秒"""
        if seconds is None:
            seconds = random.uniform(5, 30)
        t0 = time.time()
        await asyncio.sleep(seconds)
        dur = int((time.time() - t0) * 1000)
        await self._log_op(step_id, "AO_WAIT", f"{seconds:.1f}s", True, dur)
        return True

    # ── 状态查询 ──────────────────────────────────────────────

    async def get_state(self) -> dict:
        """获取当前页面状态快照"""
        return await self.page.evaluate('''() => {
            const v = document.querySelector('video');
            const d = document.querySelector('[data-e2e="video-player-digg"]');
            return {
                url: location.href,
                title: document.title,
                video: v ? {
                    paused: v.paused,
                    currentTime: Math.round(v.currentTime),
                    duration: Math.round(v.duration) || 0
                } : null,
                digg_state: d ? d.getAttribute('data-e2e-state') : null,
            };
        }''')

    async def is_on_feed(self) -> bool:
        """是否在视频 Feed 页"""
        return await self.page.locator('video').count() > 0

    async def is_on_search(self) -> bool:
        """是否在搜索结果页"""
        return 'search' in self.page.url

    async def is_verify_shown(self) -> bool:
        """是否弹出了验证码"""
        return await self.page.locator(SELECTORS['verify_panel']).count() > 0

    # ═══════════════════════════════════════════════════════════
    # 个人主页 & 信息采集
    # ═══════════════════════════════════════════════════════════

    async def goto_profile(self, step_id: int = 0) -> dict:
        """AO_PROFILE: 进入个人主页，一次性采集全部字段"""
        t0 = time.time()
        await self.page.goto("https://www.douyin.com/user/self", timeout=20000, wait_until="domcontentloaded")
        await asyncio.sleep(5)
        profile = await self.page.evaluate("""() => {
            const text = (document.body.innerText || '').trim();
            const title = (document.title || '').replace(' - 抖音', '').replace('的抖音', '').trim();
            const uidM = text.match(/抖音号[：:]\\s*(\\S+)/);
            const folM = text.match(/(\\d+(?:\\.\\d+)?[万w]?)\\s*关注/);
            const fanM = text.match(/(\\d+(?:\\.\\d+)?[万w]?)\\s*粉丝/);
            const likM = text.match(/(\\d+(?:\\.\\d+)?[万w]?)\\s*获赞/);
            const posM = text.match(/作品\\s*(\\d+)/);
            function e2e(s) { const el = document.querySelector('[data-e2e="'+s+'"]'); return el ? (el.textContent||'').trim() : ''; }
            return {
                nickname: title, user_id: uidM ? uidM[1] : '?',
                following: folM ? folM[1] : (e2e('user-info-follow')||'?'),
                fans: fanM ? fanM[1] : (e2e('user-info-fans')||'?'),
                likes: likM ? likM[1] : (e2e('user-info-like')||'?'),
                posts: posM ? posM[1] : (e2e('user-tab-count')||'?'),
                bio: (e2e('user-bio') || '?').slice(0, 50),
            };
        }""")
        self._profile = profile
        self._save_profiles_json()  # ← 写入 profiles.json
        dur = int((time.time() - t0) * 1000)
        await self._log_op(step_id, "AO_PROFILE", "user/self", True, dur)
        return profile

    async def read_profile_field(self, field: str, step_id: int = 0) -> str:
        """AO_PROFILE: 从已缓存的 profile 读取单个字段"""
        if not hasattr(self, '_profile') or not self._profile:
            await self.goto_profile(step_id)
        return self._profile.get(field, '?')

    # ═══════════════════════════════════════════════════════════
    # 评论区互动
    # ═══════════════════════════════════════════════════════════

    async def read_my_comments(self, step_id: int = 0) -> list[dict]:
        """AO_COMMENT: 读取当前视频的评论区，返回评论列表"""
        t0 = time.time()
        await self.open_comments(step_id)
        await asyncio.sleep(2)
        comments = await self.page.evaluate("""() => {
            const items = document.querySelectorAll('[class*="comment-item"], [class*="CommentItem"]');
            return Array.from(items).slice(0, 20).map(el => {
                const textEl = el.querySelector('[class*="text"], [class*="content"]');
                const nameEl = el.querySelector('[class*="name"], [class*="author"]');
                return {
                    text: textEl ? textEl.textContent.trim().slice(0, 200) : '',
                    author: nameEl ? nameEl.textContent.trim() : '',
                };
            });
        }""")
        self._last_comments = comments
        dur = int((time.time() - t0) * 1000)
        await self._log_op(step_id, "AO_READ_COMMENTS", "comment-item", True, dur)
        return comments

    async def reply_comment(self, reply_text: str, step_id: int = 0) -> bool:
        """AO_COMMENT: 回复当前评论区的第一条评论"""
        t0 = time.time()
        if not await self.page.locator(SELECTORS['comment_list']).count() > 0:
            await self.open_comments(step_id)
            await asyncio.sleep(2)
        # 点击回复按钮
        reply_btn = await self.page.evaluate("""() => {
            const btns = document.querySelectorAll('[class*="reply"], [class*="Reply"]');
            for (const b of btns) {
                if (b.offsetParent !== null) { b.click(); return true; }
            }
            return false;
        }""")
        await asyncio.sleep(1)
        # pbcopy + Meta+V 发送回复
        if reply_btn:
            proc = await asyncio.create_subprocess_exec("pbcopy", stdin=asyncio.subprocess.PIPE)
            await proc.communicate(input=reply_text.encode())
            await asyncio.sleep(0.5)
            await self.page.keyboard.press("Meta+V")
            await asyncio.sleep(1)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(2)
        dur = int((time.time() - t0) * 1000)
        await self._log_op(step_id, "AO_REPLY", "reply", reply_btn, dur)
        return reply_btn

    async def sms_login(self, phone: str = "", step_id: int = 0) -> bool:
        """抖音 SMS 验证码登录（处理 passport iframe 登录页）
        
        Args:
            phone: 手机号，为空则从账号配置读取
        Returns:
            True=登录成功
        """
        page = self.page
        log = lambda msg: None  # 静默日志，出错时打印

        # 1. 检查是否已在登录页，不在则导航过去
        if "passport" not in page.url.lower() and "login" not in page.url.lower():
            log("导航到抖音登录页...")
            await page.goto("https://www.douyin.com/passport/sso/login/", 
                          wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)

        # 2. 查找登录 iframe（抖音护照登录页在 iframe 内）
        login_frame = None
        for attempt in range(5):
            frames = page.frames
            for f in frames:
                url = f.url.lower()
                if "passport" in url or "login" in url or "sso" in url:
                    login_frame = f
                    break
            if login_frame:
                break
            await asyncio.sleep(2)

        if not login_frame:
            print("❌ 未找到登录 iframe，尝试直接页面操作...")
            login_frame = page  # fallback

        # 3. 等待登录页面完全渲染
        await asyncio.sleep(3)

        # 4. 检测当前登录模式（二维码 vs 手机号）
        qr_visible = False
        try:
            qr = await login_frame.query_selector("div[class*=qrcode], img[class*=qrcode], canvas[class*=qrcode]")
            if qr:
                qr_visible = True
                print("⚠️ 检测到二维码登录，尝试切换到手机号登录")
        except:
            pass

        # 5. 如果有二维码，找"手机号登录"标签并点击
        if qr_visible:
            for text in ["手机号登录", "手机登录", "短信登录", "验证码登录"]:
                try:
                    tab = await login_frame.query_selector(f"div:has-text('{text}'), span:has-text('{text}'), label:has-text('{text}')")
                    if tab and await tab.is_visible():
                        await tab.click()
                        await asyncio.sleep(2)
                        print(f"  ✅ 切换到 {text}")
                        break
                except:
                    continue

        # 6. 找手机号输入框并填入
        phone_filled = False
        phone_value = phone
        if not phone_value:
            # 从账号配置查
            try:
                from matrix_mgmt import MatrixManager
                mgr = MatrixManager()
                for a in mgr.list_accounts():
                    if a["id"] == self._account_id:
                        phone_value = a.get("phone", "")
                        break
            except:
                pass

        if not phone_value:
            from matrix_modules.account.sms import ApiSMSHandler
            handler = ApiSMSHandler()
            phone_value = handler.get_phone()
            if phone_value:
                phone_value = str(phone_value)

        print(f"  手机号: {phone_value or '默认'}")

        # 尝试在 iframe 里找手机号输入框
        phone_sel = "input[placeholder*='手机'], input[type='tel'], input[name='mobile'], input[id*='phone'], input[id*='mobile']"
        for sel in [phone_sel, "input:first-of-type"]:
            try:
                inp = await login_frame.query_selector(sel)
                if inp:
                    await inp.click()
                    await asyncio.sleep(0.5)
                    await inp.fill(phone_value or "18912345678")
                    await asyncio.sleep(1)
                    phone_filled = True
                    print(f"  ✅ 已填手机号: {phone_value or '默认'}")
                    break
            except:
                continue

        if not phone_filled:
            # fallback: 填第一个可见 input
            try:
                inputs = await login_frame.query_selector_all("input:visible")
                if inputs and len(inputs) > 0:
                    await inputs[0].click()
                    await inputs[0].fill(phone_value or "18912345678")
                    await asyncio.sleep(1)
                    phone_filled = True
            except:
                pass

        if not phone_filled:
            print("❌ 未找到手机号输入框")
            return False

        # 7. 点"获取验证码"按钮
        code_sent = False
        for text in ["获取验证码", "发送验证码", "获取"]:
            try:
                btn = await login_frame.query_selector(f"button:has-text('{text}'), span:has-text('{text}'), div:has-text('{text}')")
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(2)
                    code_sent = True
                    print(f"  ✅ 点击 '{text}'")
                    break
            except:
                continue

        if not code_sent:
            # fallback: 点最后一个 button
            try:
                btns = await login_frame.query_selector_all("button")
                if btns and len(btns) > 0:
                    await btns[-1].click()
                    await asyncio.sleep(2)
                    code_sent = True
            except:
                pass

        # 8. 轮询 SMS 验证码
        from matrix_modules.account.sms import ApiSMSHandler
        handler = ApiSMSHandler(phone=phone_value) if phone_value else ApiSMSHandler()
        code = ""
        for retry in range(6):  # 最多等 60s
            await asyncio.sleep(10)
            try:
                code = await handler.wait("抖音登录", timeout=5)
                if code and len(code) in (4, 5, 6):
                    print(f"  ✅ 获取到验证码: {code}")
                    break
            except:
                continue
            if retry == 3:
                print("  ⏳ 重发验证码...")
                # 尝试重新发送
                for text in ["重新发送", "获取验证码", "重发"]:
                    try:
                        btn = await login_frame.query_selector(f"button:has-text('{text}')")
                        if btn and await btn.is_visible():
                            await btn.click()
                            break
                    except:
                        continue

        if not code or len(code) not in (4, 5, 6):
            print("❌ 获取验证码失败")
            return False

        # 9. 填入验证码
        code_filled = False
        code_sel = "input[placeholder*='验证码'], input[maxlength='6'], input[maxlength='4'], input[autocomplete='one-time-code']"
        for sel in [code_sel, "input:nth-of-type(2)", "input:last-of-type"]:
            try:
                inp = await login_frame.query_selector(sel)
                if inp:
                    await inp.click()
                    await inp.fill(code)
                    await asyncio.sleep(1)
                    code_filled = True
                    print(f"  ✅ 已填验证码")
                    break
            except:
                continue

        if not code_filled:
            # fallback: 用 JS 填
            try:
                await login_frame.evaluate(f'''
                    () => {{
                        const inputs = document.querySelectorAll("input");
                        for (const i of inputs) {{
                            if (!i.value && i.offsetParent !== null) {{
                                i.value = "{code}";
                                i.dispatchEvent(new Event("input", {{bubbles: true}}));
                                break;
                            }}
                        }}
                    }}
                ''')
                await asyncio.sleep(1)
            except:
                pass

        # 10. 点登录确认
        for text in ["登录", "确认", "同意并登录", "下一步"]:
            try:
                btn = await login_frame.query_selector(f"button:has-text('{text}')")
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(3)
                    print(f"  ✅ 点击 '{text}'")
                    break
            except:
                continue

        # 11. 等待登录结果（URL 变化 = 登录成功）
        await asyncio.sleep(5)
        current_url = page.url
        if "passport" not in current_url.lower() and "login" not in current_url.lower():
            print(f"  ✅ 登录成功! URL: {current_url[:60]}")
            return True
        else:
            print(f"  ⚠️ 登录后仍在登录页，可能需要手动处理")
            return False

    def get_action_summary(self) -> dict:
        """获取本次会话的操作统计"""
        return {
            **self._action_counts,
            "elapsed_minutes": round(self._elapsed_hours() * 60, 1),
        }
