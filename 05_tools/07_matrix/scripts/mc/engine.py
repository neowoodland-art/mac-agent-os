"""
engine.py — mc run 真实执行引擎（v1.2 — 并行版）

不再依赖旧 orchestrator（Chrome CDP 模式），
改为直接使用 Camoufox 加载身份 cookie 执行。

<batch_run 流程>
  mc run --accounts X --blueprints Y
    → BatchEngine.run()
      → prepare() 所有账号（清理残留锁/PID）
      → asyncio.gather( _run_account_all_rounds(a) for a in accounts )
        └── _run_account_all_rounds(a) —— 每账号一个浏览器，跑完全部轮次
            1. 检查 cookie 有效性（跳过无效的）
            2. 用 Camoufox 启动身份目录
            3. 打开抖音/小红书首页
            4. 执行蓝图步骤（通过 atom_ops）
            5. 等待跨轮间隔
            6. 回到 3 继续下一轮
            7. 全部完成后关闭浏览器
      → 汇总所有报告

<并行设计>
  旧版 (v1.1): for round → for account → run_single（每轮每账号开闭浏览器）
  新版 (v1.2): asyncio.gather — 每个账号一个持久连接，跑完所有轮次
               浏览器启停: N×R 次 → N 次（N=账号数, R=轮次数）
               总耗时: sum(A,B,C,...) → max(A,B,C,...)

<共享浏览器>
  _run_account_all_rounds() 创建 CDPConnector 后传入 run_single(conn=...)，
  run_single 检测 own_conn 标志决定是否创建/关闭浏览器。
"""
import asyncio
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
TOOL_DIR = SCRIPTS_DIR.parent
AGENT_SYNC = Path.home() / "workbuddy-agent-os" / "agent-sync"
AGENT_LOCAL = Path.home() / "workbuddy-agent-os" / "agent-local"
IDENTITIES_ROOT = AGENT_LOCAL / "tools" / "matrix" / "identities"
sys.path.insert(0, str(SCRIPTS_DIR))


# ════════════════════════════════════════════════════════════
# 工具函数
# ════════════════════════════════════════════════════════════

def resolve_account(account_id: str) -> dict:
    """从 registry 获取账号配置"""
    from matrix_mgmt import MatrixManager
    mgr = MatrixManager()
    for a in mgr.list_accounts():
        if a["id"] == account_id:
            return a
    raise ValueError(f"账号不存在: {account_id}")


def resolve_blueprint(name: str) -> Optional[dict]:
    """解析蓝图"""
    bp_dir = TOOL_DIR / "blueprints"
    for f in sorted(bp_dir.glob("*.json")):
        bp = json.loads(f.read_text())
        if name in (bp.get("id", ""), bp.get("name", ""), f.stem):
            return bp
        if name in f.stem or f.stem in name:
            return json.loads(f.read_text())
    return None


def check_cookie(identity_hint: str) -> str:
    """检查身份目录 cookie 状态
    返回: 'ok' | 'no_cookie' | 'expired' | 'no_identity'
    """
    if not identity_hint:
        return "no_identity"
    ident_dir = IDENTITIES_ROOT / identity_hint
    if not ident_dir.exists():
        return "no_identity"
    ck = ident_dir / "user_data" / "cookies.sqlite"
    if not ck.exists() or ck.stat().st_size < 100:
        return "no_cookie"
    try:
        import sqlite3
        conn = sqlite3.connect(str(ck), timeout=2)
        cnt = conn.execute("SELECT count(*) FROM moz_cookies WHERE name LIKE '%session%'").fetchone()[0]
        conn.close()
        return "ok" if cnt > 0 else "expired"
    except:
        return "error"


# ════════════════════════════════════════════════════════════
# 执行报告
# ════════════════════════════════════════════════════════════

class StepResult:
    def __init__(self, op: str, step_id: int, success: bool = True,
                 duration: float = 0, error: str = ""):
        self.op = op
        self.step_id = step_id
        self.success = success
        self.duration = duration
        self.error = error

    def __str__(self):
        icon = "✅" if self.success else "❌"
        return f"{icon} [{self.step_id:2d}] {self.op:20s} ({self.duration:.1f}s) {self.error}"


