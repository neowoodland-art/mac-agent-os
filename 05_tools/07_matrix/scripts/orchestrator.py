#!/usr/bin/env python3
"""
YanghaoOrchestrator — 养号调度器 (v1.0.0)

统一调度 BrowserManager + AtomOps + PageState + Blueprint

用法:
    # Python 调用
    orch = YanghaoOrchestrator()
    report = await orch.run(account_id="douyin_01", blueprint_id="douyin_browse_v3")

    # 命令行
    python orchestrator.py --account douyin_01 --blueprint douyin_browse_v3
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

__version__ = "1.0.0"

# 路径
TOOL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = TOOL_DIR / "scripts"
BP_DIR = TOOL_DIR / "blueprints"
sys.path.insert(0, str(SCRIPTS_DIR))


class StepResult:
    """单步执行结果"""
    def __init__(self, step_id, op, atom_result=None, skipped=False):
        self.step_id = step_id
        self.op = op
        self.atom_result = atom_result
        self.skipped = skipped
        self.time = datetime.now().isoformat()

    def __str__(self):
        if self.skipped:
            return f"  ⏭️ [{self.step_id:2d}] {self.op} (跳过)"
        if self.atom_result:
            return f"  {self.atom_result}"
        return f"  ➡️ [{self.step_id:2d}] {self.op}"


class RunReport:
    """一次养号运行报告"""
    def __init__(self, account_id: str, blueprint_id: str):
        self.account_id = account_id
        self.blueprint_id = blueprint_id
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.steps: list = []
        self.error: Optional[str] = None

    def add_step(self, result: StepResult):
        self.steps.append(result)

    def finish(self):
        self.end_time = datetime.now()

    @property
    def duration(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    @property
    def passed(self) -> int:
        return sum(1 for s in self.steps if s.atom_result and s.atom_result.success)

    @property
    def failed(self) -> int:
        return sum(1 for s in self.steps if s.atom_result and not s.atom_result.success and not s.skipped)

    @property
    def total(self) -> int:
        return len(self.steps)

    def print_summary(self):
        print(f"\n{'='*55}")
        print(f" 📊 养号报告")
        print(f"{'='*55}")
        print(f"  账号:   {self.account_id}")
        print(f"  蓝图:   {self.blueprint_id}")
        print(f"  耗时:   {self.duration:.0f}秒")
        print(f"  步骤:   {self.passed}/{self.total} 通过")
        if self.failed:
            print(f"  失败:   {self.failed}")
        if self.error:
            print(f"  异常:   {self.error}")
        print(f"{'='*55}")
        print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print()


class YanghaoOrchestrator:
    """养号调度器 — 统一管理浏览器生命周期和操作执行"""

    def __init__(self):
        self._bm = None
        self._page = None

    # ─── 加载配置 ──────────────────────────────────────────────

    def _load_blueprint(self, blueprint_id: str) -> dict:
        """加载蓝图"""
        bp_file = BP_DIR / f"{blueprint_id}.json"
        if not bp_file.exists():
            # 自动补全 v3 后缀
            bp_file_v3 = BP_DIR / f"{blueprint_id}.json"
            if not bp_file_v3.exists():
                raise FileNotFoundError(f"蓝图不存在: {blueprint_id}")
        return json.loads(bp_file.read_text())

    # ─── 执行 ──────────────────────────────────────────────────

    async def run(self, account_id: str, blueprint_id: str) -> RunReport:
        """执行一次养号"""
        report = RunReport(account_id, blueprint_id)

        try:
            from browser_manager import BrowserManager
            from atom_ops import AtomOps
            from page_state import PageState

            # 1. 启动浏览器
            print(f"\n{'='*55}")
            print(f" 🚀 启动养号: {account_id}")
            print(f"{'='*55}")
            print(f"  蓝图: {blueprint_id}")
            print()

            self._bm = BrowserManager()
            launch_info = await self._bm.launch(account_id)
            bt = launch_info["type"]

            # 2. 获取 page (Chrome 直接从 persistent context 拿)
            if bt == "chrome":
                self._page = launch_info.get("page") or self._bm.page
            else:
                # Camoufox: 从 browser 创建 page
                browser = launch_info.get("browser")
                if browser:
                    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
                    self._page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                else:
                    self._page = self._bm.page
            print(f"  ✅ 浏览器已连接 ({bt})")

            # 3. 初始化操作层
            from douyin_ops import DouyinOps
            ops = AtomOps(self._page)
            state = PageState(self._page)
            dyops = DouyinOps(self._page)

            # 注入 ops 的 dyops 引用
            ops._dyops = dyops

            # 4. 登录检查和处理
            login_state = await self._bm.detect_login_state(self._page)
            print(f"  登录状态: {login_state['status']} ({login_state['detail']})")
            
            if login_state["status"] == "lost":
                print("  ⚠️  登录态丢失，自动注入保存的 Cookie...")
                ok = await self._bm.inject_cookies(self._page)
                if not ok:
                    print("  ❌ Cookie 注入失败，请手动登录!")
                    print(f"  请打开浏览器登录抖音后，重新运行")
                    raise Exception("登录态丢失")
                print(f"  ✅ Cookie 已注入")
            elif login_state["status"] == "cookie_available":
                ok = await self._bm.inject_cookies(self._page)
                print(f"  {'✅ Cookie 已自动注入' if ok else '❌ Cookie 注入失败'}")
            else:
                print(f"  ✅ 已通过 {login_state['method']} 保持登录")
            print()

            # 5. 应用浏览器指纹保护
            print()
            print("  🔒 应用反检测保护...")
            await self._bm.apply_fingerprint_protection(self._page)
            
            # 6. 初始化行为画像
            from anti_detection import BehaviorProfile
            profile = BehaviorProfile(account_id)
            
            # 7. 激活手机模式（刷新触发）
            print("  📱 激活手机模式...")
            await self._bm.activate_mobile_mode(self._page)
            print("  手机模式: ✅")
            
            # 8. 清理初始弹窗
            await self._bm.remove_overlays(self._page)
            print()

            # 6. 执行蓝图
            blueprint = self._load_blueprint(blueprint_id)
            steps = blueprint.get("steps", [])
            print(f"  蓝图步骤: {len(steps)} 步")
            print()

            for step in steps:
                step_id = step.get("step_id", "?")
                op = step.get("op", "?")
                args = step.get("args", {})
                wait_after = step.get("wait_after", 1)

                # 查找对应原子操作
                func = getattr(ops, op, None)
                if not func:
                    report.add_step(StepResult(step_id, op, skipped=True))
                    print(f"  ⏭️ [{step_id:2d}] {op} (无此操作)")
                    await asyncio.sleep(1)
                    continue

                # 执行（参数路由）
                try:
                    if op == "goto_home":
                        activate = args.get("activate_mobile", False)
                        r = await ops.goto_home(activate_mobile=activate)
                    elif op == "open_video":
                        r = await ops.open_video()
                    elif op == "wait_watch":
                        secs = args.get("seconds", 8)
                        r = await ops.wait_watch(seconds=secs)
                    elif op == "like":
                        r = await ops.like()
                    elif op == "collect":
                        r = await ops.collect()
                    elif op == "next_video":
                        r = await ops.next_video()
                    elif op == "scroll_feed":
                        r = await ops.scroll_feed()
                    elif op == "search":
                        kw = args.get("keyword", "美食推荐")
                        r = await ops.search(kw)
                    elif op == "check_login":
                        r = await ops.check_login()
                    else:
                        r = AtomResult(op, True, "未实现,跳过")
                        print(f"  ➡️ [{step_id:2d}] {op} (未实现)")
                except Exception as e:
                    r = AtomResult(op, False, f"异常:{type(e).__name__}")

                sr = StepResult(step_id, op, atom_result=r)
                report.add_step(sr)
                print(sr)

                # 等待
                await asyncio.sleep(wait_after)

            report.finish()
            report.print_summary()

        except Exception as e:
            report.error = f"{type(e).__name__}: {str(e)[:100]}"
            report.finish()
            print(f"\n❌ 运行异常: {report.error}")

        finally:
            # 关闭浏览器
            if self._bm:
                await self._bm.close()

        return report


# ─── 命令行入口 ────────────────────────────────────────────────

async def main_cli():
    parser = argparse.ArgumentParser(description="养号调度器 v1.0.0")
    parser.add_argument("--account", "-a", required=True, help="账号ID")
    parser.add_argument("--blueprint", "-b", default="douyin_browse_v3", help="蓝图ID")
    parser.add_argument("--list-accounts", action="store_true", help="列出可用账号")
    parser.add_argument("--list-blueprints", action="store_true", help="列出可用蓝图")
    args = parser.parse_args()

    if args.list_accounts:
        import yaml
        from local_paths import config_path
        acct_file = config_path("accounts.yaml")
        data = yaml.safe_load(open(acct_file))
        print("可用账号:")
        for a in data.get("accounts", []):
            if a.get("enabled") and a.get("platform") == "douyin":
                bt = a.get("browser_type", "chrome")
                print(f"  {a['id']:20s} | {a.get('display_name','?'):16s} | {a.get('phone','?'):15s} | {bt}")
        return

    if args.list_blueprints:
        print("可用蓝图:")
        for f in sorted(BP_DIR.glob("*.json")):
            bp = json.loads(f.read_text())
            print(f"  {bp.get('id', f.stem):30s} v{bp.get('version','?')} | {bp.get('description','')[:50]}")
        return

    orch = YanghaoOrchestrator()
    await orch.run(args.account, args.blueprint)


if __name__ == "__main__":
    asyncio.run(main_cli())
