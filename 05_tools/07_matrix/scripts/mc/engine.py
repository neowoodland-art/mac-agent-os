"""
engine.py — mc run 真实执行引擎

不再依赖旧 orchestrator（Chrome CDP 模式），
改为直接使用 Camoufox 加载身份 cookie 执行。

流程:
  mc run --accounts X --blueprints Y
    → BatchEngine.run()
      → for each account:
          1. 检查 cookie 有效性（跳过无效的）
          2. 用 Camoufox 启动身份目录
          3. 打开抖音首页
          4. 验证登录态
          5. 执行蓝图步骤（通过 atom_ops）
          6. 关闭浏览器
      → 返回汇总报告
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
                         round_idx: int) -> AccountRunReport:
        """对单个账号执行一轮蓝图

        使用现有 CDPConnector + DouyinOps 模式（与 yanghao_runner.py 一致）
        """
        report = AccountRunReport(account_id, blueprint_name, round_idx)

        # 1. 解析账号+蓝图
        try:
            acct_info = resolve_account(account_id)
        except ValueError as e:
            log.warning(f"  ⏭️ {account_id}: {e}")
            report.skipped = True
            return report

        platform = acct_info.get("platform", "douyin")
        identity_hint = acct_info.get("identity_hint", account_id)

        cookie_status = check_cookie(identity_hint)
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
        log.info(f"  📱 {account_id} → {blueprint_name} ({len(steps)}步)")

        # 2. 使用 CDPConnector 启动 Camoufox（与 yanghao_runner 一致）
        identity_dir = str(IDENTITIES_ROOT / identity_hint)

        try:
            from cdp_connector import CDPConnector
            from douyin_ops import DouyinOps

            conn = CDPConnector(
                browser_type="camoufox",
                headless=False,
                window=(702, 783),
                identity_dir=identity_dir,
            )

            await conn.connect()
            await conn.init_anti_detection()
            dyops = DouyinOps(conn.page)

            # 导航到首页
            target_url = "https://www.douyin.com/" if platform != "xiaohongshu" else "https://www.xiaohongshu.com/"
            log.info(f"  🌐 打开 {target_url}")
            await conn.page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(5)

            # 找第一个视频进入播放模式（与 yanghao_runner 一致）
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

            # 3. 执行蓝图步骤（与 yanghao_runner 相同的执行模式）
            for i, step in enumerate(steps):
                sn = step.get("step_id", i + 1)
                op = step.get("op", "")
                sargs = step.get("args", {})
                start_t = time.time()

                try:
                    result = "OK"

                    if op == "goto_home":
                        await conn.page.goto("https://www.douyin.com/", timeout=15000)
                        await asyncio.sleep(3)
                    elif op == "dy_goto_profile":
                        await conn.page.goto("https://www.douyin.com/user/self", timeout=20000, wait_until="domcontentloaded")
                        await asyncio.sleep(4)
                        result = "profile_loaded"
                    elif op == "dy_read_nickname":
                        nick = await conn.page.evaluate("""() => { const el=document.querySelector('[data-e2e="user-info"]'); if(!el) return '?'; const t=el.textContent.trim(); const m=t.match(/^([^\\d]+?)(?=关注\\d)/); return m?m[1].trim():t.slice(0,20); }""")
                        log.info(f"      📝 昵称: {nick}")
                        result = "nickname=" + nick
                    elif op == "dy_read_douyin_id":
                        dyid = await conn.page.evaluate("""() => { const el=document.querySelector('[data-e2e="user-info"]'); if(!el) return '?'; const t=el.textContent.trim(); const m=t.match(/抖音号[：:]\\s*(\\S+)/); return m?m[1]:'?'; }""")
                        log.info(f"      🔢 抖音号: {dyid}")
                        result = "douyin_id=" + dyid
                    elif op == "dy_read_following":
                        v = await conn.page.evaluate("""() => { const el=document.querySelector('[data-e2e="user-info-follow"]'); return el?el.textContent.trim():'?'; }""")
                        log.info(f"      👥 关注: {v}")
                        result = "following=" + v
                    elif op == "dy_read_fans":
                        v = await conn.page.evaluate("""() => { const el=document.querySelector('[data-e2e="user-info-fans"]'); return el?el.textContent.trim():'?'; }""")
                        log.info(f"      👥 粉丝: {v}")
                        result = "fans=" + v
                    elif op == "dy_read_likes":
                        v = await conn.page.evaluate("""() => { const el=document.querySelector('[data-e2e="user-info-like"]'); return el?el.textContent.trim():'?'; }""")
                        log.info(f"      👍 获赞: {v}")
                        result = "likes=" + v
                    elif op == "dy_read_posts":
                        v = await conn.page.evaluate("""() => { const el=document.querySelector('[data-e2e="user-tab-count"]'); return el?el.textContent.trim():'?'; }""")
                        log.info(f"      📹 作品: {v}")
                        result = "posts=" + v
                    elif op == "dy_read_bio":
                        v = await conn.page.evaluate("""() => { const el=document.querySelector('[data-e2e="user-bio"]'); return el?el.textContent.trim().slice(0,50):'?'; }""")
                        log.info(f"      📄 简介: {v}")
                        result = "bio=" + v
                    elif op == "wait_watch":
                        seconds = sargs.get("seconds", random.randint(5, 12))
                        await dyops.wait_watch(step_id=sn, seconds=seconds)
                    elif op == "like":
                        r = await conn.page.evaluate("""() => {
                            const b = document.querySelector('[data-e2e="feed-active-video-double-like"]');
                            if (b) { b.click(); return '👍'; }
                            const b2 = document.querySelector('[data-e2e="like-count"]');
                            if (b2) { b2.click(); return '👍'; }
                            return '-';
                        }""")
                        result = r
                    elif op == "collect":
                        r = await conn.page.evaluate("""() => {
                            const b = document.querySelector('[data-e2e="video-collect"]');
                            return b ? (b.click(), '⭐') : '-';
                        }""")
                        result = r
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

            await conn.close()
            log.info(f"  ✅ {account_id}: 完成 ({report.success}/{len(steps)}步)")

        except Exception as e:
            log.error(f"  ❌ {account_id}: {e}")
            report.failed = len(steps)

        return report

    async def run(self) -> BatchReport:
        """执行全部任务"""
        from mc.browser import BrowserManager

        report = BatchReport()
        report.accounts = self.accounts
        report.blueprints = self.blueprints
        report.rounds_total = self.rounds_total
        report.mix_mode = self.mix

        bm = BrowserManager()

        try:
            with bm:
                for round_idx in range(1, self.rounds_total + 1):
                    log.info(f"\n{'─'*45}")
                    log.info(f"  🔄 第 {round_idx}/{self.rounds_total} 轮")
                    log.info(f"{'─'*45}")

                    for account_id in self.accounts:
                        acct_info = resolve_account(account_id)
                        identity_hint = acct_info.get("identity_hint", account_id)
                        bm.prepare(identity_hint)

                        bp_name = self._pick_blueprint(round_idx)
                        acct_report = await self.run_single(account_id, bp_name, round_idx)
                        report.account_reports.append(acct_report)

                    if round_idx < self.rounds_total:
                        wait = random.uniform(30, 60)
                        log.info(f"\n  ⏳ 等待 {wait:.0f}s 后下一轮...")
                        await asyncio.sleep(wait)

        except Exception as e:
            log.error(f"❌ 批量执行异常: {e}")
            report.error = str(e)

        return report