class AccountRunReport:
    def __init__(self, account: str, blueprint: str, round_idx: int):
        self.account = account
        self.blueprint = blueprint
        self.round = round_idx
        self.steps: List[StepResult] = []
        self.start = time.time()
        self.success = 0
        self.failed = 0
        self.skipped = False

    @property
    def duration(self) -> float:
        return time.time() - self.start

    def add_step(self, result: StepResult):
        self.steps.append(result)
        if result.success:
            self.success += 1
        else:
            self.failed += 1

    def to_dict(self) -> dict:
        return {
            "account": self.account,
            "blueprint": self.blueprint,
            "round": self.round,
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "duration": round(self.duration, 1),
            "steps": [{"op": s.op, "step_id": s.step_id, "success": s.success,
                       "duration": round(s.duration, 1), "error": s.error} for s in self.steps],
        }


class BatchReport:
    def __init__(self):
        self.accounts: List[str] = []
        self.blueprints: List[str] = []
        self.rounds_total = 0
        self.mix_mode = False
        self.start = time.time()
        self.account_reports: List[AccountRunReport] = []
        self.error: Optional[str] = None

    @property
    def duration(self) -> float:
        return time.time() - self.start

    @property
    def success(self) -> int:
        return sum(r.success for r in self.account_reports)

    @property
    def failed(self) -> int:
        return sum(r.failed for r in self.account_reports)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.account_reports if r.skipped)

    def to_dict(self) -> dict:
        return {
            "accounts": self.accounts,
            "blueprints": self.blueprints,
            "rounds": self.rounds_total,
            "mix_mode": self.mix_mode,
            "duration": round(self.duration, 1),
            "total_steps": self.success + self.failed,
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "account_reports": [r.to_dict() for r in self.account_reports],
            "error": self.error,
        }


# ════════════════════════════════════════════════════════════
# 核心引擎
# ════════════════════════════════════════════════════════════

