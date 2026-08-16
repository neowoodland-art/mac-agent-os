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
    "comment_like":         '[data-e2e="comment-digg"]',       # 评论点赞按钮
    "comment_item":         '[data-e2e="comment-item"]',        # 单条评论容器
    "comment_reply_btn":    '[class*="reply"],[class*="Reply"]', # 回复按钮
    "hot_tag":              '.hot-tag,[class*="hot"]',           # 热评标记

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

    # 验证码（兼容新旧两种 class）
    "verify_mask":          '.second-verify-mask',
    "verify_panel":         '.second-verify-panel, .uc-ui-verify_sms-verify',        # 旧+新
    "verify_input":         '.uc-ui-verify_sms-verify_input, input[placeholder*="验证码"]',
    "verify_get_code":      '.uc-ui-typography_descript, [class*="getCode"], button:has-text("获取验证码")',
    "verify_confirm":       '.uc-ui-verify_sms-verify_button.primary, .uc-ui-verify_sms-verify_b',
    "verify_cancel":        '.uc-ui-verify_sms-verify_button.second',
    "verify_phone_input":   'input[placeholder*="手机"]',
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
        self._app_login_required = False  # 标记：是否需要使用抖音App登录

    def set_account_id(self, aid: str):
        print(f"[set_account_id] id(self)={id(self)}, aid={aid}")
        self._account_id = aid

    def _save_profiles_json(self):
        """保存主页信息到 profiles.json + homepage_info.json（两个 Dashboard 数据源）"""
        if not self._account_id:
            print(f"[douyin_ops] _save_profiles_json: _account_id 为空，跳过")
            return
        try:
            prof = getattr(self, '_profile', {})
            PROFILES_JSON.parent.mkdir(parents=True, exist_ok=True)

            # ── 写 profiles.json（供账号管理页面读取）──
            if PROFILES_JSON.exists():
                all_p = json.loads(PROFILES_JSON.read_text())
            else:
                all_p = {}

            # v5 防覆盖保护：新值有效（非 ?/空）才覆盖，否则保留旧值
            def _pick(new_v, old_v):
                if new_v not in (None, "", "?"):
                    return new_v
                return old_v if old_v not in (None, "") else "?"

            old_p = all_p.get(self._account_id, {}) if isinstance(all_p, dict) else {}
            ban_status = prof.get("_status", "normal")
            all_p[self._account_id] = {
                "nickname": _pick(prof.get("nickname"), old_p.get("nickname")),
                "user_id": _pick(prof.get("user_id"), old_p.get("user_id")),
                "following": _pick(prof.get("following"), old_p.get("following")),
                "fans": _pick(prof.get("fans"), old_p.get("fans")),
                "likes": _pick(prof.get("likes"), old_p.get("likes")),
                "posts": _pick(prof.get("posts"), old_p.get("posts")),
                "bio": _pick(prof.get("bio"), old_p.get("bio")),
                "status": ban_status,
                "platform": "douyin",
                "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            PROFILES_JSON.write_text(json.dumps(all_p, ensure_ascii=False, indent=2))

            # ── 同步写 homepage_info.json（供信息采集页面读取）──
            hp_path = PROFILES_JSON.parent / "homepage_info.json"
            hp_data = {"collected_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "results": []}
            if hp_path.exists():
                try:
                    hp_data = json.loads(hp_path.read_text())
                except Exception:
                    hp_data = {"collected_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "results": []}
            entry = None
            for r in hp_data.get("results", []):
                rid = r.get("identity_dir", "").replace("identities/", "")
                if rid == self._account_id:
                    entry = r
                    break
            if not entry:
                hp_data.setdefault("results", []).append({
                    "identity_dir": f"identities/{self._account_id}",
                    "phone": self._account_id.split("_")[-1] if "_" in self._account_id else self._account_id,
                    "douyin": {}, "xiaohongshu": None
                })
                entry = hp_data["results"][-1]
            if entry.get("douyin") is None:
                entry["douyin"] = {}
            entry["douyin"].update({
                "nickname": _pick(prof.get("nickname"), entry["douyin"].get("nickname")),
                "fans": _pick(prof.get("fans"), entry["douyin"].get("fans")),
                "following": _pick(prof.get("following"), entry["douyin"].get("following")),
                "likes": _pick(prof.get("likes"), entry["douyin"].get("likes")),
                "posts": _pick(prof.get("posts"), entry["douyin"].get("posts")),
                "bio": _pick(prof.get("bio"), entry["douyin"].get("bio")),
                "status": ban_status,
                "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })
            hp_path.write_text(json.dumps(hp_data, ensure_ascii=False, indent=2))

        except Exception as e:
            print(f"[douyin_ops] _save_profiles_json 失败: {e}")

    # ═══════════════════════════════════════════════════════════
    # v5 主页数据 API 采集（不依赖 DOM 结构，抖音改版不再影响）
    # ═══════════════════════════════════════════════════════════

    def _known_user_id(self) -> str:
        """从已有 profiles.json 读取该账号的 user_id（供 other 接口降级用）"""
        try:
            if PROFILES_JSON.exists():
                all_p = json.loads(PROFILES_JSON.read_text())
                p = all_p.get(self._account_id, {})
                uid = str(p.get("user_id", "") or "")
                if uid and uid != "?":
                    return uid
        except Exception:
            pass
        return ""

    @staticmethod
    def _profile_from_api_user(u: dict) -> dict:
        """把 API user 对象转成统一 profile 结构"""
        avatar = ""
        try:
            avatar = (u.get("avatar_thumb") or {}).get("url_list", [""])[0]
        except Exception:
            pass
        def _num(v):
            return "" if v is None else str(v)
        return {
            "nickname": u.get("nickname", "") or "",
            "user_id": str(u.get("uid", u.get("unique_id", "")) or ""),
            "following": _num(u.get("following_count")),
            "fans": _num(u.get("follower_count")),
            "likes": _num(u.get("total_favorited")),
            "posts": _num(u.get("aweme_count")),
            "bio": (u.get("signature", "") or "").strip()[:50],
            "avatar": avatar,
        }

    async def _fetch_profile_api(self) -> dict:
        """v5: 通过抖音 Web API 获取主页数据（同源 fetch，不依赖 DOM）

        优先 /aweme/v1/web/user/profile/self/（无需 uid）
        失败降级 /aweme/v1/web/user/profile/other/（用已有 user_id）
        返回统一 profile 结构；失败返回空 dict
        """
        # 1. 先尝试 self 接口（当前登录用户）
        js_self = """async () => {
            try {
                const r = await fetch('/aweme/v1/web/user/profile/self/?device_platform=webapp&aid=6383', {
                    headers: { 'Accept': 'application/json, text/plain, */*', 'Referer': 'https://www.douyin.com/' }
                });
                const d = await r.json();
                return JSON.stringify({ok: !!(d && d.user), data: (d && d.user) || {}});
            } catch(e) {
                return JSON.stringify({ok: false, error: e.message});
            }
        }"""
        try:
            raw = await self.page.evaluate(js_self)
            payload = json.loads(raw)
            if payload.get("ok"):
                prof = self._profile_from_api_user(payload["data"])
                print(f"[douyin_ops] ✅ API self 成功: {prof['nickname']} 粉丝={prof['fans']}")
                return prof
        except Exception as e:
            print(f"[douyin_ops] API self 异常: {e}")

        # 2. 降级 other 接口（需要数字 uid，从已有 profiles.json 读取）
        uid = self._known_user_id()
        if uid:
            js_other = f"""async () => {{
                try {{
                    const r = await fetch('/aweme/v1/web/user/profile/other/?user_id={uid}&device_platform=webapp&aid=6383', {{
                        headers: {{ 'Accept': 'application/json, text/plain, */*', 'Referer': 'https://www.douyin.com/' }}
                    }});
                    const d = await r.json();
                    return JSON.stringify({{ok: !!(d && d.user), data: (d && d.user) || {{}}}});
                }} catch(e) {{
                    return JSON.stringify({{ok: false, error: e.message}});
                }}
            }}"""
            try:
                raw2 = await self.page.evaluate(js_other)
                payload2 = json.loads(raw2)
                if payload2.get("ok"):
                    prof2 = self._profile_from_api_user(payload2["data"])
                    print(f"[douyin_ops] ✅ API other 成功: {prof2['nickname']} 粉丝={prof2['fans']}")
                    return prof2
            except Exception as e:
                print(f"[douyin_ops] API other 异常: {e}")
        else:
            print("[douyin_ops] ⚠️ 无已知 user_id，跳过 other 接口降级")
        return {}

    async def _collect_profile_dom(self) -> dict:
        """DOM 兜底解析（v4 旧逻辑，仅当 API 全部失败时使用）"""
        profile = await self.page.evaluate("""() => {
            try {
                const text = (document.body.innerText || '').trim();
                // 昵称：优先从标题取，失败则尝试 DOM 选择器
                var nickFromTitle = (document.title || '').replace(' - 抖音', '').replace('的抖音', '').trim();
                // DOM 兜底：找页面中可能包含昵称的元素
                var nickFromDom = '';
                var nickEl = document.querySelector('[data-e2e="user-info"] span, [class*="profile"] [class*="name"], .user-info .name, .profile-info span');
                if (nickEl && nickEl.textContent) nickFromDom = nickEl.textContent.trim();
                const nickname = nickFromTitle || nickFromDom || '?';
                const uidM = text.match(/抖音号[：:]\\s*(\\S+)/);
                // 正则匹配两种顺序："数字 标签" 和 "标签 数字"
                function extractNum(label) {
                    var m1 = text.match(new RegExp('(\\\\d+(?:\\\\.\\\\d+)?[万w]?)\\\\s*' + label));
                    if (m1) return m1[1];
                    var m2 = text.match(new RegExp(label + '\\\\s*(\\\\d+(?:\\\\.\\\\d+)?[万w]?)'));
                    if (m2) return m2[1];
                    return null;
                }
                const folM = extractNum('关注');
                const fanM = extractNum('粉丝');
                const likM = extractNum('获赞');
                const posM = extractNum('作品');
                // e2e 兜底：从原始文本中只提取数字部分
                function e2eNum(s) {
                    try {
                        var el = document.querySelector('[data-e2e="'+s+'"]');
                        if (!el) return null;
                        var m = (el.textContent||'').trim().match(/\\d+(?:\\.\\d+)?[万w]?/);
                        return m ? m[0] : null;
                    } catch(e) { return null; }
                }
                // DOM 兜底：data-e2e 容器内的数字（结构: <div data-e2e="xxx"><div>标签</div><div>数字</div></div>）
                function statByE2e(e2eName) {
                    try {
                        var container = document.querySelector('[data-e2e="'+e2eName+'"]');
                        if (!container) return null;
                        var divs = container.querySelectorAll('div');
                        for (var j = 0; j < divs.length; j++) {
                            var m = (divs[j].textContent||'').trim().match(/^\\d+(?:\\.\\d+)?[万w]?$/);
                            if (m) return m[0];
                        }
                    } catch(e) {}
                    return null;
                }
                return {
                    nickname: nickname, user_id: uidM ? uidM[1] : '?',
                    following: folM || (e2eNum('user-info-follow')||statByE2e('user-info-follow')||'?'),
                    fans: fanM || (e2eNum('user-info-fans')||statByE2e('user-info-fans')||'?'),
                    likes: likM || (e2eNum('user-info-like')||statByE2e('user-info-like')||'?'),
                    posts: posM || (e2eNum('user-tab-count')||statByE2e('user-tab-count')||'?'),
                    bio: (document.querySelector('[data-e2e="user-bio"]')?.textContent?.trim() || '?').slice(0, 50),
                };
            } catch(e) {
                return { nickname: '?', user_id: '?', following: '?', fans: '?', likes: '?', posts: '?', bio: '?', _error: e.message };
            }
        }""")
        return profile

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
                          message="需要点赞按钮可见", soft=True),  # 软条件：按钮选择器失效时放行键盘Z兜底
            ],
            "collect": [
                Condition("page_mode", "page_mode", "player", message="需要在视频播放页"),
                Condition("selector", '[data-e2e="video-player-collect"]', True,
                          message="需要收藏按钮可见", soft=True),  # 软条件：放行JS/坐标兜底
            ],
            "follow": [
                Condition("page_mode", "page_mode", "player", message="需要在视频播放页"),
                Condition("selector", '[data-e2e="feed-follow-icon"]', True,
                          message="需要关注按钮可见", soft=True),  # 软条件：放行DOM/JS兜底
            ],
            "open_comments": [
                Condition("page_mode", "page_mode", "player", message="需要在视频播放页"),
            ],
            "close_comments": [],
            "next_video": [
                Condition("page_mode", "page_mode", "player", message="需要在视频播放页"),
            ],
            "prev_video": [
                Condition("page_mode", "page_mode", "player", message="需要在视频播放页"),
            ],
            "post_comment": [
                # B模式兼容：评论区已在页面中无需额外条件
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
            "open_video": [],
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
            t0 = time.time()
            for _ in range(3):
                await self.page.goto(HOME_URL, timeout=30000, wait_until="domcontentloaded")
                # 等首页真正加载完成：等视频卡片出现，最多等10秒
                for w in range(10):
                    url = self.page.url
                    card_count = await self.page.evaluate(
                        "document.querySelectorAll('.discover-video-card-item, "
                        "[class*=\"video-card\"], [data-e2e=\"alink-item\"]').length")
                    if card_count > 0 and '/user/' not in url and '/login' not in url:
                        return OpResult(op, step_id, True, "home", time.time()-t0)
                    await asyncio.sleep(1)
                # 10秒没等到 → 再跳一次
                await asyncio.sleep(2)
            return OpResult(op, step_id, True, f"home(last_url={self.page.url[:50]})", time.time()-t0)

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
            result = await self.post_comment(text, step_id=step_id)
            success = result == 'ok'
            return OpResult(op, step_id, success, result if not success else "sent", time.time()-t0)

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
            """进入视频播放页 — 鼠标点击第一张视频卡片"""
            t0 = time.time()
            # 先查：已在播放页则跳过（看URL是否已进入视频页，不看video元素——feed上的video预览也会count>0）
            url = self.page.url
            if '/video/' in url or 'modal_id' in url:
                await self._ensure_video_focused()
                return OpResult(op, step_id, True, "already_player", time.time()-t0)

            # 找第一张视频卡片，鼠标点击进入播放
            card = self.page.locator('.discover-video-card-item, a[href*="/video/"], [class*="video-card"]').first
            for _ in range(15):
                if await card.count() > 0:
                    break
                await asyncio.sleep(1)
            if await card.count() > 0:
                await card.click()
                await asyncio.sleep(1)
                await card.click()
                await asyncio.sleep(3)
                return OpResult(op, step_id, True, "video_card_clicked", time.time()-t0)
            return OpResult(op, step_id, False, "no_card_found", time.time()-t0)

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

        if op == "like_comment":
            target = args.get("target", "first")
            ok = await self.like_comment(target=target, step_id=step_id)
            return OpResult(op, step_id, ok, "liked" if ok else "no_btn", time.time()-t0)

        if op == "scroll_to_hot_comment":
            ok = await self.scroll_to_hot_comment(step_id=step_id)
            return OpResult(op, step_id, ok, "scrolled", time.time()-t0)

        if op == "find_comment_by_code":
            code = args.get("code", "")
            ok = await self.find_comment_by_code(code, step_id=step_id)
            return OpResult(op, step_id, ok, f"found:{code}" if ok else f"not_found:{code}", time.time()-t0)

        if op == "reply_with_text":
            text = args.get("text", "")
            ok = await self.reply_with_text(text, step_id=step_id)
            return OpResult(op, step_id, ok, "replied" if ok else "failed", time.time()-t0)

        if op == "post_comment_with_code":
            text = args.get("text", "")
            code = args.get("code", "")
            r = await self.post_comment_with_code(text, code, step_id=step_id)
            return OpResult(op, step_id, r == "ok", r, time.time()-t0)

        if op == "auto_verify":
            ok = await self.auto_verify(step_id=step_id)
            return OpResult(op, step_id, ok, "verified" if ok else "no_verify", time.time()-t0)

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
            logged_in = await self._ensure_logged_in()
            if logged_in:
                # 登录成功后重新导航到个人主页（弹窗改变了URL）
                await self.page.goto("https://www.douyin.com/user/self", timeout=20000, wait_until="domcontentloaded")
                await asyncio.sleep(3)
            else:
                print("⚠️ dy_goto_profile: 未能登录")
                await asyncio.sleep(3)
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
        """AO_NAV: 导航到指定URL（含登录恢复后页面前置检测）"""
        t0 = time.time()
        try:
            # 如果页面被登录恢复卡住(弹窗/加载中)，先 reload 一次
            try:
                cur = self.page.url
                if cur and ('login' in cur.lower() or 'passport' in cur.lower()):
                    await self.page.reload(timeout=15000)
                    await self._wait(1)
            except Exception:
                pass

            await self.page.goto(url, timeout=30000, wait_until='domcontentloaded')
            await self._wait(2)
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_NAV", url, True, dur)
            return True
        except Exception as e:
            # 兜底：reload 重试一次
            try:
                await self.page.reload(timeout=15000)
                await self._wait(1)
                await self.page.goto(url, timeout=30000, wait_until='domcontentloaded')
                await self._wait(2)
                dur = int((time.time() - t0) * 1000)
                await self._log_op(step_id, "AO_NAV", f"{url}(retry)", True, dur)
                return True
            except Exception as e2:
                await self._log_op(step_id, "AO_NAV", url, False, int((time.time()-t0)*1000), str(e2))
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

    async def _click_comment_btn(self) -> bool:
        """点击页面上的评论区入口按钮（快速探测，100ms超时）"""
        for sel in [
            SELECTORS['comment_icon'],
            '[data-e2e="video-player-comment"]',
            '[class*="comment-action"]',
            '[class*="comment-count"]',
            '[aria-label*="评论"]',
        ]:
            try:
                btn = self.page.locator(sel)
                await btn.first.wait_for(state="attached", timeout=100)
                await btn.first.click(timeout=1000)
                return True
            except Exception:
                continue
        return False

    async def open_comments(self, step_id: int = 0) -> bool:
        """打开评论区（和成功版一致的逻辑）"""
        t0 = time.time()
        try:
            # 1. 先检测评论区是否已打开
            try:
                if await self.page.locator(SELECTORS['comment_list']).count() > 0:
                    dur = int((time.time() - t0) * 1000)
                    await self._log_op(step_id, "AO_OPEN", "already_open", True, dur)
                    return True
            except Exception:
                pass

            url = self.page.url
            is_standalone = '/video/' in url and 'modal_id' not in url

            if is_standalone:
                # ── B模式：评论区在页面下方，滚动触发懒加载 ──
                # 首先检测评论区是否已加载
                _cl = self.page.locator(SELECTORS['comment_list'])
                if await _cl.count() > 0:
                    await _cl.first.scroll_into_view_if_needed()
                    dur = int((time.time() - t0) * 1000)
                    await self._log_op(step_id, "AO_OPEN", "B_already_loaded", True, dur)
                    return True
                # 滚动到页面底部触发评论区懒加载
                await self.page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                await self._wait(2)
                if await _cl.count() > 0:
                    await _cl.first.scroll_into_view_if_needed()
                    dur = int((time.time() - t0) * 1000)
                    await self._log_op(step_id, "AO_OPEN", "B_scroll_bottom", True, dur)
                    return True
                # 再试：滚动到 70% 位置（评论区可能在中间）
                await self.page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight * 0.7)")
                await self._wait(1.5)
                if await _cl.count() > 0:
                    await _cl.first.scroll_into_view_if_needed()
                    dur = int((time.time() - t0) * 1000)
                    await self._log_op(step_id, "AO_OPEN", "B_scroll_mid", True, dur)
                    return True
                # 回到顶部
                await self.page.evaluate("window.scrollTo(0, 0)")
            else:
                # ── A模式：键盘X打开评论区浮层 ──
                await self._ensure_video_focused()
                await self.page.keyboard.press(KEYS['comment'])
                await self._wait(1.0)
                try:
                    if await self.page.locator(SELECTORS['comment_list']).count() > 0:
                        dur = int((time.time() - t0) * 1000)
                        await self._log_op(step_id, "AO_OPEN", "A:keyboard_x", True, dur)
                        return True
                except Exception:
                    pass

            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_OPEN", "failed", False, dur)
            return False
        except Exception as e:
            await self._log_op(step_id, "AO_OPEN", "error", False, int((time.time()-t0)*1000), str(e))
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
        """AO_COMMENT: 发表评论(纯Playwright操作)。返回 'ok' / 'verify_needed' / 'failed'"""
        if not self._check_rate("comment"):
            print(f"  [post_comment] ⚡ 频率限制跳过")
            return 'ok'
        t0 = time.time()
        try:
            # 1. 确保评论区打开
            _cl_count = await self.page.locator(SELECTORS['comment_list']).count()
            print(f"  [post_comment] comment_list.count={_cl_count}")
            if _cl_count == 0:
                await self.open_comments(step_id)
                await self._wait(2)

            # 2. 滚动评论区到可视区域
            cl = self.page.locator(SELECTORS['comment_list'])
            if await cl.count() > 0:
                try:
                    await cl.first.scroll_into_view_if_needed(timeout=3000)
                except Exception:
                    pass
                await self._wait(0.5)

            # 3. 找输入框——多选择器兜底
            editor_selectors = [
                '[contenteditable="true"]',
                SELECTORS['comment_editor'],
                '[data-e2e="comment-input"]',
                '[class*="comment-input"]',
                'textarea[placeholder*="评论"]',
                'input[placeholder*="评论"]',
            ]
            editor = None
            for sel in editor_selectors:
                el = self.page.locator(sel)
                c = await el.count()
                print(f"  [post_comment]   sel={sel} count={c}")
                if c > 0:
                    editor = el
                    print(f"  [post_comment] ✅ 命中: {sel}")
                    break
            if editor is None:
                dur = int((time.time() - t0) * 1000)
                await self._log_op(step_id, "AO_COMMENT", "all_selectors", False, dur, "所有选择器未命中")
                print(f"  [post_comment] ❌ 无输入框, 耗时{dur}ms")
                return 'failed'

            # 4. 真实鼠标点击激活编辑器（不用 force=True，不用 JS evaluate）
            try:
                await editor.first.wait_for(state="visible", timeout=3000)
                await editor.first.scroll_into_view_if_needed(timeout=2000)
                await self._wait(0.3)
            except Exception:
                pass
            # Playwright 真实鼠标点击（非 JS click）
            box = await editor.first.bounding_box()
            if box:
                await self.page.mouse.click(
                    box['x'] + box['width'] // 2,
                    box['y'] + box['height'] // 2
                )
            else:
                await editor.first.click()
            await self._wait(0.8)

            # 5. pbcopy + Meta+V 粘贴输入（复制 reply_comment 的成功方案）
            #    绕过 Draft.js + Camoufox 键盘事件兼容问题，粘贴是浏览器原生操作
            proc = await asyncio.create_subprocess_exec(
                'pbcopy', stdin=asyncio.subprocess.PIPE
            )
            await proc.communicate(input=text.encode())
            await self._wait(0.3)
            await self.page.keyboard.press('Meta+V')
            await self._wait(0.5)

            # 6. 发送——用 Enter （你说可用回车或 Ctrl+回车）
            sent = False
            for attempt in range(3):
                # 策略A: Enter
                await self._wait(0.3)
                await self.page.keyboard.press('Enter')
                await self._wait(2.5)
                if await self._verify_comment_posted(text):
                    sent = True
                    break
                # 策略B: Ctrl+Enter
                await self.page.keyboard.press('Control+Enter')
                await self._wait(2.5)
                if await self._verify_comment_posted(text):
                    sent = True
                    break

            if not sent:
                dur = int((time.time() - t0) * 1000)
                await self._log_op(step_id, "AO_COMMENT", "send_failed", False, dur, "所有发送方式均失败")
                print(f"  [post_comment] ❌ 发送失败, 耗时{dur}ms")
                return 'failed'

            self._action_counts["comment"] += 1
            await self._wait(1.5)

            # 7. 检查验证码
            if await self.page.locator(SELECTORS['verify_panel']).count() > 0:
                dur = int((time.time() - t0) * 1000)
                await self._log_op(step_id, "AO_COMMENT", "verify_panel", True, dur, "触发验证码")
                return 'verify_needed'

            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_COMMENT", f"ok:{text[:20]}", True, dur)
            print(f"  [post_comment] ✅ 发送成功, 耗时{dur}ms")
            return 'ok'

        except Exception as e:
            print(f"  [post_comment] ❌ 异常: {e}")
            await self._log_op(step_id, "AO_COMMENT", "error", False, int((time.time()-t0)*1000), str(e))
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

    async def auto_verify(self, step_id: int = 0) -> bool:
        """
        自动处理验证弹窗：检测→填手机→获验证码→填码→确认
        兼容新旧两种 class 名，复用 SMS API 获取验证码。
        """
        t0 = time.time()
        try:
            panel = self.page.locator(SELECTORS['verify_panel'])
            if await panel.count() == 0:
                return False

            self.log(f"  ⚠️ 检测到验证弹窗, 自动处理...")

            # 1. 找手机号输入框并填号
            phone_input = self.page.locator(SELECTORS['verify_phone_input']).first
            if await phone_input.count() > 0:
                await phone_input.click()
                await self._wait(0.5)
                phone = self._get_phone_from_account()
                if phone:
                    await phone_input.fill(phone)
                    self.log(f"  📱 已填入手机号: {phone}")
                    await self._wait(1)

            # 2. 点击"获取验证码"
            get_code_btn = self.page.locator(SELECTORS['verify_get_code']).first
            if await get_code_btn.count() > 0:
                await get_code_btn.click()
                self.log(f"  📡 已点击获取验证码")
                await self._wait(1)

            # 3. 等待验证码输入框出现
            for _ in range(45):
                if await self.page.locator(SELECTORS['verify_input']).count() > 0:
                    break
                await asyncio.sleep(1)

            # 4. 获取验证码（复用 SMS API）
            code = await self._fetch_sms_code()
            if not code:
                self.log(f"  ❌ 获取验证码失败")
                return False
            self.log(f"  ✅ 获取到验证码: {code}")

            # 5. 填验证码
            code_input = self.page.locator(SELECTORS['verify_input']).first
            if await code_input.count() > 0:
                await code_input.fill(code)
                await self._wait(0.5)

            # 6. 点确认
            confirm = self.page.locator(SELECTORS['verify_confirm']).first
            if await confirm.count() > 0:
                await confirm.click()
            else:
                await self.page.keyboard.press('Enter')

            await self._wait(2)

            # 6.5 检测"请使用抖音App登录"
            try:
                body_text = (await self.page.evaluate("document.body.innerText")) or ""
                for keyword in ["请使用抖音App登录", "请使用抖音 APP", "请使用抖音app"]:
                    if keyword in body_text:
                        self.log(f"  ⛔ 检测到: {keyword} — 该账号需使用抖音App登录")
                        self._app_login_required = True
                        self._mark_app_login_required()
                        return False
            except:
                pass

            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_VERIFY", "auto", True, dur)
            self.log(f"  ✅ 验证完成")
            return True
        except Exception as e:
            await self._log_op(step_id, "AO_VERIFY", "auto", False, int((time.time()-t0)*1000), str(e))
            return False

    async def _get_phone_from_account(self) -> str:
        """从 accounts.yaml 读取当前账号手机号"""
        try:
            import yaml, os
            cfg = os.path.expanduser(
                '~/workbuddy-agent-os/agent-local/tools/matrix/config/accounts.yaml')
            aid = self._account_id if hasattr(self, '_account_id') else ''
            if os.path.exists(cfg):
                data = yaml.safe_load(open(cfg))
                for a in data.get('accounts', []):
                    if a.get('id') == aid:
                        return a.get('phone', '')
        except:
            pass
        return ''

    async def _fetch_sms_code(self) -> str:
        """获取 SMS 验证码（复用短信 API）"""
        try:
            from matrix_modules.account.sms.api import ApiSMSHandler
            phone = self._get_phone_from_account()
            if not phone:
                return ''
            handler = ApiSMSHandler(phone=phone)
            code = await handler.wait(platform=self._account_id or "douyin", timeout=120)
            if code:
                self._reset_sms_failures()
                return code
        except:
            pass
        # 走到这里说明 SMS 获取失败
        if self._track_sms_failure():
            self._mark_sms_failed()
        return ''

    # ── 评论验证 ──────────────────────────────────────────────

    async def _verify_comment_posted(self, text: str) -> bool:
        """验证评论是否已发布：检查评论区前几条是否包含刚发的文字"""
        try:
            cl = self.page.locator(SELECTORS['comment_list'])
            if await cl.count() == 0:
                return False
            # 获取评论区所有评论项
            items = cl.first.locator('> div, [data-e2e="comment-item"]')
            count = await items.count()
            if count == 0:
                return False
            # 检查前 5 条评论是否包含我们的文字（全文匹配）
            check_text = text.strip()
            for i in range(min(count, 5)):
                try:
                    item_text = await items.nth(i).inner_text(timeout=2000)
                    if check_text in item_text.strip():
                        print(f"  [verify_comment] ✅ 评论已发布 (第{i+1}条)")
                        return True
                except Exception:
                    continue
            print(f"  [verify_comment] ❌ 未在评论区找到匹配文字")
            return False
        except Exception as e:
            print(f"  [verify_comment] ❌ 验证异常: {e}")
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
        """AO_PROFILE: 进入个人主页，一次性采集全部字段

        v5 策略（2026-08-15）：API 优先，DOM 兜底
          1. 同源 fetch 抖音 Web API（profile/self → profile/other）
             —— 不依赖页面 DOM 结构，抖音改版不再影响
          2. API 失败 → DOM innerText 正则（旧逻辑保留）
        """
        t0 = time.time()
        await self.page.goto("https://www.douyin.com/user/self", timeout=20000, wait_until="domcontentloaded")
        # 检查登录状态，未登录时自动处理弹窗
        logged_in = await self._ensure_logged_in()
        if logged_in:
            # 登录成功后需要重新导航到个人主页（登录弹窗可能改变了页面URL）
            await self.page.goto("https://www.douyin.com/user/self", timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(3)
        else:
            print("⚠️ 未能登录，但仍尝试采集数据")
            await asyncio.sleep(3)

        # ── v5: API 优先（不依赖 DOM 结构）──
        profile = await self._fetch_profile_api()
        if not profile or not profile.get("nickname"):
            print("[douyin_ops] ⚠️ API 采集失败，降级 DOM 解析")
            profile = await self._collect_profile_dom()

        self._profile = profile

        # 抖音封号检测
        ban_status = await self._check_douyin_banned()
        profile["_status"] = ban_status
        if ban_status == "banned":
            print(f"[douyin_ops] ⚠️ 账号被封禁")

        self._save_profiles_json()  # ← 写入 profiles.json
        dur = int((time.time() - t0) * 1000)
        await self._log_op(step_id, "AO_PROFILE", "user/self", True, dur)
        return profile

    async def _check_douyin_banned(self) -> str:
        """检测抖音账号是否被封禁
        Returns: "normal" / "banned" / "unknown"
        """
        try:
            text = (await self.page.evaluate("document.body.innerText")) or ""
            # 封号关键词
            ban_keywords = ["账号已重置", "因违规", "已被封禁", "账号存在风险",
                            "已被限制", "账号异常", "违规封禁", "处罚通知"]
            for kw in ban_keywords:
                if kw in text:
                    print(f"[douyin_ops] ⚠️ 检测到封号关键词: {kw}")
                    return "banned"
            # DOM 检测：特定封号提示元素
            try:
                ban_el = self.page.locator('[class*="ban"],[class*="punish"],[class*="forbid"]')
                if await ban_el.count() > 0 and await ban_el.first.is_visible():
                    return "banned"
            except:
                pass
        except:
            pass
        return "normal"

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

    async def like_comment(self, target: str = "first", step_id: int = 0) -> bool:
        """点赞评论。target=first 点第一条, hot 点热评, 或数字指定索引"""
        t0 = time.time()
        try:
            if await self.page.locator(SELECTORS['comment_list']).count() == 0:
                await self.open_comments(step_id)
                await asyncio.sleep(2)

            items = await self.page.locator(SELECTORS['comment_like']).all()
            if not items:
                await self._log_op(step_id, "AO_LIKE_COMMENT", "comment_like", False, int((time.time()-t0)*1000), "无评论点赞按钮")
                return False

            idx = 0
            if target == "hot":
                # 找有热评标记的评论
                hot_items = await self.page.locator(f'{SELECTORS["comment_item"]}:has({SELECTORS["hot_tag"]})').all()
                if hot_items:
                    idx = 1  # 热评通常是第二条（第一条是置顶）
            elif target.isdigit():
                idx = int(target)

            if idx >= len(items):
                idx = 0
            await items[idx].click()
            await self._wait(1)
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_LIKE_COMMENT", f"comment_like[{idx}]", True, dur)
            return True
        except Exception as e:
            await self._log_op(step_id, "AO_LIKE_COMMENT", "comment_like", False, int((time.time()-t0)*1000), str(e))
            return False

    async def scroll_to_hot_comment(self, step_id: int = 0) -> bool:
        """滚动到热评区域"""
        t0 = time.time()
        try:
            if await self.page.locator(SELECTORS['comment_list']).count() == 0:
                await self.open_comments(step_id)
                await asyncio.sleep(2)

            # 滚动评论区到热评
            await self.page.evaluate("""() => {
                const list = document.querySelector('[data-e2e="comment-list"]');
                if (list) {
                    const items = list.querySelectorAll('[data-e2e="comment-item"]');
                    if (items.length > 3) {
                        items[Math.min(2, items.length-1)].scrollIntoView({behavior: 'smooth', block: 'center'});
                    }
                }
            }""")
            await self._wait(1.5)
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_SCROLL_HOT", "comment-list", True, dur)
            return True
        except Exception as e:
            await self._log_op(step_id, "AO_SCROLL_HOT", "comment-list", False, int((time.time()-t0)*1000), str(e))
            return False

    # ── 占位: 三级接力原子操作（等你录制后替换）──

    async def find_comment_by_code(self, code: str, step_id: int = 0) -> bool:
        """
        在评论区搜索包含识别码的评论。
        遍历所有 comment-item，匹配文本内容中的 🌸XX 码。
        """
        t0 = time.time()
        try:
            if await self.page.locator(SELECTORS['comment_list']).count() == 0:
                await self.open_comments(step_id)
                await asyncio.sleep(2)

            # 遍历所有评论，找包含 code 的
            found = await self.page.evaluate(f"""() => {{
                const items = document.querySelectorAll('[data-e2e="comment-item"]');
                for (const item of items) {{
                    const text = (item.textContent || '').trim();
                    if (text.includes('{code}')) {{
                        item.scrollIntoView({{behavior:'smooth', block:'center'}});
                        item.style.border = '2px solid red';
                        // 点击评论使其聚焦
                        const replyBtn = item.querySelector('[class*="reply"],[class*="Reply"]');
                        if (replyBtn) {{
                            replyBtn.click();
                            return 'found_and_reply';
                        }}
                        item.click();
                        return 'found';
                    }}
                }}
                return '';
            }}""")
            if found:
                await self._wait(1.5)
                dur = int((time.time() - t0) * 1000)
                await self._log_op(step_id, "AO_FIND_COMMENT", f"code={code} result={found}", True, dur)
                return True
            else:
                await self._log_op(step_id, "AO_FIND_COMMENT", f"code={code} not_found", False, int((time.time()-t0)*1000))
                return False
        except Exception as e:
            await self._log_op(step_id, "AO_FIND_COMMENT", f"code={code}", False, int((time.time()-t0)*1000), str(e))
            return False

    async def reply_with_text(self, text: str, step_id: int = 0) -> bool:
        """
        回复当前聚焦的评论（find_comment_by_code 后调用）。
        在已聚焦的评论回复框中输入文本并发送。
        """
        t0 = time.time()
        try:
            # 找 Draft.js 编辑器
            editor = self.page.locator(SELECTORS['comment_editor'])
            if await editor.count() == 0:
                await self._log_op(step_id, "AO_REPLY_TEXT", "editor", False, int((time.time()-t0)*1000), "回复输入框未找到")
                return False

            await editor.click()
            await self._wait(0.5)
            await editor.press_sequentially(text, delay=random.uniform(50, 120))
            await self._wait(0.5)

            # 发送：先找发送按钮，失败则 Enter
            sent = await self.page.evaluate("""() => {
                const btns = document.querySelectorAll('button, [class*="send"], [class*="submit"]');
                for (const b of btns) {
                    const t = (b.textContent || '').trim();
                    if (t.includes('发送') || t.includes('发布') || b.className.includes('send')) {
                        b.click(); return true;
                    }
                }
                return false;
            }""")
            if not sent:
                await self.page.keyboard.press('Enter')

            await self._wait(1.5)
            dur = int((time.time() - t0) * 1000)
            await self._log_op(step_id, "AO_REPLY_TEXT", f"text={text[:20]}", True, dur)
            return True
        except Exception as e:
            await self._log_op(step_id, "AO_REPLY_TEXT", f"text={text[:20]}", False, int((time.time()-t0)*1000), str(e))
            return False

    async def post_comment_with_code(self, text: str, code: str, step_id: int = 0) -> str:
        """发评+识别码。复用 post_comment，末尾追加 code"""
        full_text = f"{text} {code}" if code else text
        return await self.post_comment(full_text, step_id=step_id)

    async def _ensure_logged_in(self) -> bool:
        """状态机：检查抖音登录状态，未登录则自动处理弹窗

        流程:
          1. 看右上角是否有 [data-e2e="user-info"] （已登录标志）
          2. 如果已登录 → return True
          3. 如果未登录：
             a. 找登录弹窗（verify_panel）
             b. 如果有一键登录按钮 → 点它
             c. 如果有验证码输入框 → 切 tab → 调 sms_login
             d. 如果无弹窗 → 点右上角「登录」触发弹窗
          4. 再次检查右上角 → 有 user-info 则成功
        """
        page = self.page
        await asyncio.sleep(6)  # 等页面稳定（抖音首页首次加载较慢）

        # ── 1. 检查当前登录状态 ──
        async def _has_avatar() -> bool:
            """右上角有头像/用户信息 = 已登录"""
            try:
                # 方法1: data-e2e 用户信息区
                info = await page.query_selector('[data-e2e="user-info"]')
                if info and await info.is_visible():
                    return True
                # 方法2: 右上角头像区域（无 e2e 时的 fallback）
                avatar = await page.query_selector('[class*="avatar"],[class*="Avatar"],[data-e2e*="avatar"]')
                if avatar and await avatar.is_visible():
                    return True
                # 方法3: 页面文本不含"登录"按钮字样
                has_login_btn = await page.query_selector('button:has-text("登录"), span:has-text("登录"), div:has-text("登录")')
                if not has_login_btn:
                    # 没有登录按钮 + 能拿到 user-info? 可能是变体
                    return False
                btn_visible = await has_login_btn.is_visible()
                return not btn_visible
            except:
                return False

        if await _has_avatar():
            print("  ✅ 已登录")
            return True

        print("  ⚠️ 未登录状态，检测登录弹窗...")

        # ── 2. 查找登录弹窗（优先找 iframe，因为手机号输入框在 iframe 内）──
        login_frame = page
        panel = None
        try:
            # 先检查 iframe（passport 登录域）
            for f in page.frames:
                url = f.url.lower()
                if "passport" in url or "login" in url or "sso" in url:
                    p = await f.query_selector(SELECTORS.get("verify_panel", '[class*="verify"]'))
                    if p:
                        panel = p
                        login_frame = f
                        break
            # iframe 没找到 → 检查主页面（遮罩层）
            if not panel:
                panel = await page.query_selector(SELECTORS.get("verify_panel", '[class*="verify"]'))
        except:
            pass

        # ── 3. 处理弹窗 ──
        if panel:
            print("  📱 检测到登录弹窗")
            # 3a. 检查是否是一键登录
            try:
                oneclick = await login_frame.query_selector('button:has-text("一键登录"), span:has-text("一键登录")')
                if oneclick and await oneclick.is_visible():
                    print("  ✅ 检测到一键登录 → 点击")
                    await oneclick.click()
                    await asyncio.sleep(5)
                    if await _has_avatar():
                        print("  ✅ 一键登录成功")
                        return True
                    # 一键登录可能跳到验证码页，继续走 sms
            except:
                pass

            # 3b. 检查是否是验证码登录界面（有手机号输入框）
            try:
                phone_inp = await login_frame.query_selector(SELECTORS["verify_phone_input"])
                if phone_inp and await phone_inp.is_visible():
                    print("  📱 检测到验证码登录界面 → 调用 sms_login")
                    return await self.sms_login(login_frame=login_frame)
            except:
                pass

            # 3c. 如果既不是一键也不是验证码，尝试切到验证码 tab
            try:
                for text in ["验证码登录", "手机号登录", "短信登录"]:
                    tab = await login_frame.query_selector(
                        f'div:has-text("{text}"), span:has-text("{text}"), label:has-text("{text}")'
                    )
                    if tab and await tab.is_visible():
                        await tab.click()
                        await asyncio.sleep(3)
                        print(f"  ✅ 切换到 {text}")
                        return await self.sms_login(login_frame=login_frame)
            except:
                pass
        else:
            # ── 4. 无弹窗 → 主动触发登录 ──
            print("  🔘 无登录弹窗，尝试点击登录按钮触发")
            try:
                login_btn = await page.query_selector(
                    'button:has-text("登录"), span:has-text("登录"), [data-e2e*="login"]'
                )
                if login_btn and await login_btn.is_visible():
                    await login_btn.click()
                    await asyncio.sleep(3)
                    # 递归检查弹窗
                    return await self._ensure_logged_in()
            except:
                pass
            print("  ❌ 找不到登录按钮或弹窗")
            return False

        # ── 5. 最终检查 ──
        await asyncio.sleep(3)
        if await _has_avatar():
            print("  ✅ 已登录")
            return True
        print("  ❌ 登录失败")
        return False

    async def sms_login(self, phone: str = "", step_id: int = 0, login_frame=None) -> bool:
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
        if login_frame is None:  # 未被 _ensure_logged_in 传入时才自己找
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

        # 5. 无论二维码是否可见，都尝试切换到"验证码登录"tab
        # （录制确认：抖音登录页默认显示二维码，需手动切tab）
        switched_tab = False
        for text in ["手机号登录", "手机登录", "短信登录", "验证码登录"]:
            try:
                tab = await login_frame.query_selector(f"div:has-text('{text}'), span:has-text('{text}'), label:has-text('{text}')")
                if tab and await tab.is_visible():
                    await tab.click()
                    await asyncio.sleep(3)  # 等 tab 切换动画 + 输入框渲染
                    print(f"  ✅ 切换到 {text}")
                    switched_tab = True
                    break
            except:
                continue

        if qr_visible and not switched_tab:
            print("⚠️ 检测到二维码但无法自动切换到手机号登录")
            return False

        # 6. 找手机号输入框并填入（带重试）
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

        # 尝试在 iframe 里找手机号输入框（带 3 次重试，防渲染延迟）
        phone_sel = "input[placeholder*='手机'], input[type='tel'], input[name='mobile'], input[id*='phone'], input[id*='mobile']"
        for retry in range(3):
            for sel in [phone_sel, "input:first-of-type"]:
                try:
                    inp = await login_frame.query_selector(sel)
                    if inp and await inp.is_visible():
                        await inp.click()
                        await asyncio.sleep(0.5)
                        if not phone_value:
                            print("❌ 未配置手机号，无法登录")
                            return False
                        await inp.fill(phone_value)
                        await asyncio.sleep(1)
                        phone_filled = True
                        print(f"  ✅ 已填手机号: {phone_value}")
                        break
                except:
                    continue
            if phone_filled:
                break
            await asyncio.sleep(1)  # 重试前等 1 秒

        if not phone_filled:
            # fallback: 填第一个可见 input
            try:
                inputs = await login_frame.query_selector_all("input:visible")
                if inputs and len(inputs) > 0:
                    if not phone_value:
                        print("❌ 未配置手机号，无法登录")
                        return False
                    await inputs[0].click()
                    await inputs[0].fill(phone_value)
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

        # 11. 检测"请使用抖音App登录"（验证码正确但账号需App登录）
        await asyncio.sleep(3)
        try:
            body_text = (await page.evaluate("document.body.innerText")) or ""
            for keyword in ["请使用抖音App登录", "请使用抖音 APP", "请使用抖音app"]:
                if keyword in body_text:
                    print(f"  ⛔ 检测到: {keyword} — 该账号需使用抖音App登录，短信已失效")
                    self._app_login_required = True
                    self._mark_app_login_required()
                    return False
        except:
            pass

        # 12. 等待登录结果（URL 变化 = 登录成功）
        await asyncio.sleep(5)
        current_url = page.url
        if "passport" not in current_url.lower() and "login" not in current_url.lower():
            print(f"  ✅ 登录成功! URL: {current_url[:60]}")
            return True
        # 兜底：即使 URL 还在登录域，但如果右上角有用户头像也视为成功
        try:
            info = await page.query_selector('[data-e2e="user-info"]')
            if info and await info.is_visible():
                print("  ✅ 右上角检测到用户信息，登录成功")
                return True
        except:
            pass
        print(f"  ⚠️ 登录后仍在登录页，可能需要手动处理")
        return False

    def _mark_app_login_required(self):
        """标记账号为"需使用抖音App登录" — 写入 profiles.json"""
        if not self._account_id:
            return
        try:
            from datetime import datetime
            PROFILES_JSON.parent.mkdir(parents=True, exist_ok=True)
            if PROFILES_JSON.exists():
                all_p = json.loads(PROFILES_JSON.read_text())
            else:
                all_p = {}
            all_p[self._account_id] = {
                **all_p.get(self._account_id, {}),
                "status": "app_login_required",
                "_status": "app_login_required",
                "status_detail": "需使用抖音App登录，短信验证码方式已失效",
                "platform": "douyin",
                "updated": datetime.now().isoformat(),
            }
            PROFILES_JSON.write_text(json.dumps(all_p, ensure_ascii=False, indent=2))
            print(f"  📝 profiles.json 已更新: {self._account_id} → app_login_required")
        except Exception as e:
            print(f"  ⚠️ _mark_app_login_required 写入失败: {e}")

    def _mark_sms_failed(self):
        """标记账号为'短信接收失败' — 写入 profiles.json"""
        if not self._account_id:
            return
        try:
            from datetime import datetime
            PROFILES_JSON.parent.mkdir(parents=True, exist_ok=True)
            if PROFILES_JSON.exists():
                all_p = json.loads(PROFILES_JSON.read_text())
            else:
                all_p = {}
            all_p[self._account_id] = {
                **all_p.get(self._account_id, {}),
                "status": "sms_failed",
                "_status": "sms_failed",
                "status_detail": "多次短信验证码接收失败，请检查手机号或短信服务",
                "platform": "douyin",
                "updated": datetime.now().isoformat(),
            }
            PROFILES_JSON.write_text(json.dumps(all_p, ensure_ascii=False, indent=2))
            print(f"  📝 profiles.json 已更新: {self._account_id} → sms_failed")
        except Exception as e:
            print(f"  ⚠️ _mark_sms_failed 写入失败: {e}")

    _SMS_FAIL_FILE = Path(str(PROFILES_JSON.parent / "sms_failures.json"))

    def _track_sms_failure(self) -> bool:
        """记录一次短信接收失败，连续2次返回 True（触发标记）"""
        if not self._account_id:
            return False
        try:
            self._SMS_FAIL_FILE.parent.mkdir(parents=True, exist_ok=True)
            fails = {}
            if self._SMS_FAIL_FILE.exists():
                fails = json.loads(self._SMS_FAIL_FILE.read_text())
            acct = fails.get(self._account_id, {"count": 0})
            acct["count"] = acct.get("count", 0) + 1
            acct["last_attempt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            fails[self._account_id] = acct
            self._SMS_FAIL_FILE.write_text(json.dumps(fails, ensure_ascii=False, indent=2))
            print(f"  📡 SMS 接收失败 #{acct['count']} [{self._account_id}]")
            return acct["count"] >= 2
        except:
            return False

    def _reset_sms_failures(self):
        """SMS 成功后重置失败计数"""
        if not self._account_id:
            return
        try:
            if self._SMS_FAIL_FILE.exists():
                fails = json.loads(self._SMS_FAIL_FILE.read_text())
                if self._account_id in fails:
                    del fails[self._account_id]
                    self._SMS_FAIL_FILE.write_text(json.dumps(fails, ensure_ascii=False, indent=2))
        except:
            pass

    def get_action_summary(self) -> dict:
        """获取本次会话的操作统计"""
        return {
            **self._action_counts,
            "elapsed_minutes": round(self._elapsed_hours() * 60, 1),
        }