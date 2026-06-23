"""
engine.py — mc run 执行引擎（v5.3 — 身份共享 + 多平台同浏览器）

核心逻辑：
  1. 按 identity_dir 分组账号 → 同身份共用一个浏览器
  2. 每个浏览器内先做完抖音，再做小红书
  3. 不同身份组之间错峰启动（防假死）
  4. 每个账号在其平台上顺序执行蓝图
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
from matrix_mgmt import AGENT_SYNC, AGENT_LOCAL

IDENTITIES_ROOT = AGENT_LOCAL / "tools" / "matrix" / "identities"
sys.path.insert(0, str(SCRIPTS_DIR))


# ════════════════════════════════════════════════════════════
# 工具函数
# ════════════════════════════════════════════════════════════

def resolve_account(account_id: str) -> dict:
    from matrix_mgmt import MatrixManager
    mgr = MatrixManager()
    for a in mgr.list_accounts():
        if a["id"] == account_id:
            return a
    raise ValueError(f"账号不存在: {account_id}")


def resolve_blueprint(name: str) -> Optional[dict]:
    bp_dir = TOOL_DIR / "blueprints"
    for f in sorted(bp_dir.glob("*.json")):
        bp = json.loads(f.read_text())
        if name in (bp.get("id", ""), bp.get("name", ""), f.stem):
            return bp
        if name in f.stem or f.stem in name:
            return json.loads(f.read_text())
    return None


def check_cookie(identity_hint: str) -> str:
    """检查身份目录 cookie 状态 → 'ok'|'no_cookie'|'expired'|'no_identity'"""
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
        conn_ck = sqlite3.connect(str(ck), timeout=2)
        cnt = conn_ck.execute("SELECT count(*) FROM moz_cookies WHERE name LIKE '%session%'").fetchone()[0]
        conn_ck.close()
        return "ok" if cnt > 0 else "expired"
    except:
        return "error"


def group_accounts_by_identity(account_ids: List[str]) -> dict:
    """按 identity_dir 分组账号，同目录的放到一个组里"""
    groups = {}
    for aid in account_ids:
        try:
            info = resolve_account(aid)
        except ValueError:
            continue
        ident = info.get("identity_dir", aid).replace("identities/", "")
        groups.setdefault(ident, []).append(info)
    return groups


# ════════════════════════════════════════════════════════════
# 执行报告
# ════════════════════════════════════════════════════════════

class StepResult:
    def __init__(self, op: str, step_id: int, success: bool = True,
                 duration: float = 0, error: str = ""):
        self.op = op; self.step_id = step_id; self.success = success
        self.duration = duration; self.error = error

    def __str__(self):
        icon = "✅" if self.success else "❌"
        return f"{icon} [{self.step_id:2d}] {self.op:20s} ({self.duration:.1f}s) {self.error}"


class AccountRunReport:
    def __init__(self, account: str, blueprint: str, round_idx: int):
        self.account = account; self.blueprint = blueprint; self.round = round_idx
        self.steps: List[StepResult] = []; self.start = time.time()
        self.success = 0; self.failed = 0; self.skipped = False

    @property
    def duration(self) -> float: return time.time() - self.start

    def add_step(self, result: StepResult):
        self.steps.append(result)
        if result.success: self.success += 1
        else: self.failed += 1

    def to_dict(self) -> dict:
        return {"account": self.account, "blueprint": self.blueprint,
                "round": self.round, "success": self.success, "failed": self.failed,
                "skipped": self.skipped, "duration": round(self.duration, 1),
                "steps": [{"op": s.op, "step_id": s.step_id, "success": s.success,
                           "duration": round(s.duration, 1), "error": s.error} for s in self.steps]}


class BatchReport:
    def __init__(self):
        self.accounts: List[str] = []; self.blueprints: List[str] = []
        self.rounds_total = 0; self.mix_mode = False
        self.start = time.time(); self.account_reports: List[AccountRunReport] = []
        self.error: Optional[str] = None

    @property
    def duration(self) -> float: return time.time() - self.start
    @property
    def success(self) -> int: return sum(r.success for r in self.account_reports)
    @property
    def failed(self) -> int: return sum(r.failed for r in self.account_reports)
    @property
    def skipped(self) -> int: return sum(1 for r in self.account_reports if r.skipped)

    def to_dict(self) -> dict:
        return {"accounts": self.accounts, "blueprints": self.blueprints,
                "rounds": self.rounds_total, "mix_mode": self.mix_mode,
                "duration": round(self.duration, 1),
                "total_steps": self.success + self.failed,
                "success": self.success, "failed": self.failed,
                "skipped": self.skipped,
                "account_reports": [r.to_dict() for r in self.account_reports],
                "error": self.error}


# ════════════════════════════════════════════════════════════
# 核心引擎
# ════════════════════════════════════════════════════════════

class BatchEngine:
    def __init__(self, accounts: List[str], blueprints: List[str],
                 rounds: int = 10, mix: bool = False,
                 corpus: List[str] = None,
                  stagger: str = "15-30",
                  keep_open: bool = False,
                  max_browsers: int = 3,
                  run_id: str = ""):
        self.accounts = accounts
        self.blueprints = blueprints
        self.rounds_total = rounds
        self.mix = mix
        self.corpus = corpus or []
        self.stagger = stagger
        self.keep_open = keep_open
        self.max_browsers = max_browsers
        self.run_id = run_id
        self.task_params = {}

    def _pick_blueprint(self, round_idx: int) -> str:
        if self.mix:
            return random.choice(self.blueprints)
        return self.blueprints[(round_idx - 1) % len(self.blueprints)]

    def _resolve_args(self, sargs: dict, account_id: str, platform: str) -> dict:
        """解析蓝图步骤中的占位符，替换为实际内容"""
        import copy
        resolved = copy.deepcopy(sargs)
        for k, v in resolved.items():
            if not isinstance(v, str):
                continue
            if "@corpus" in v:
                from mc.corpus import CorpusManager
                cm = CorpusManager()
                direction = resolved.get("direction", "") or self.task_params.get("direction", "")
                text = cm.get_comment_for_video(
                    video_title=self.task_params.get("keyword", ""),
                    direction=direction,
                    account_id=account_id,
                )
                resolved[k] = v.replace("@corpus", text)
            if "@keyword" in v:
                kw = self.task_params.get("keyword", "")
                resolved[k] = v.replace("@keyword", kw)
            if "@direction" in v:
                dr = self.task_params.get("direction", "")
                resolved[k] = v.replace("@direction", dr)
            if "@url" in v:
                url = self.task_params.get("url", "")
                resolved[k] = v.replace("@url", url)
            if "@scene" in v:
                scene = self.task_params.get("scene", "first_comment")
                from mc.corpus import CorpusManager
                cm = CorpusManager()
                text = cm.get_comment_for_scene(
                    persona=self.task_params.get("persona", ""),
                    scene=scene,
                    keyword=self.task_params.get("keyword", ""),
                    round_num=self.task_params.get("round_num", 1),
                )
                if text:
                    resolved[k] = v.replace("@scene", text)
        return resolved

    async def _run_acct_on_conn(self, account_info: dict, blueprint_name: str,
                                 round_idx: int, conn) -> AccountRunReport:
        """在已有浏览器连接上执行单个账号的单个轮次"""
        account_id = account_info["id"]
        report = AccountRunReport(account_id, blueprint_name, round_idx)
        platform = account_info.get("platform", "douyin")

        bp = resolve_blueprint(blueprint_name)
        if not bp:
            report.skipped = True
            return report
        steps = bp.get("steps", [])
        log.info(f"  📱 {account_id} ({platform}) → {blueprint_name} ({len(steps)}步)")

        # 导航到该平台的首页
        home_url = "https://www.xiaohongshu.com/explore" if platform == "xiaohongshu" else "https://www.douyin.com/"
        try:
            await conn.page.goto(home_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(5)
        except:
            await conn.page.goto(home_url, timeout=60000, wait_until="load")
            await asyncio.sleep(5)

        # ── 钩子1: 登录状态检测（执行前确保登录）──
        from matrix_modules.account.login_state_machine import LoginStateMachine
        lsm = LoginStateMachine()
        login_ok = await lsm.ensure_login(conn.page, account_id, platform)
        if not login_ok:
            log.warning(f"  ❌ [{account_id}] 登录检测不通过，跳过本轮")
            report.skipped = True
            return report

        # 创建 platform ops
        if platform == "xiaohongshu":
            from ops.xhs_ops import XhsOps
            ops = XhsOps(conn.page)
        else:
            from douyin_ops import DouyinOps
            ops = DouyinOps(conn.page)
        ops.set_account_id(account_id)

        # 抖音：进入视频播放
        if platform == "douyin":
            await ops.execute("open_video")

        # 执行步骤
        for i, step in enumerate(steps):
            sn = step.get("step_id", i + 1)
            op_name = step.get("op", "")
            sargs = self._resolve_args(step.get("args", {}), account_id, platform)
            result = await ops.execute(op=op_name, args=sargs, step_id=sn)
            report.add_step(StepResult(op_name, sn, result.success, result.elapsed,
                                       "" if result.success else result.error))
            icon = "✅" if result.success else "❌"
            log.info(f"    {icon} [{sn:2d}] {op_name:18s} → {result.detail[:25]} ({result.elapsed:.1f}s)")

            # ── 钩子2: 操作后检查验证弹窗 ──
            verify_type = await lsm.check_verify_dialog(conn.page)
            if verify_type == "sms":
                log.warning(f"    📱 [{account_id}] 触发短信验证，自动恢复...")
                await lsm.recover_sms(conn.page, account_id)
                # 跳过当前步
                log.info(f"    ⏭️ 跳过当前操作 [{sn}]")
            elif verify_type == "captcha":
                log.warning(f"    🔐 [{account_id}] 滑块验证，需手动处理")
                # 上报但不中断（留给你手动处理）

            # ── 钩子3: 冷却管理 ──
            cooldown = self._get_cooldown(op_name)
            await asyncio.sleep(cooldown)

        return report

    def _get_cooldown(self, op_name: str) -> float:
        """操作完成后冷却时间（自动去掉 xhs_/dy_ 前缀匹配）"""
        import random, re
        COOLDOWNS = {
            "like":       (2, 4),
            "collect":    (3, 6),
            "comment":    (30, 45),
            "post_comment": (30, 45),
            "follow":     (10, 20),
            "search":     (3, 6),
            "scroll_feed": (2, 3),
            "wait_watch":  (0, 0),   # wait_watch 自带等待
        }
        # 去掉 xhs_/dy_ 前缀再匹配
        base_name = re.sub(r'^(xhs_|dy_|xhs_|dy_)', '', op_name)
        base = COOLDOWNS.get(base_name, COOLDOWNS.get(op_name, (2, 5)))
        return random.uniform(*base)

    async def _run_identity_group(self, group_accts: List[dict]) -> List[AccountRunReport]:
        """运行同一身份下的所有账号（共用一个浏览器）"""
        reports = []
        identity_dir = group_accts[0].get("identity_dir", group_accts[0]["id"]).replace("identities/", "")

        # ── 浏览器数限制检查（L2 层，谁开浏览器谁检查）──
        import subprocess as _sp
        while True:
            try:
                out = _sp.run("pgrep -f camoufox | wc -l", shell=True, capture_output=True, text=True, timeout=5)
                count = int(out.stdout.strip() or 0)
            except:
                count = 0
            if count < self.max_browsers:
                break
            log.warning(f"  ⏳ 已达最大浏览器数({self.max_browsers})，等待其他任务释放...")
            await asyncio.sleep(15)

        if check_cookie(identity_dir) == "no_identity":
            log.warning(f"  ⏭️ 身份 {identity_dir}: 身份目录不存在，全部跳过")
            for acct in group_accts:
                for r in range(1, self.rounds_total + 1):
                    rpt = AccountRunReport(acct["id"], "", r)
                    rpt.skipped = True
                    reports.append(rpt)
            return reports
        
        # cookie 不存在或过期 → 让 ensure_login 恢复链处理
        if check_cookie(identity_dir) in ("no_cookie", "expired", "error"):
            log.info(f"  🔐 [{identity_dir}] cookie 状态需恢复，由 LoginStateMachine 处理")

        from cdp_connector import CDPConnector
        conn = CDPConnector(browser_type="camoufox", headless=False,
                            window=(802, 783),
                            identity_dir=str(IDENTITIES_ROOT / identity_dir))
        try:
            await conn.connect()
            await conn.init_anti_detection()
            log.info(f"  🖥️ 浏览器已启动 [身份: {identity_dir}]")

            # 按平台排序：先抖音后小红书
            sorted_accts = sorted(group_accts, key=lambda a: (a.get("platform", "") == "xiaohongshu", a.get("platform", "")))

            for acct_info in sorted_accts:
                acct_id = acct_info["id"]
                for round_idx in range(1, self.rounds_total + 1):
                    bp_name = self._pick_blueprint(round_idx)
                    rpt = await self._run_acct_on_conn(acct_info, bp_name, round_idx, conn)
                    reports.append(rpt)
                    if round_idx < self.rounds_total:
                        wait = random.uniform(5, 10)
                        log.info(f"  ⏳ [{acct_id}] 等待 {wait:.0f}s...")
                        await asyncio.sleep(wait)

        except Exception as e:
            log.error(f"  ❌ 身份 {identity_dir}: {e}")
            for acct in group_accts:
                if not any(r.account == acct["id"] and r.blueprint for r in reports):
                    rpt = AccountRunReport(acct["id"], "", 1)
                    rpt.failed = 99
                    reports.append(rpt)
        finally:
            if not self.keep_open:
                await conn.close()
                log.info(f"  🛑 浏览器已关闭 [身份: {identity_dir}]")

        return reports

    async def run(self) -> BatchReport:
        report = BatchReport()
        report.accounts = self.accounts; report.blueprints = self.blueprints
        report.rounds_total = self.rounds_total; report.mix_mode = self.mix

        # 1. 按身份分组
        groups = group_accounts_by_identity(self.accounts)
        if not groups:
            report.error = "没有有效的账号"
            return report

        log.info(f"\n{'='*50}")
        log.info(f"  🚀 批量执行计划")
        log.info(f"     身份组: {len(groups)}")
        for ident, accts in groups.items():
            log.info(f"       🖥️ {ident} → {[a['id'] for a in accts]}")
        log.info(f"     每账号 {self.rounds_total} 轮 | 蓝图: {self.blueprints}")
        log.info(f"{'='*50}")

        # 2. 解析错峰参数
        try:
            s_min, s_max = [int(x) for x in self.stagger.split("-")]
        except:
            s_min, s_max = 15, 30

        # 3. 并行执行身份组（Semaphore 控制并发数 = max_browsers）
        sem = asyncio.Semaphore(self.max_browsers)
        all_reports = []

        async def _run_one_group(ident, accts):
            async with sem:
                log.info(f"\n  🖥️ 启动身份组 [{ident}]")
                return await self._run_identity_group(accts)

        group_list = list(groups.items())
        tasks = [asyncio.create_task(_run_one_group(ident, accts))
                 for ident, accts in group_list]
        for coro in asyncio.as_completed(tasks):
            group_reports = await coro
            all_reports.extend(group_reports)

        report.account_reports = all_reports

        # 写入标准结果文件（供 CommandBus / 看板读取）
        if self.run_id:
            try:
                from mc.execution_policy import write_result
                status = "completed" if not report.error else "failed"
                write_result(self.run_id, status, report=report.to_dict(),
                            error=report.error)
            except:
                pass

        return report