class BatchEngine:
    def __init__(self, accounts: List[str], blueprints: List[str],
                 rounds: int = 10, mix: bool = False,
                 corpus: List[str] = None):
        self.accounts = accounts
        self.blueprints = blueprints
        self.rounds_total = rounds
        self.mix = mix
        self.corpus = corpus or []

    def _pick_blueprint(self, round_idx: int) -> str:
        if self.mix:
            return random.choice(self.blueprints)
        return self.blueprints[(round_idx - 1) % len(self.blueprints)]

    async def run_single(self, account_id: str, blueprint_name: str,
                         round_idx: int, conn=None) -> AccountRunReport:
        """对单个账号执行一轮蓝图

        Args:
            conn: 可选的已有 CDPConnector 实例（跨轮复用浏览器时使用）。
                  为 None 则自行启动并关闭浏览器。

        使用现有 CDPConnector + DouyinOps 模式（与 yanghao_runner.py 一致）
        """
        report = AccountRunReport(account_id, blueprint_name, round_idx)
        own_conn = conn is None

        # profile_cache: 在 goto_profile 时一次性提取全部字段，读字段步骤从缓存返回
        profile_cache: dict = {}

        # 1. 解析账号+蓝图
        try:
            acct_info = resolve_account(account_id)
        except ValueError as e:
            log.warning(f"  ⏭️ {account_id}: {e}")
            report.skipped = True
            return report

        platform = acct_info.get("platform", "douyin")
        identity_hint = acct_info.get("identity_hint", account_id)

        # 复用连接时 cookie 已在 _run_account_all_rounds 中验证过，跳过（避免浏览器写锁冲突）
        cookie_status = "ok" if not own_conn else check_cookie(identity_hint)
        if cookie_status != "ok":
            log.warning(f"  ⏭️ {account_id}: cookie={cookie_status}，跳过")
            report.skipped = True
            return report

        bp = resolve_blueprint(blueprint_name)
        if not bp:
            log.warning(f"  ⏭️ {blueprint_name}: 蓝图未找到")
            report.skipped = True
            return report
        steps = bp.get("steps", [])
        log.info(f"  📱 {account_id}{' [复用]' if not own_conn else ''} → {blueprint_name} ({len(steps)}步)")

        # 2. 浏览器连接管理
        identity_dir = str(IDENTITIES_ROOT / identity_hint)

        try:
            from cdp_connector import CDPConnector
            from douyin_ops import DouyinOps

            if own_conn:
                conn = CDPConnector(
                    browser_type="camoufox",
                    headless=False,
                    window=(702, 783),
                    identity_dir=identity_dir,
                )
                await conn.connect()
                await conn.init_anti_detection()
            dyops = DouyinOps(conn.page)

            # 导航到首页（复用模式下也确保正确页面）
            target_url = "https://www.douyin.com/" if platform != "xiaohongshu" else "https://www.xiaohongshu.com/"
            log.info(f"  🌐 打开 {target_url}")
            await conn.page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(5)

            # 找第一个视频进入播放模式（仅第一轮/自建连接时）
            if platform == "douyin":
                video_links = await conn.page.evaluate("""() => {
                    const all = document.querySelectorAll('a');
                    const videos = [];
                    for (const a of all) {
                        if (a.href && a.href.includes('/video/')) videos.push(a.href);
                    }
                    return [...new Set(videos)].slice(0, 3);
                }""")
                if video_links:
                    log.info(f"  📍 进入视频播放页...")
                    try:
                        await conn.page.goto(video_links[0], timeout=15000, wait_until="domcontentloaded")
                        await asyncio.sleep(3)
                    except:
                        pass

            # 3. 参数替换：蓝图中的 @url/@keyword/@comment_text 等从 task_params 填入
            task_params = getattr(self, 'task_params', {})
            def _resolve(val):
                if isinstance(val, str):
                    for k, v in task_params.items():
                        val = val.replace(f'@{k}', str(v))
                return val

            # 4. 执行蓝图步骤
            for i, step in enumerate(steps):
                sn = step.get("step_id", i + 1)
                op = step.get("op", "")
                sargs_raw = step.get("args", {})
                sargs = {k: _resolve(v) for k, v in sargs_raw.items()}
                start_t = time.time()

                try:
                    result = "OK"

                    if op == "goto_home":
                        await conn.page.goto("https://www.douyin.com/", timeout=15000)
                        await asyncio.sleep(3)
                    elif op == "goto_url":
                        url = sargs.get("url", "https://www.douyin.com/")
                        log.info(f"  📍 导航到: {url[:60]}...")
                        await conn.page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(5)
                    elif op == "dy_goto_profile":
                        await conn.page.goto("https://www.douyin.com/user/self", timeout=20000, wait_until="domcontentloaded")
                        await asyncio.sleep(5)

                        # 统一提取：一次 page.evaluate 获取全部字段
                        profile_cache = await conn.page.evaluate("""() => {
                            const text = (document.body.innerText || '').trim();
                            const title = (document.title || '').replace(' - 抖音', '').replace('的抖音', '').trim();

                            const uidM = text.match(/抖音号[：:]\\s*(\\S+)/);
                            const folM = text.match(/(\\d+(?:\\.\\d+)?[万w]?)\\s*关注/);
                            const fanM = text.match(/(\\d+(?:\\.\\d+)?[万w]?)\\s*粉丝/);
                            const likM = text.match(/(\\d+(?:\\.\\d+)?[万w]?)\\s*获赞/);
                            const posM = text.match(/作品\\s*(\\d+)/);

                            function getE2e(s) {
                                const el = document.querySelector('[data-e2e="'+s+'"]');
                                return el ? (el.textContent||'').trim() : '';
                            }
                            const folE = getE2e('user-info-follow').replace(/[^0-9]/g,'');
                            const fanE = getE2e('user-info-fans').replace(/[^0-9]/g,'');
                            const likE = getE2e('user-info-like').replace(/[^0-9]/g,'');
                            const cntE = getE2e('user-tab-count');

                            const fol = folM ? folM[1] : (folE || '?');
                            const fan = fanM ? fanM[1] : (fanE || '?');
                            const lik = likM ? likM[1] : (likE || '?');
                            const pos = posM ? posM[1] : (cntE || '?');

                            let bio = '?';
                            const bioE = getE2e('user-bio');
                            if (bioE) bio = bioE.slice(0, 50);

                            return { nickname: title, user_id: uidM ? uidM[1] : '?',
                                     following: fol, fans: fan, likes: lik,
                                     posts: pos, bio: bio };
                        }""")
                        p = profile_cache
                        log.info(
                            f"      📊 主页: {p.get('nickname','?')}"
                            f" ID={p.get('user_id','?')}"
                            f" 关注={p.get('following','?')}"
                            f" 粉丝={p.get('fans','?')}"
                            f" 获赞={p.get('likes','?')}"
                            f" 作品={p.get('posts','?')}"
                        )
                        # 保存主页信息到 profiles.json
                        try:
                            pf = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "data" / "profiles.json"
                            if pf.exists():
                                all_p = json.loads(pf.read_text())
                            else:
                                all_p = {}
                            pf.parent.mkdir(parents=True, exist_ok=True)
                            all_p[account_id] = {
                                "nickname": p.get("nickname","?"),
                                "user_id": p.get("user_id","?"),
                                "following": p.get("following","?"),
                                "fans": p.get("fans","?"),
                                "likes": p.get("likes","?"),
                                "posts": p.get("posts","?"),
                                "platform": "douyin",
                                "updated": datetime.now().isoformat(),
                            }
                            pf.write_text(json.dumps(all_p, ensure_ascii=False, indent=2))
                        except:
                            pass
                        result = "profile_loaded"
                    elif op == "dy_read_nickname":
                        v = profile_cache.get("nickname", "?")
                        log.info(f"      📝 昵称: {v} (cached)")
                        result = "nickname=" + v
                    elif op == "dy_read_douyin_id":
                        v = profile_cache.get("user_id", "?")
                        log.info(f"      🔢 抖音号: {v} (cached)")
                        result = "douyin_id=" + v
                    elif op == "dy_read_following":
                        v = profile_cache.get("following", "?")
                        log.info(f"      👥 关注: {v} (cached)")
                        result = "following=" + v
                    elif op == "dy_read_fans":
                        v = profile_cache.get("fans", "?")
                        log.info(f"      👥 粉丝: {v} (cached)")
                        result = "fans=" + v
                    elif op == "dy_read_likes":
                        v = profile_cache.get("likes", "?")
                        log.info(f"      👍 获赞: {v} (cached)")
                        result = "likes=" + v
                    elif op == "dy_read_posts":
                        v = profile_cache.get("posts", "?")
                        log.info(f"      📹 作品: {v} (cached)")
                        result = "posts=" + v
                    elif op == "dy_read_bio":
                        v = profile_cache.get("bio", "?")
                        log.info(f"      📄 简介: {v} (cached)")
                        result = "bio=" + v
                    elif op == "wait_watch":
                        seconds = sargs.get("seconds", random.randint(5, 12))
                        await dyops.wait_watch(step_id=sn, seconds=seconds)
                    elif op == "like":
                        # 双路径：1) DOM 点 digg 按钮 2) 视频获焦 + KeyZ 快捷键兜底
                        ok = await dyops.like(step_id=sn, probability=1.0)
                        if not ok:
                            log.info(f"  🔄 digg 按钮未找到，尝试 KeyZ 快捷键")
                            video = conn.page.locator('video')
                            if await video.count() > 0:
                                box = await video.first.bounding_box()
                                if box:
                                    await conn.page.mouse.click(
                                        box['x'] + box['width'] // 2,
                                        box['y'] + box['height'] // 3,
                                    )
                                    await asyncio.sleep(0.5)
                            await conn.page.keyboard.press("z")
                            await asyncio.sleep(1.5)
                            ok = await dyops.like(step_id=sn, probability=1.0)
                        result = "👍" if ok else "-"
                    elif op == "collect":
                        r = await conn.page.evaluate("""() => {
                            const b = document.querySelector('[data-e2e="video-collect"]');
                            return b ? (b.click(), '⭐') : '-';
                        }""")
                        result = r
                    elif op == "open_comments":
                        # 检测页面模式：Path A（弹窗） vs Path B（全屏视频页）
                        page_url = conn.page.url
                        is_full_page = "/video/" in page_url and "modal_id" not in page_url
                        if is_full_page:
                            r = await conn.page.evaluate("""() => {
                                const list = document.querySelector('[data-e2e="comment-list"]');
                                if (list && list.offsetParent !== null) {
                                    list.scrollIntoView({behavior: 'instant', block: 'start'});
                                    return 'already_open';
                                }
                                const inputArea = document.querySelector('.comment-input-inner-container, [class*="comment-input"]');
                                if (inputArea && inputArea.offsetParent !== null) {
                                    inputArea.scrollIntoView({behavior: 'instant', block: 'center'});
                                    return 'scrolled';
                                }
                                window.scrollTo(0, document.body.scrollHeight);
                                return 'scrolled_bottom';
                            }""")
                            await asyncio.sleep(3)
                            result = f"comments_{r}"
                        else:
                            ok = await dyops.open_comments(step_id=sn)
                            await asyncio.sleep(3)
                            result = "opened" if ok else "not_found"
                    elif op == "post_comment":
                        text = sargs.get("text", "拍得真好")
                        # @corpus 标记：从语料库按方向自动生成评论
                        if text == "@corpus":
                            direction = task_params.get("direction", "")
                            kw = sargs.get("keyword", task_params.get("keyword", ""))
                            try:
                                from mc.corpus import CorpusManager
                                cm = CorpusManager()
                                gen = cm.get_comment_for_video(kw, direction=direction if direction else None)
                                if gen:
                                    text = gen
                            except: pass
                        # 检测页面模式：Path A（弹窗） vs Path B（全屏视频页）
                        page_url = conn.page.url
                        is_full_page = "/video/" in page_url and "modal_id" not in page_url
                        if is_full_page:
                            # Path B: 滚动到评论区 + 点输入框 + pbcopy 粘贴 + 发送
                            await asyncio.sleep(1)
                            await conn.page.evaluate("""() => {
                                const area = document.querySelector('[class*="comment-input-inner"], [class*="comment-input-inner-container"]');
                                if (area) area.scrollIntoView({behavior: 'instant', block: 'center'});
                            }""")
                            await asyncio.sleep(1)
                            r = await conn.page.evaluate("""() => {
                                const input = document.querySelector('[class*="comment-input-inner"] [contenteditable="true"], [contenteditable="true"]');
                                if (input && input.offsetParent !== null) { input.focus(); input.click(); return 'focused'; }
                                const container = document.querySelector('[class*="comment-input-inner"]');
                                if (container) { container.click(); return 'container_clicked'; }
                                return 'no_input';
                            }""")
                            await asyncio.sleep(1)
                        else:
                            # Path A: 聚焦评论输入框
                            r = await conn.page.evaluate("""() => {
                                const sel = '[data-e2e="comment-input"], textarea[placeholder*="评论"], .comment-input, [contenteditable="true"]';
                                const el = document.querySelector(sel);
                                if (el && el.offsetParent !== null) { el.focus(); return 'focused'; }
                                const tas = document.querySelectorAll('textarea');
                                for (const ta of tas) { if (ta.offsetParent !== null) { ta.focus(); return 'ta_' + ta.placeholder; } }
                                return 'no_input';
                            }""")
                            await asyncio.sleep(0.5)
                        # pbcopy 写入剪贴板（Draft.js 只认系统级粘贴）
                        proc = await asyncio.create_subprocess_exec(
                            "pbcopy", stdin=asyncio.subprocess.PIPE
                        )
                        await proc.communicate(input=text.encode())
                        await asyncio.sleep(0.5)
                        # Meta+V 粘贴 + Enter 发送
                        await conn.page.keyboard.press("Meta+V")
                        await asyncio.sleep(1.5)
                        await conn.page.keyboard.press("Enter")
                        await asyncio.sleep(2)
                        result = f"comment_sent({text[:10]})"
                    elif op == "close_comments":
                        # Escape 关闭评论区
                        await conn.page.keyboard.press("Escape")
                        await asyncio.sleep(1)
                        result = "comments_closed"
                    elif op == "xhs_goto_profile":
                        # 尝试多种方式进入个人主页
                        target = ""
                        # 方式1: 找"我"的导航链接
                        target = await conn.page.evaluate("""() => {
                            const links = document.querySelectorAll('a');
                            for (const a of links) {
                                const href = a.href || '';
                                if (href.includes('/user/profile/')) return href;
                            }
                            return '';
                        }""")
                        if not target:
                            # 方式2: 直接导航到创作者中心（已登录用户）
                            await conn.page.goto("https://creator.xiaohongshu.com", timeout=15000, wait_until="domcontentloaded")
                            await asyncio.sleep(3)
                            # 检查是否被重定向到登录页
                            if "login" in conn.page.url.lower() or "sign" in conn.page.url.lower():
                                # 方式3: 回到首页
                                await conn.page.goto("https://www.xiaohongshu.com/explore", timeout=15000, wait_until="domcontentloaded")
                                await asyncio.sleep(3)
                                # 尝试 JS 点击"我"按钮
                                await conn.page.evaluate("""() => {
                                    const items = document.querySelectorAll('[class*="tab"],[class*="nav-item"]');
                                    for (const el of items) {
                                        const t = (el.textContent||'').trim();
                                        if (t.includes('我') || t.includes('我的')) { el.click(); return; }
                                    }
                                }""")
                                await asyncio.sleep(3)
                                target = conn.page.url
                            else:
                                target = conn.page.url
                        if target:
                            await conn.page.goto(target, timeout=20000, wait_until="domcontentloaded")
                            await asyncio.sleep(5)

                        # 统一提取：一次 page.evaluate 获取全部字段
                        profile_cache = await conn.page.evaluate(r"""() => {
                            const text = (document.body.innerText || '').trim();
                            const title = (document.title || '').replace(' - 小红书', '').trim();

                            const uidM = text.match(/小红书号[：:]\s*(\d+)/);
                            const folM = text.match(/(\d+(?:\.\d+)?[万wW]?)\s*关注/);
                            const fanM = text.match(/(\d+(?:\.\d+)?[万wW]?)\s*粉丝/);
                            const likM = text.match(/(\d+(?:\.\d+)?[万wW]?)\s*获赞与收藏/);
                            const posM = text.match(/笔记[・·](\d+(?:\.\d+)?[万wW]?)/);

                            let bio = '?';
                            if (text.includes('还没有简介') || text.includes('暂无简介')) {
                                bio = '(无)';
                            } else {
                                const bioM = text.match(/IP属地[：:].+?\n(.+?)(?=\d+关注|\d+粉丝)/);
                                if (bioM) bio = bioM[1].trim().slice(0, 50) || '(无)';
                            }

                            return { nickname: title, user_id: uidM ? uidM[1] : '?',
                                     following: folM ? folM[1] : '?', fans: fanM ? fanM[1] : '?',
                                     likes: likM ? likM[1] : '?', posts: posM ? posM[1] : '?',
                                     bio: bio };
                        }""")
                        p = profile_cache
                        log.info(
                            f"      📊 主页: {p.get('nickname','?')}"
                            f" ID={p.get('user_id','?')}"
                            f" 关注={p.get('following','?')}"
                            f" 粉丝={p.get('fans','?')}"
                            f" 获赞={p.get('likes','?')}"
                            f" 笔记={p.get('posts','?')}"
                        )
                        # 保存主页信息
                        try:
                            pf = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "data" / "profiles.json"
                            all_p = json.loads(pf.read_text()) if pf.exists() else {}
                            all_p[account_id] = {
                                "nickname": p.get("nickname","?"),
                                "user_id": p.get("user_id","?"),
                                "following": p.get("following","?"),
                                "fans": p.get("fans","?"),
                                "likes": p.get("likes","?"),
                                "posts": p.get("posts","?"),
                                "platform": "xiaohongshu",
                                "updated": datetime.now().isoformat(),
                            }
                            pf.write_text(json.dumps(all_p, ensure_ascii=False, indent=2))
                        except:
                            pass
                        result = "profile_loaded"
                    elif op == "xhs_read_nickname":
                        v = profile_cache.get("nickname", "?")
                        log.info(f"      📝 昵称: {v} (cached)")
                        result = "nickname=" + v
                    elif op == "xhs_read_user_id":
                        v = profile_cache.get("user_id", "?")
                        log.info(f"      🔢 小红书号: {v} (cached)")
                        result = "user_id=" + v
                    elif op == "xhs_read_following":
                        v = profile_cache.get("following", "?")
                        log.info(f"      👥 关注: {v} (cached)")
                        result = "following=" + v
                    elif op == "xhs_read_fans":
                        v = profile_cache.get("fans", "?")
                        log.info(f"      👥 粉丝: {v} (cached)")
                        result = "fans=" + v
                    elif op == "xhs_read_likes":
                        v = profile_cache.get("likes", "?")
                        log.info(f"      👍 获赞: {v} (cached)")
                        result = "likes=" + v
                    elif op == "xhs_read_bio":
                        v = profile_cache.get("bio", "?")
                        log.info(f"      📄 简介: {v} (cached)")
                        result = "bio=" + v
                    elif op == "xhs_goto_home":
                        await conn.page.goto("https://www.xiaohongshu.com/explore", timeout=20000, wait_until="domcontentloaded")
                        await asyncio.sleep(4)
                        result = "home_loaded"
                    elif op == "xhs_browse":
                        if "explore" not in conn.page.url:
                            await conn.page.goto("https://www.xiaohongshu.com/explore", timeout=15000, wait_until="domcontentloaded")
                            await asyncio.sleep(3)
                        result = "browsing"
                    elif op == "xhs_scroll_feed":
                        await conn.page.evaluate("() => window.scrollBy(0, 800)")
                        await asyncio.sleep(2)
                        result = "scrolled"
                    elif op == "xhs_click_note":
                        note = conn.page.locator('section.note-item, a[href*="/explore/"], [class*="note-item"]').first
                        if await note.count() > 0:
                            await note.click()
                            await asyncio.sleep(4)
                            result = "note_opened"
                        else:
                            result = "no_note"
                    elif op == "xhs_like":
                        r = await conn.page.evaluate("""() => {
                            const btns = document.querySelectorAll('[class*="like"],[data-testid*="like"]');
                            for (const b of btns) {
                                if (b.offsetParent !== null) { b.click(); return '👍'; }
                            }
                            return '-';
                        }""")
                        await asyncio.sleep(1)
                        result = r
                    elif op == "xhs_comment":
                        await conn.page.keyboard.press("x")
                        await asyncio.sleep(2)
                        result = "comment_opened"
                    elif op == "xhs_follow":
                        r = await conn.page.evaluate("""() => {
                            const btns = document.querySelectorAll('button');
                            for (const b of btns) {
                                const t = (b.textContent || '').trim();
                                if (t.includes('关注') && !t.includes('已关注')) { b.click(); return '✅'; }
                            }
                            return '-';
                        }""")
                        await asyncio.sleep(1)
                        result = r
                    elif op == "xhs_collect":
                        r = await conn.page.evaluate("""() => {
                            const btns = document.querySelectorAll('[class*="collect"],[class*="save"]');
                            for (const b of btns) {
                                if (b.offsetParent !== null) { b.click(); return '⭐'; }
                            }
                            return '-';
                        }""")
                        await asyncio.sleep(1)
                        result = r
                    elif op == "xhs_search":
                        kw = sargs.get("keyword", "热门推荐")
                        await conn.page.evaluate(f"(k) => {{ const i = document.querySelector('input'); if(i) {{ i.value=k; i.dispatchEvent(new Event('input')); }} }}", kw)
                        await asyncio.sleep(1)
                        await conn.page.keyboard.press("Enter")
                        await asyncio.sleep(3)
                        result = f"searched({kw})"
                    elif op in ("next_video", "swipe_next"):
                        await conn.page.evaluate("() => window.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown'}))")
                        await asyncio.sleep(2)
                    elif op == "scroll_feed":
                        await conn.page.evaluate("() => window.scrollBy(0, 600)")
                        await asyncio.sleep(1)
                    elif op in ("open_video", "enter_video"):
                        card = conn.page.locator('.discover-video-card-item').first
                        if await card.count() > 0:
                            await card.click()
                            await asyncio.sleep(3)
                    elif op == "search":
                        kw = sargs.get("keyword", "热门")
                        await conn.page.evaluate(f"(k) => {{ const i = document.querySelector('input'); if(i) {{ i.value=k; i.dispatchEvent(new Event('input')); }} }}", kw)
                        await asyncio.sleep(2)
                    elif op == "wait":
                        await asyncio.sleep(sargs.get("seconds", 2))
                    elif op == "goto_profile":
                        d = await dyops.goto_profile(step_id=sn)
                        result = d.get("nickname","ok")
                        # 保存到 profiles.json
                        try:
                            pf = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "data" / "profiles.json"
                            all_p = json.loads(pf.read_text()) if pf.exists() else {}
                            all_p[account_id] = {**d, "platform":"douyin","updated":datetime.now().isoformat()}
                            pf.write_text(json.dumps(all_p, ensure_ascii=False, indent=2))
                        except: pass
                    elif op == "read_profile_field":
                        v = await dyops.read_profile_field(sargs.get("field","nickname"), step_id=sn)
                        result = f"{sargs.get('field','?')}={v}"
                    elif op == "read_my_comments":
                        comments = await dyops.read_my_comments(step_id=sn)
                        result = f"comments={len(comments)}"
                    elif op == "reply_comment":
                        text = sargs.get("text", "谢谢支持")
                        ok = await dyops.reply_comment(text, step_id=sn)
                        result = "replied" if ok else "no_reply_btn"
                    elif op == "search_browse":
                        kw = sargs.get("keyword", "热门推荐")
                        await dyops.search(kw, step_id=sn)
                        await dyops.click_search_result(step_id=sn)
                        await dyops.wait_watch(seconds=random.randint(5, 12), step_id=sn)
                        import random as _rnd
                        if _rnd.random() < 0.6: await dyops.like(step_id=sn)
                        if _rnd.random() < 0.2: await dyops.collect(step_id=sn)
                        result = "searched+browsed"
                    else:
                        await asyncio.sleep(2)
                        result = f"skip({op})"

                    dur = time.time() - start_t
                    report.add_step(StepResult(op, sn, True, dur))
                    log.info(f"    ✅ [{sn:2d}] {op:15s} → {str(result)[:20]} ({dur:.1f}s)")

                except Exception as step_err:
                    dur = time.time() - start_t
                    report.add_step(StepResult(op, sn, False, dur, str(step_err)))
                    log.warning(f"    ⚠️ [{sn:2d}] {op:15s} → {type(step_err).__name__}")

                await asyncio.sleep(1.5)

            if own_conn:
                await conn.close()
            log.info(f"  ✅ {account_id}: 完成 ({report.success}/{len(steps)}步)")

        except Exception as e:
            log.error(f"  ❌ {account_id}: {e}")
            if own_conn and conn:
                await conn.close()
            report.failed = len(steps)

        return report

    async def _run_account_all_rounds(self, account_id: str,
                                       bm) -> List[AccountRunReport]:
        """单个账号用一个浏览器实例跑完全部轮次（并行子任务）

        由 run() 通过 asyncio.gather 并发调用。
        BrowserManager 的 prepare() 已在 run() 中统一执行，
        这里只负责：resolve_account → cookie 检查 → CDPConnector 连接
        → 循环跑所有轮次 → 关闭浏览器。

        Args:
            account_id: 账号名称（如 douyin_01）
            bm: BrowserManager 实例（仅用于 prepare，实际不管理这里启动的浏览器）

        Returns:
            每轮一个 AccountRunReport
        """
        reports: List[AccountRunReport] = []

        acct_info = resolve_account(account_id)
        platform = acct_info.get("platform", "douyin")
        identity_hint = acct_info.get("identity_hint", account_id)

        # Cookie 检查（一次检查，所有轮共用）
        cookie_status = check_cookie(identity_hint)
        if cookie_status != "ok":
            for r in range(1, self.rounds_total + 1):
                rpt = AccountRunReport(account_id, "", r)
                rpt.skipped = True
                reports.append(rpt)
            log.warning(f"  ⏭️ {account_id}: cookie={cookie_status}，全部跳过")
            return reports

        identity_dir = str(IDENTITIES_ROOT / identity_hint)

        from cdp_connector import CDPConnector
        conn = CDPConnector(
            browser_type="camoufox",
            headless=False,
            window=(702, 783),
            identity_dir=identity_dir,
        )

        try:
            await conn.connect()
            await conn.init_anti_detection()

            for round_idx in range(1, self.rounds_total + 1):
                bp_name = self._pick_blueprint(round_idx)
                rpt = await self.run_single(
                    account_id, bp_name, round_idx, conn=conn,
                )
                reports.append(rpt)

                if round_idx < self.rounds_total:
                    wait = random.uniform(30, 60)
                    log.info(f"\n  ⏳ [{account_id}] 等待 {wait:.0f}s 后下一轮...")
                    await asyncio.sleep(wait)

        except Exception as e:
            log.error(f"  ❌ {account_id}: 浏览器异常退出 - {e}")
            for r in range(1, self.rounds_total + 1):
                if not any(x.round == r for x in reports):
                    rpt = AccountRunReport(account_id, "", r)
                    rpt.failed = 99
                    reports.append(rpt)
        finally:
            await conn.close()
            log.info(f"  🛑 {account_id} 浏览器已关闭")

        return reports

    async def run(self) -> BatchReport:
        """执行全部任务（并行模式）"""
        from mc.browser import BrowserManager

        report = BatchReport()
        report.accounts = self.accounts
        report.blueprints = self.blueprints
        report.rounds_total = self.rounds_total
        report.mix_mode = self.mix

        bm = BrowserManager()

        try:
            with bm:
                # 1) 统一 prepare（清理残留）
                for account_id in self.accounts:
                    acct_info = resolve_account(account_id)
                    identity_hint = acct_info.get("identity_hint", account_id)
                    bm.prepare(identity_hint)

                # 2) 并行执行：每账号独立浏览器，跑完全部轮次
                log.info(f"\n{'='*50}")
                log.info(f"  🚀 并行执行 {len(self.accounts)} 个账号")
                log.info(f"     每账号 {self.rounds_total} 轮 | 蓝图: {self.blueprints}")
                log.info(f"{'='*50}")

                tasks = [self._run_account_all_rounds(a, bm) for a in self.accounts]
                results = await asyncio.gather(*tasks)

                for account_reports in results:
                    report.account_reports.extend(account_reports)

        except Exception as e:
            log.error(f"❌ 批量执行异常: {e}")
            report.error = str(e)

        return report
