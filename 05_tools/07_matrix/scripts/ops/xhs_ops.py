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

from ops._base import PlatformOps, OpResult, Condition

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
            "xhs_click_next_image", "xhs_click_prev_image",
            "xhs_like", "xhs_collect", "xhs_comment", "xhs_follow", "xhs_search",
            "xhs_post_comment",
            "xhs_goto_profile",
            "xhs_read_nickname", "xhs_read_user_id", "xhs_read_following",
            "xhs_read_fans", "xhs_read_likes", "xhs_read_bio",
            "wait_watch", "go_back", "goto_url",
        ]

    def set_account_id(self, account_id: str):
        """设置当前账号ID，供写 profiles.json"""
        self._account_id = account_id

    # ── 三段式操作模型 v2.0 ──────────────────────────────────

    STATE_SELECTORS = [
        'section.note-item',                 # feed 中的笔记
        'span.like-lottie',                  # 点赞按钮
        '[class*="collect"]',                # 收藏
        '[class*="follow"]',                 # 关注
        'input[placeholder*="搜索"]',        # 搜索框
        'textarea.textarea',                 # 小红书搜索输入框
        'p#content-textarea',                # 评论输入框（有ID，稳定）
        'button.btn.submit',                 # 发评论按钮
        'img.preview-interactive',           # 图片翻页
        'img.avatar-item',                   # 头像
        'a.cover.mask',                      # 笔记封面链接
        'div.continue',                      # 登录继续按钮
        'input#verificationCodeInput',       # 验证码输入框（有ID）
        'span.login-text',                   # 登录按钮
        'div.foot-btn',                      # 同意并登录
        '.reds-count',                       # 登录态指示器
        '.login-container',                  # 登录面板
        'a.bottom-channel',                  # 底栏导航
    ]

    def _get_pre_conditions(self, op: str) -> list[Condition]:
        conds = {
            "xhs_like": [
                Condition("page_mode", "page_mode", "player", message="需要在笔记详情页"),
            ],
            "xhs_collect": [
                Condition("page_mode", "page_mode", "player", message="需要在笔记详情页"),
            ],
            "xhs_comment": [
                Condition("page_mode", "page_mode", "player", message="需要在笔记详情页"),
            ],
            "xhs_follow": [
                Condition("page_mode", "page_mode", "profile", message="需要在用户主页"),
            ],
            "xhs_scroll_feed": [
                Condition("page_mode", "page_mode", "grid", message="需要在发现页"),
            ],
            "xhs_click_note": [
                Condition("page_mode", "page_mode", "grid", message="需要在发现页"),
            ],
            "xhs_search": [
                Condition("selector", 'input[placeholder*="搜索"]', True,
                          message="需要搜索框可见"),
            ],
            "xhs_click_next_image": [
                Condition("page_mode", "page_mode", "player", message="需要在笔记详情页"),
            ],
            "xhs_click_prev_image": [
                Condition("page_mode", "page_mode", "player", message="需要在笔记详情页"),
            ],
            "xhs_post_comment": [
                Condition("page_mode", "page_mode", "player", message="需要在笔记详情页"),
            ],
            "xhs_goto_home": [],
            "xhs_browse": [],
            "xhs_goto_profile": [],
            "xhs_read_nickname": [],
            "xhs_read_user_id": [],
            "xhs_read_following": [],
            "xhs_read_fans": [],
            "xhs_read_likes": [],
            "xhs_read_bio": [],
            "wait_watch": [],
            "go_back": [],
        }
        return conds.get(op, [])

    def _get_post_conditions(self, op: str) -> list[Condition]:
        conds = {
            "xhs_goto_home": [
                Condition("page_mode", "page_mode", "grid", message="应回到发现页"),
            ],
            "xhs_like": [
                Condition("selector", '[class*="like"]', True,
                          message="点赞按钮应仍在页面"),
            ],
        }
        return conds.get(op, [])

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
        # 策略1: a.cover 点击（录制确认最稳定）
        try:
            cover = self.page.locator('a.cover.mask, a.cover')
            if await cover.count() > 0:
                await cover.first.click()
                await asyncio.sleep(4)
                return OpResult("xhs_click_note", step_id, True, "note_opened")
        except:
            pass
        # 策略2: 通用选择器（原有）
        note = self.page.locator('section.note-item, a[href*="/explore/"], [class*="note-item"]').first
        if await note.count() > 0:
            await note.click()
            await asyncio.sleep(4)
            return OpResult("xhs_click_note", step_id, True, "note_opened")
        # 回到首页重试
        await self.page.goto("https://www.xiaohongshu.com/explore", timeout=15000, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        note2 = self.page.locator('section.note-item, a[href*="/explore/"], [class*="note-item"]').first
        if await note2.count() > 0:
            await note2.click()
            await asyncio.sleep(4)
            return OpResult("xhs_click_note", step_id, True, "note_opened_retry")
        return OpResult("xhs_click_note", step_id, False, "no_note")

    async def xhs_click_next_image(self, args: dict, step_id: int) -> OpResult:
        """图片笔记向右翻页 — 点击右侧SVG区域（两次录制确认 (677,268)）"""
        # 策略1: 坐标点击（录制确认右侧 ~(677,268)）
        try:
            await self.page.mouse.click(677, 268)
            await asyncio.sleep(1.5)
            return OpResult("xhs_click_next_image", step_id, True, "next")
        except:
            pass
        # 策略2: img.preview-interactive 点击（在预览模式中翻页）
        try:
            pi = self.page.locator('img.preview-interactive')
            if await pi.count() > 0:
                await pi.first.click()
                await asyncio.sleep(1.5)
                return OpResult("xhs_click_next_image", step_id, True, "next")
        except:
            pass
        return OpResult("xhs_click_next_image", step_id, False, "no_next_btn")

    async def xhs_click_prev_image(self, args: dict, step_id: int) -> OpResult:
        """图片笔记向左翻页 — 点击左侧SVG区域（录制确认 (28,274)）"""
        # 策略1: 坐标点击（录制确认左侧 ~(28,274)）
        try:
            await self.page.mouse.click(28, 274)
            await asyncio.sleep(1.5)
            return OpResult("xhs_click_prev_image", step_id, True, "prev")
        except:
            pass
        # 策略2: 备用坐标（略右移）
        try:
            await self.page.mouse.click(70, 274)
            await asyncio.sleep(1.5)
            return OpResult("xhs_click_prev_image", step_id, True, "prev")
        except:
            pass
        return OpResult("xhs_click_prev_image", step_id, False, "no_prev_btn")

    # ═══════════════════════════════════════════════════════
    # 互动类
    # ═══════════════════════════════════════════════════════

    async def xhs_like(self, args: dict, step_id: int) -> OpResult:
        """点赞 — 点 SPAN.like-lottie（force=True 绕过可见性检查）"""
        try:
            btn = self.page.locator('span.like-lottie')
            if await btn.count() > 0:
                await btn.first.click(force=True)
                await asyncio.sleep(1)
                return OpResult("xhs_like", step_id, True, "👍")
        except:
            pass
        # 快速兜底
        r = await self.page.evaluate("""() => {
            const all = document.querySelectorAll('span, button, div');
            for (const el of all) {
                const c = (el.className || '') + (el.textContent || '');
                if ((c.includes('like') || c.includes('赞')) && el.offsetParent) {
                    if (c.includes('collect') || c.includes('save')) continue;
                    el.click(); return '👍';
                }
            }
            return '-';
        }""")
        await asyncio.sleep(1)
        return OpResult("xhs_like", step_id, r == "👍", r)

    async def xhs_collect(self, args: dict, step_id: int) -> OpResult:
        """收藏 — 底栏第二位（点赞在左，收藏在点赞+45px处）"""
        # 策略1: 找点赞按钮位置，点击右侧45px（两次录制确认）
        try:
            like = self.page.locator('span.like-lottie')
            if await like.count() > 0:
                box = await like.first.bounding_box()
                if box:
                    await self.page.mouse.click(box['x'] + 45, box['y'])
                    await asyncio.sleep(1)
                    return OpResult("xhs_collect", step_id, True, "⭐")
        except:
            pass
        # 策略2: SVG 兜底（录制显示收藏是 svg 标签）
        try:
            likes = self.page.locator('span.like-lottie')
            if await likes.count() > 0:
                svgs = self.page.locator('span.like-lottie ~ svg, span.like-lottie + svg')
                if await svgs.count() > 0:
                    await svgs.first.click(force=True)
                    await asyncio.sleep(1)
                    return OpResult("xhs_collect", step_id, True, "⭐svg")
        except:
            pass
        # 策略3: JS查找收藏class
        r = await self.page.evaluate("""() => {
            const btns = document.querySelectorAll('[class*="collect"],[class*="save"]');
            for (const b of btns) {
                if (b.offsetParent !== null) { b.click(); return '⭐'; }
            }
            return '-';
        }""")
        await asyncio.sleep(1)
        return OpResult("xhs_collect", step_id, r == "⭐", r)

    async def xhs_comment(self, args: dict, step_id: int) -> OpResult:
        await self.page.keyboard.press("x")
        await asyncio.sleep(2)
        return OpResult("xhs_comment", step_id, True, "comment_opened")

    async def xhs_follow(self, args: dict, step_id: int) -> OpResult:
        """关注 — 点 SPAN.reds-button-new-text（基于录制）"""
        try:
            btn = self.page.locator('span.reds-button-new-text')
            if await btn.count() > 0:
                await btn.first.click(force=True)
                await asyncio.sleep(2)
                return OpResult("xhs_follow", step_id, True, "✅")
        except:
            pass
        # 兜底
        r = await self.page.evaluate("""() => {
            const btns = document.querySelectorAll('button, span');
            for (const b of btns) {
                const t = (b.textContent || '').trim();
                if (t.includes('关注') && !t.includes('已关注') && b.offsetParent) { b.click(); return '✅'; }
            }
            return '-';
        }""")
        await asyncio.sleep(2)
        return OpResult("xhs_follow", step_id, r == "✅", r)

    async def xhs_post_comment(self, args: dict, step_id: int) -> OpResult:
        """小红书发评论 — 优先用ID选择器 p#content-textarea，再 fallback"""
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
            # Step 1: 滑到底部（评论区在底部）
            await self.page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            # Step 2: 优先用 ID 选择器 p#content-textarea（录制确认稳定）
            filled = False
            try:
                inp = self.page.locator('p#content-textarea')
                if await inp.count() > 0 and await inp.first.is_visible():
                    await inp.first.click()
                    await asyncio.sleep(0.5)
                    proc = await asyncio.create_subprocess_exec("pbcopy", stdin=asyncio.subprocess.PIPE)
                    await proc.communicate(input=text.encode())
                    await asyncio.sleep(0.5)
                    await self.page.keyboard.press("Meta+V")
                    await asyncio.sleep(1.5)
                    filled = True
            except:
                pass
            
            # Fallback: JS 填字（原有的）
            if not filled:
                filled = await self.page.evaluate(f"""() => {{
                    const all = document.querySelectorAll(
                        'textarea, input[type="text"], [contenteditable="true"], ' +
                        '[class*="input"], [class*="editor"], [class*="textarea"]'
                    );
                    for (const el of all) {{
                        if (el.offsetParent !== null) {{
                            el.focus();
                            el.click();
                            const sel = window.getSelection();
                            const range = document.createRange();
                            range.selectNodeContents(el);
                            sel.removeAllRanges();
                            sel.addRange(range);
                            document.execCommand('insertText', false, '{text}');
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            return true;
                        }}
                    }}
                    return false;
                }}""")
            await asyncio.sleep(1)
            
            # Step 3: 如果JS填字失败，pbcopy 兜底
            if not filled:
                proc = await asyncio.create_subprocess_exec("pbcopy", stdin=asyncio.subprocess.PIPE)
                await proc.communicate(input=text.encode())
                await asyncio.sleep(0.5)
                await self.page.keyboard.press("Meta+V")
                await asyncio.sleep(1.5)
            
            # Step 4: 找发送按钮（找包含"发送"文本/class含submit的按钮）
            sent = await self.page.evaluate("""() => {
                const btns = document.querySelectorAll('button, [class*="submit"], [class*="send"]');
                for (const b of btns) {
                    const t = (b.textContent || '').trim();
                    if ((t.includes('发送') || t.includes('发布') || b.className.includes('submit')) 
                        && b.offsetParent) {
                        b.click(); return true;
                    }
                }
                return false;
            }""")
            if not sent:
                # 没找到发送按钮 → Enter发送
                await self.page.keyboard.press("Enter")
            
            await asyncio.sleep(2)
            return OpResult("xhs_post_comment", step_id, True, f"👍评论({text[:10]})")
        except Exception as e:
            return OpResult("xhs_post_comment", step_id, False, "评论失败", error=str(e))

    async def xhs_search(self, args: dict, step_id: int) -> OpResult:
        kw = args.get("keyword", "热门推荐")
        if kw == "@random":
            import random as _r
            kw = _r.choice(["穿搭推荐","美食日常","旅行攻略","化妆教程","家居好物",
                            "宠物日常","电影推荐","读书分享","健身打卡","摄影技巧"])
        try:
            # 小红书搜索栏是 TEXTAREA.textarea（非 input）
            search_box = self.page.locator('textarea.textarea')
            if await search_box.count() > 0:
                await search_box.first.click()
                await asyncio.sleep(0.5)
                await search_box.first.fill(kw)
                await asyncio.sleep(1)
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(3)
                return OpResult("xhs_search", step_id, True, f"searched({kw[:10]})")
        except:
            pass
        # 兜底
        try:
            await self.page.evaluate(
                "(k) => { const i = document.querySelector('input,textarea'); if(i) { i.value=k; i.dispatchEvent(new Event('input')); } }",
                kw
            )
            await asyncio.sleep(1)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(3)
            return OpResult("xhs_search", step_id, True, f"searched({kw[:10]})")
        except Exception as e:
            return OpResult("xhs_search", step_id, False, "search_failed", error=str(e))

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

        # 2.5 检测封禁状态
        ban_status = await self.check_banned_status()
        profile["_status"] = ban_status
        log.info(
            f"      📊 小红书主页: {profile.get('nickname','?')}"
            f" ID={profile.get('user_id','?')}"
            f" 关注={profile.get('following','?')}"
            f" 粉丝={profile.get('fans','?')}"
            f" 获赞={profile.get('likes','?')}"
            f" 笔记={profile.get('posts','?')}"
            f" 状态={ban_status}"
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
    # 内部 + 通用操作
    # ═══════════════════════════════════════════════════════

    async def wait_watch(self, args: dict, step_id: int) -> OpResult:
        """等待观看（随机5-15秒）"""
        import random
        seconds = args.get("seconds") or random.randint(5, 15)
        await asyncio.sleep(seconds)
        return OpResult("wait_watch", step_id, True, f"watched_{seconds}s")

    async def go_back(self, args: dict, step_id: int) -> OpResult:
        """返回上一页"""
        try:
            await self.page.go_back(wait_until="domcontentloaded")
            await asyncio.sleep(2)
            return OpResult("go_back", step_id, True, "back")
        except Exception as e:
            return OpResult("go_back", step_id, True, "back_fallback")

    async def goto_url(self, args: dict, step_id: int) -> OpResult:
        """跳转到指定URL（定向评论用）"""
        url = args.get("url", XHS_HOME_URL)
        try:
            await self.page.goto(url, timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(4)
            return OpResult("goto_url", step_id, True, f"goto {url[:30]}")
        except Exception as e:
            return OpResult("goto_url", step_id, False, "goto_fail", error=str(e))

    async def check_banned_status(self) -> str:
        """检测小红书账号是否被封禁
        Returns: "normal" / "banned" / "unknown"
        """
        try:
            text = (await self.page.evaluate("document.body.innerText")) or ""
            # 个人主页：含有"违反"+"社区规范"关键词
            if "违反" in text and "社区规范" in text:
                return "banned"
            # 操作弹窗：div.banned-title 可见
            try:
                bt = self.page.locator('div.banned-title')
                if await bt.count() > 0 and await bt.first.is_visible():
                    return "banned"
            except:
                pass
        except:
            pass
        return "normal"

    def _save_profiles_json(self):
        """保存主页信息到 profiles.json + homepage_info.json（两个 Dashboard 数据源）"""
        if not self._account_id:
            return
        try:
            cache = self._profile_cache
            status = cache.get("_status", "normal")

            # ── 写 profiles.json（供账号管理页面读取）──
            if PROFILES_JSON.exists():
                all_p = json.loads(PROFILES_JSON.read_text())
            else:
                all_p = {}
            PROFILES_JSON.parent.mkdir(parents=True, exist_ok=True)
            all_p[self._account_id] = {
                "nickname": cache.get("nickname", "?"),
                "user_id": cache.get("user_id", "?"),
                "following": cache.get("following", "?"),
                "fans": cache.get("fans", "?"),
                "likes": cache.get("likes", "?"),
                "posts": cache.get("posts", "?"),
                "bio": cache.get("bio", "?"),
                "status": status,
                "platform": "xiaohongshu",
                "updated": datetime.now().isoformat(),
            }
            PROFILES_JSON.write_text(json.dumps(all_p, ensure_ascii=False, indent=2))

            # ── 同步写 homepage_info.json（供信息采集页面读取）──
            hp_path = PROFILES_JSON.parent / "homepage_info.json"
            hp_data = {"collected_at": datetime.now().isoformat(), "results": []}
            if hp_path.exists():
                try:
                    hp_data = json.loads(hp_path.read_text())
                except Exception:
                    hp_data = {"collected_at": datetime.now().isoformat(), "results": []}
            # 查找或创建当前账号的记录
            entry = None
            for r in hp_data.get("results", []):
                rid = r.get("identity_dir", "").replace("identities/", "")
                if rid == self._account_id or r.get("phone") == cache.get("phone", self._account_id):
                    entry = r
                    break
            if not entry:
                hp_data.setdefault("results", []).append({
                    "identity_dir": f"identities/{self._account_id}",
                    "phone": cache.get("phone", self._account_id),
                    "douyin": None, "xiaohongshu": {}
                })
                entry = hp_data["results"][-1]
            # 确保 xiaohongshu 字段存在
            if entry.get("xiaohongshu") is None:
                entry["xiaohongshu"] = {}
            entry["xiaohongshu"].update({
                "nickname": cache.get("nickname", ""),
                "fans": cache.get("fans", "0"),
                "following": cache.get("following", "0"),
                "likes": cache.get("likes", "0"),
                "notes": cache.get("posts", "0"),
                "bio": cache.get("bio", ""),
                "status": status,
                "updated": datetime.now().isoformat(),
            })
            hp_path.write_text(json.dumps(hp_data, ensure_ascii=False, indent=2))

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"_save_profiles_json 失败: {e}")
