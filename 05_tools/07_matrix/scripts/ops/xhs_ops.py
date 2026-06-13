"""
ops/xhs_ops.py — 小红书平台操作 v1.0
从 mc/engine.py (v4.3) 提取，实现 PlatformOps 接口。

操作清单 (16个):
  导航:     xhs_goto_home, xhs_browse
  互动:     xhs_like, xhs_collect, xhs_comment, xhs_follow
  内容:     xhs_click_note, xhs_scroll_feed, xhs_search
  主页:     xhs_goto_profile, xhs_read_nickname, xhs_read_user_id,
            xhs_read_following, xhs_read_fans, xhs_read_likes, xhs_read_bio
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ops._base import PlatformOps, OpResult

log = logging.getLogger(__name__)

HOME = Path.home()
PROFILES_JSON = HOME / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "data" / "profiles.json"
XHS_HOME_URL = "https://www.xiaohongshu.com/explore"


class XhsOps(PlatformOps):
    """小红书平台操作库"""

    name = "xiaohongshu"

    def __init__(self, page):
        self.page = page
        self._profile_cache: dict = {}       # goto_profile 后缓存
        self._account_id: str = ""           # 由 engine 设置，写 profiles.json 用

    def supported_ops(self) -> list[str]:
        return [
            "xhs_goto_home", "xhs_browse", "xhs_scroll_feed", "xhs_click_note",
            "xhs_like", "xhs_collect", "xhs_comment", "xhs_follow", "xhs_search",
            "xhs_post_comment",
            "xhs_goto_profile",
            "xhs_read_nickname", "xhs_read_user_id", "xhs_read_following",
            "xhs_read_fans", "xhs_read_likes", "xhs_read_bio",
        ]

    def set_account_id(self, account_id: str):
        """设置当前账号ID，供写 profiles.json"""
        self._account_id = account_id

    # ── PlatformOps 入口 ────────────────────────────────────

    async def _do_execute(self, op: str, args: dict, step_id: int) -> Optional[OpResult]:
        method = getattr(self, op, None)
        if method is None:
            return OpResult(op, step_id, False, "unsupported", 0, f"未知操作: {op}")
        return await method(args, step_id)

    # ═══════════════════════════════════════════════════════
    # 导航类
    # ═══════════════════════════════════════════════════════

    async def xhs_goto_home(self, args: dict, step_id: int) -> OpResult:
        await self.page.goto(XHS_HOME_URL, timeout=20000, wait_until="domcontentloaded")
        await asyncio.sleep(4)
        return OpResult("xhs_goto_home", step_id, True, "home_loaded")

    async def xhs_browse(self, args: dict, step_id: int) -> OpResult:
        if "explore" not in self.page.url:
            await self.page.goto(XHS_HOME_URL, timeout=15000, wait_until="domcontentloaded")
            await asyncio.sleep(3)
        return OpResult("xhs_browse", step_id, True, "browsing")

    async def xhs_scroll_feed(self, args: dict, step_id: int) -> OpResult:
        await self.page.evaluate("() => window.scrollBy(0, 800)")
        await asyncio.sleep(2)
        return OpResult("xhs_scroll_feed", step_id, True, "scrolled")

    async def xhs_click_note(self, args: dict, step_id: int) -> OpResult:
        note = self.page.locator('section.note-item, a[href*="/explore/"], [class*="note-item"]').first
        if await note.count() > 0:
            await note.click()
            await asyncio.sleep(4)
            return OpResult("xhs_click_note", step_id, True, "note_opened")
        return OpResult("xhs_click_note", step_id, True, "no_note")

    # ═══════════════════════════════════════════════════════
    # 互动类
    # ═══════════════════════════════════════════════════════

    async def xhs_like(self, args: dict, step_id: int) -> OpResult:
        r = await self.page.evaluate("""() => {
            const btns = document.querySelectorAll('[class*="like"],[data-testid*="like"]');
            for (const b of btns) {
                if (b.offsetParent !== null) { b.click(); return '👍'; }
            }
            return '-';
        }""")
        await asyncio.sleep(1)
        ok = r == "👍"
        return OpResult("xhs_like", step_id, ok, r, error="" if ok else "like_not_found")

    async def xhs_collect(self, args: dict, step_id: int) -> OpResult:
        r = await self.page.evaluate("""() => {
            const btns = document.querySelectorAll('[class*="collect"],[class*="save"]');
            for (const b of btns) {
                if (b.offsetParent !== null) { b.click(); return '⭐'; }
            }
            return '-';
        }""")
        await asyncio.sleep(1)
        ok = r == "⭐"
        return OpResult("xhs_collect", step_id, ok, r, error="" if ok else "collect_not_found")

    async def xhs_comment(self, args: dict, step_id: int) -> OpResult:
        await self.page.keyboard.press("x")
        await asyncio.sleep(2)
        return OpResult("xhs_comment", step_id, True, "comment_opened")

    async def xhs_follow(self, args: dict, step_id: int) -> OpResult:
        r = await self.page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                const t = (b.textContent || '').trim();
                if (t.includes('关注') && !t.includes('已关注')) { b.click(); return '✅'; }
            }
            return '-';
        }""")
        ok = r == "✅"
        return OpResult("xhs_follow", step_id, ok, r, error="" if ok else "follow_not_found")

    async def xhs_post_comment(self, args: dict, step_id: int) -> OpResult:
        """小红书发评论 — pbcopy + Meta+V + Enter"""
        text = args.get("text", "")
        if not text or text == "@corpus":
            try:
                from mc.corpus import CorpusManager
                cm = CorpusManager()
                picks = cm.get_comments(platform="xiaohongshu", count=5)
                if picks:
                    text = random.choice(picks)
                else:
                    text = "好实用呀"
            except Exception:
                text = "好实用呀"
        try:
            proc = await asyncio.create_subprocess_exec("pbcopy", stdin=asyncio.subprocess.PIPE)
            await proc.communicate(input=text.encode())
            await asyncio.sleep(0.5)
            await self.page.keyboard.press("Meta+V")
            await asyncio.sleep(1.5)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(2)
            return OpResult("xhs_post_comment", step_id, True, f"👍评论({text[:10]})")
        except Exception as e:
            return OpResult("xhs_post_comment", step_id, False, "评论失败", error=str(e))

    async def xhs_search(self, args: dict, step_id: int) -> OpResult:
        kw = args.get("keyword", "热门推荐")
        await self.page.evaluate(
            "(k) => { const i = document.querySelector('input'); if(i) { i.value=k; i.dispatchEvent(new Event('input')); } }",
            kw
        )
        await asyncio.sleep(1)
        await self.page.keyboard.press("Enter")
        await asyncio.sleep(3)
        return OpResult("xhs_search", step_id, True, f"searched({kw[:10]})")

    # ═══════════════════════════════════════════════════════
    # 主页信息采集
    # ═══════════════════════════════════════════════════════

    async def xhs_goto_profile(self, args: dict, step_id: int) -> OpResult:
        """导航到个人主页并提取全部字段到 profile_cache"""
        # 1. 从页面找 profile URL
        profile_url = await self.page.evaluate("""() => {
            const links = document.querySelectorAll('a');
            for (const a of links) {
                const href = a.href || '';
                if (href.includes('/user/profile/')) return href;
            }
            return '';
        }""")
        target = profile_url or "https://www.xiaohongshu.com/user/profile"
        await self.page.goto(target, timeout=20000, wait_until="domcontentloaded")
        await asyncio.sleep(5)

        # 2. 统一提取全部字段
        profile = await self.page.evaluate("""() => {
            const text = (document.body.innerText || '').trim();
            const title = (document.title || '').replace(' - 小红书', '').trim();

            const uidM = text.match(/小红书号[：:]\\s*(\\d+)/);
            const folM = text.match(/(\\d+(?:\\.\\d+)?[万wW]?)\\s*关注/);
            const fanM = text.match(/(\\d+(?:\\.\\d+)?[万wW]?)\\s*粉丝/);
            const likM = text.match(/(\\d+(?:\\.\\d+)?[万wW]?)\\s*获赞与收藏/);
            const posM = text.match(/笔记[・·](\\d+(?:\\.\\d+)?[万wW]?)/);

            let bio = '(无)';
            if (text.includes('还没有简介') || text.includes('暂无简介')) {
                bio = '(无)';
            } else {
                const bioM = text.match(/IP属地[：:].+?\\n(.+?)(?=\\d+关注|\\d+粉丝)/);
                if (bioM) bio = bioM[1].trim().slice(0, 50) || '(无)';
            }

            return { nickname: title, user_id: uidM ? uidM[1] : '?',
                     following: folM ? folM[1] : '?', fans: fanM ? fanM[1] : '?',
                     likes: likM ? likM[1] : '?', posts: posM ? posM[1] : '?',
                     bio: bio };
        }""")

        self._profile_cache = profile

        log.info(
            f"      📊 小红书主页: {profile.get('nickname','?')}"
            f" ID={profile.get('user_id','?')}"
            f" 关注={profile.get('following','?')}"
            f" 粉丝={profile.get('fans','?')}"
            f" 获赞={profile.get('likes','?')}"
            f" 笔记={profile.get('posts','?')}"
        )

        # 3. 保存到 profiles.json
        self._save_profiles_json()

        return OpResult("xhs_goto_profile", step_id, True, "profile_loaded")

    # ═══════════════════════════════════════════════════════
    # 读缓存字段
    # ═══════════════════════════════════════════════════════

    async def xhs_read_nickname(self, args: dict, step_id: int) -> OpResult:
        v = self._profile_cache.get("nickname", "?")
        log.info(f"      📝 昵称: {v} (cached)")
        return OpResult("xhs_read_nickname", step_id, True, f"nickname={v}")

    async def xhs_read_user_id(self, args: dict, step_id: int) -> OpResult:
        v = self._profile_cache.get("user_id", "?")
        log.info(f"      🔢 ID: {v} (cached)")
        return OpResult("xhs_read_user_id", step_id, True, f"user_id={v}")

    async def xhs_read_following(self, args: dict, step_id: int) -> OpResult:
        v = self._profile_cache.get("following", "?")
        log.info(f"      👥 关注: {v} (cached)")
        return OpResult("xhs_read_following", step_id, True, f"following={v}")

    async def xhs_read_fans(self, args: dict, step_id: int) -> OpResult:
        v = self._profile_cache.get("fans", "?")
        log.info(f"      👥 粉丝: {v} (cached)")
        return OpResult("xhs_read_fans", step_id, True, f"fans={v}")

    async def xhs_read_likes(self, args: dict, step_id: int) -> OpResult:
        v = self._profile_cache.get("likes", "?")
        log.info(f"      👍 获赞: {v} (cached)")
        return OpResult("xhs_read_likes", step_id, True, f"likes={v}")

    async def xhs_read_bio(self, args: dict, step_id: int) -> OpResult:
        v = self._profile_cache.get("bio", "?")
        log.info(f"      📄 简介: {v} (cached)")
        return OpResult("xhs_read_bio", step_id, True, f"bio={v}")

    # ═══════════════════════════════════════════════════════
    # 内部
    # ═══════════════════════════════════════════════════════

    def _save_profiles_json(self):
        """保存主页信息到 profiles.json（供 Dashboard 读取）"""
        if not self._account_id:
            return
        try:
            if PROFILES_JSON.exists():
                all_p = json.loads(PROFILES_JSON.read_text())
            else:
                all_p = {}
            PROFILES_JSON.parent.mkdir(parents=True, exist_ok=True)
            all_p[self._account_id] = {
                "nickname": self._profile_cache.get("nickname", "?"),
                "user_id": self._profile_cache.get("user_id", "?"),
                "following": self._profile_cache.get("following", "?"),
                "fans": self._profile_cache.get("fans", "?"),
                "likes": self._profile_cache.get("likes", "?"),
                "posts": self._profile_cache.get("posts", "?"),
                "platform": "xiaohongshu",
                "updated": datetime.now().isoformat(),
            }
            PROFILES_JSON.write_text(json.dumps(all_p, ensure_ascii=False, indent=2))
        except Exception:
            pass
