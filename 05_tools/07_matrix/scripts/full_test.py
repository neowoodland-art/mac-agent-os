#!/usr/bin/env python3
"""
全面测试脚本 — 启动双账号 Chrome + 运行蓝图 + 生成测试报告

用法:
  python full_test.py                    # 完整测试（启动Chrome + 运行蓝图）
  python full_test.py --skip-launch      # 跳过Chrome启动（假设已手动启动）
  python full_test.py --account-only douyin_01  # 只测试一个账号
"""
import argparse
import asyncio
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── 路径 ──
from local_paths import data_path, profiles_path, logs_path, code_dir
BASE_DIR = code_dir()
SCRIPTS_DIR = Path(__file__).parent
DB_PATH = data_path("matrix.db")
BLUEPRINT_DIR = code_dir() / "blueprints"
PROFILES_DIR = profiles_path()
LOG_DIR = logs_path()
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 视口配置
VIEWPORT = {"width": 702, "height": 783, "mobile": False}

# 测试账号列表
TEST_ACCOUNTS = [
    {"id": "douyin_01", "port": 9222, "profile": "account_01"},
    {"id": "douyin_02", "port": 9223, "profile": "douyin_02"},
]

# 要测试的蓝图
TEST_BLUEPRINTS = ["douyin_browse_v2", "douyin_search_browse"]

# 测试结果收集
test_results = []


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "  ", "OK": "✅", "FAIL": "❌", "WARN": "⚠️", "STEP": "▶️"}.get(level, "  ")
    print(f"[{ts}] {prefix} {msg}")


# ── Chrome 管理 ──

def kill_chrome_on_port(port: int):
    """关闭指定端口的 Chrome"""
    try:
        result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True, timeout=5)
        pids = [int(p) for p in result.stdout.strip().splitlines() if p.strip()]
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        if pids:
            time.sleep(3)
            # 检查是否退出
            for pid in pids:
                try:
                    os.kill(pid, 0)
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            time.sleep(1)
    except Exception:
        pass


def launch_chrome(account: dict) -> bool:
    """启动 Chrome 实例"""
    profile_dir = PROFILES_DIR / account["profile"]
    profile_dir.mkdir(parents=True, exist_ok=True)
    port = account["port"]

    cmd = [
        CHROME,
        f'--remote-debugging-port={port}',
        f'--user-data-dir={profile_dir}',
        '--no-first-run', '--no-default-browser-check',
        '--disable-extensions', '--disable-background-networking',
        '--disable-sync', '--disable-component-update',
        '--disable-features=TranslateUI',
        f'--window-size={VIEWPORT["width"]},{VIEWPORT["height"]}',
        '--window-position=100,100',
    ]

    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 等待 CDP 就绪
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for i in range(20):
        time.sleep(1)
        try:
            with opener.open(f"http://localhost:{port}/json/version", timeout=3) as r:
                json.loads(r.read())
                return True
        except Exception:
            pass
    return False


def is_chrome_running(port: int) -> bool:
    """检查 Chrome 是否在指定端口运行"""
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://localhost:{port}/json/version", timeout=3) as r:
            json.loads(r.read())
            return True
    except Exception:
        return False


# ── 蓝图执行器（使用 douyin_ops 原子操作）──

async def run_blueprint_for_account(account: dict, blueprint_name: str) -> dict:
    """运行单个账号的蓝图，返回测试结果"""
    account_id = account["id"]
    port = account["port"]
    result = {
        "account": account_id,
        "port": port,
        "blueprint": blueprint_name,
        "steps": [],
        "success": False,
        "error": None,
        "duration": 0,
        "login_status": False,
    }

    t_start = time.time()

    try:
        # 1. 连接 Chrome
        log(f"连接 Chrome（端口 {port}）...", "STEP")
        from patchright.async_api import async_playwright
        import urllib.request

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://localhost:{port}/json/version", timeout=5) as r:
            ws_url = json.loads(r.read())["webSocketDebuggerUrl"]

        pw = await async_playwright().start()
        browser = await pw.chromium.connect_over_cdp(ws_url)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        # 2. 注入指纹
        log("注入浏览器指纹...", "STEP")
        cdp = await context.new_cdp_session(page)

        # 视口覆盖
        await cdp.send("Emulation.setDeviceMetricsOverride", {
            "width": VIEWPORT["width"], "height": VIEWPORT["height"],
            "deviceScaleFactor": 1, "mobile": VIEWPORT["mobile"],
        })
        # 时区
        await cdp.send("Emulation.setTimezoneOverride", {"timezoneId": "Asia/Shanghai"})
        # 语言
        await cdp.send("Emulation.setLocaleOverride", {"locale": "zh-CN"})

        # App 跳转拦截
        blocked_schemes = [
            "xhdsdiscover://*", "snssdk1128://*", "snssdk1233://*",
            "kuaishou://*", "zhihu://*", "weixin://*",
            "alipays://*", "taobao://*", "openapp.jdmobile://*", "intent://*",
        ]
        await cdp.send("Fetch.enable", {
            "patterns": [{"urlPattern": s, "requestStage": "Request"} for s in blocked_schemes]
        })
        async def handle_paused(event):
            try:
                await cdp.send("Fetch.failRequest", {"requestId": event["requestId"], "errorReason": "Aborted"})
            except Exception:
                pass
        cdp.on("Fetch.requestPaused", handle_paused)

        # WebGL + webdriver 隐藏
        await page.add_init_script("""
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {
                if (param === 37445) return 'Google Inc. (NVIDIA)';
                if (param === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER, OpenGL 4.6)';
                return getParameter.call(this, param);
            };
            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(param) {
                if (param === 37445) return 'Google Inc. (NVIDIA)';
                if (param === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER, OpenGL 4.6)';
                return getParameter2.call(this, param);
            };
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            const originalUA = navigator.userAgent;
            Object.defineProperty(navigator, 'userAgent', { get: () => originalUA.replace('Headless', '') });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
        """)

        # 3. 检查登录状态
        log("检查登录状态...", "STEP")
        await page.goto('https://www.douyin.com/', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(3)

        avatar = page.locator("[data-e2e='user-avatar']")
        logged_in = await avatar.count() > 0
        result["login_status"] = logged_in
        log(f"登录状态: {'✅ 已登录' if logged_in else '❌ 未登录'}", "OK" if logged_in else "WARN")

        # 4. 加载蓝图
        bp_path = BLUEPRINT_DIR / f"{blueprint_name}.json"
        if not bp_path.exists():
            result["error"] = f"蓝图文件不存在: {bp_path}"
            log(f"蓝图文件不存在: {bp_path}", "FAIL")
            await pw.stop()
            return result

        with open(bp_path, encoding='utf-8') as f:
            blueprint = json.load(f)

        # 5. 执行蓝图步骤
        sys.path.insert(0, str(SCRIPTS_DIR))
        from douyin_ops import DouyinOps

        ops = DouyinOps(page)
        steps = blueprint.get("steps", [])

        log(f"开始执行蓝图 [{blueprint_name}]，共 {len(steps)} 步", "STEP")

        for i, step in enumerate(steps, 1):
            op_name = step.get("op", "?")
            args = step.get("args", {})
            step_id = step.get("step_id", i)

            step_result = {
                "step": i,
                "op": op_name,
                "args": str(args),
                "success": False,
                "error": None,
                "duration_ms": 0,
            }

            t_step = time.time()
            try:
                # 映射操作名到 DouyinOps 方法
                method = getattr(ops, op_name, None)
                if method is None:
                    step_result["error"] = f"未知操作: {op_name}"
                    log(f"  步骤 {i}/{len(steps)} [{op_name}] → ❌ 未知操作", "FAIL")
                else:
                    # 调用原子操作
                    ret = await method(step_id=step_id, **args)

                    # 判断成功（post_comment 返回字符串）
                    if isinstance(ret, str):
                        step_result["success"] = ret in ('ok', 'verify_needed')
                        if ret == 'verify_needed':
                            step_result["error"] = "触发验证码"
                            log(f"  步骤 {i}/{len(steps)} [{op_name}] → ⚠️ 触发验证码", "WARN")
                        else:
                            log(f"  步骤 {i}/{len(steps)} [{op_name}] → ✅", "OK")
                    elif isinstance(ret, bool):
                        step_result["success"] = ret
                        log(f"  步骤 {i}/{len(steps)} [{op_name}] → {'✅' if ret else '❌'}", "OK" if ret else "FAIL")
                    else:
                        step_result["success"] = True
                        log(f"  步骤 {i}/{len(steps)} [{op_name}] → ✅", "OK")

            except Exception as e:
                step_result["error"] = str(e)
                log(f"  步骤 {i}/{len(steps)} [{op_name}] → ❌ {e}", "FAIL")

            step_result["duration_ms"] = int((time.time() - t_step) * 1000)
            result["steps"].append(step_result)

            # 步骤间等待
            wait_after = step.get("wait_after", 1.5)
            wait_jitter = step.get("wait_jitter", 0.5)
            if wait_after > 0:
                import random
                await asyncio.sleep(wait_after + random.uniform(-wait_jitter, wait_jitter))

        # 统计结果
        total = len(result["steps"])
        passed = sum(1 for s in result["steps"] if s["success"])
        result["success"] = passed == total
        result["duration"] = round(time.time() - t_start, 1)

        log(f"蓝图 [{blueprint_name}] 完成: {passed}/{total} 步成功，耗时 {result['duration']}s",
            "OK" if result["success"] else "FAIL")

        # 获取操作统计
        summary = ops.get_action_summary()
        result["action_summary"] = summary
        log(f"操作统计: {summary}", "INFO")

        await pw.stop()

    except Exception as e:
        result["error"] = str(e)
        result["duration"] = round(time.time() - t_start, 1)
        log(f"测试异常: {e}", "FAIL")

    return result


# ── 主测试流程 ──

async def run_full_test(skip_launch: bool = False, account_only: str = None):
    """执行完整测试"""
    global test_results

    print(f"\n{'='*70}")
    print(f"🧪 Matrix 养号系统全面测试")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    # 确定测试账号
    accounts = TEST_ACCOUNTS
    if account_only:
        accounts = [a for a in accounts if a["id"] == account_only]
        if not accounts:
            log(f"未找到账号: {account_only}", "FAIL")
            return

    # 阶段1: 启动 Chrome
    if not skip_launch:
        print(f"\n{'─'*70}")
        print("📋 阶段1: 启动 Chrome 实例")
        print(f"{'─'*70}")

        for acc in accounts:
            port = acc["port"]
            # 先检查是否已运行
            if is_chrome_running(port):
                log(f"{acc['id']} (端口 {port}) 已运行，跳过启动", "INFO")
            else:
                log(f"启动 {acc['id']} (端口 {port}, Profile: {acc['profile']})...", "STEP")
                ok = launch_chrome(acc)
                if ok:
                    log(f"{acc['id']} Chrome 启动成功", "OK")
                else:
                    log(f"{acc['id']} Chrome 启动超时", "FAIL")

        # 等待所有 Chrome 就绪
        await asyncio.sleep(2)
    else:
        log("跳过 Chrome 启动（使用已运行实例）", "INFO")

    # 阶段2: 逐账号测试蓝图
    print(f"\n{'─'*70}")
    print("📋 阶段2: 执行养号蓝图测试")
    print(f"{'─'*70}")

    for acc in accounts:
        print(f"\n{'='*50}")
        print(f"🧪 测试账号: {acc['id']} (端口 {acc['port']})")
        print(f"{'='*50}")

        for bp_name in TEST_BLUEPRINTS:
            log(f"▶ 开始测试蓝图: {bp_name}", "STEP")
            result = await run_blueprint_for_account(acc, bp_name)
            test_results.append(result)

            # 蓝图间休息
            log("蓝图间休息 5 秒...", "INFO")
            await asyncio.sleep(5)

    # 阶段3: 生成测试报告
    print(f"\n{'─'*70}")
    print("📋 阶段3: 生成测试报告")
    print(f"{'─'*70}")

    report = generate_report(test_results)
    print(report)

    # 保存报告
    report_path = BASE_DIR / "docs" / "TEST_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    log(f"测试报告已保存到: {report_path}", "OK")

    return test_results


def generate_report(results: list) -> str:
    """生成 Markdown 测试报告"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        f"# Matrix 养号系统全面测试报告",
        f"",
        f"> **测试时间**: {now}",
        f"> **测试蓝图**: {', '.join(TEST_BLUEPRINTS)}",
        f"> **测试账号**: {', '.join(a['id'] for a in TEST_ACCOUNTS)}",
        f"",
        f"---",
        f"",
    ]

    # 总览
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["success"])
    lines.append(f"## 测试总览")
    lines.append(f"")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 总测试数 | {total_tests} |")
    lines.append(f"| 通过数 | {passed_tests} |")
    lines.append(f"| 失败数 | {total_tests - passed_tests} |")
    lines.append(f"| 通过率 | {passed_tests/total_tests*100:.0f}% |")
    lines.append(f"")

    # 按账号分
    lines.append(f"## 按账号汇总")
    lines.append(f"")
    lines.append(f"| 账号 | 蓝图 | 登录 | 步骤通过 | 总步骤 | 耗时 | 结果 |")
    lines.append(f"|------|------|------|---------|--------|------|------|")

    for r in results:
        passed_steps = sum(1 for s in r["steps"] if s["success"])
        total_steps = len(r["steps"])
        login_icon = "✅" if r["login_status"] else "❌"
        result_icon = "✅" if r["success"] else "❌"
        lines.append(f"| {r['account']} | {r['blueprint']} | {login_icon} | {passed_steps} | {total_steps} | {r['duration']}s | {result_icon} |")
    lines.append(f"")

    # 详细步骤
    lines.append(f"## 详细步骤结果")
    lines.append(f"")

    for r in results:
        lines.append(f"### {r['account']} / {r['blueprint']}")
        lines.append(f"")
        if r.get("error"):
            lines.append(f"**整体错误**: {r['error']}")
            lines.append(f"")
        lines.append(f"| 步骤 | 操作 | 参数 | 结果 | 耗时 | 错误 |")
        lines.append(f"|------|------|------|------|------|------|")
        for s in r["steps"]:
            icon = "✅" if s["success"] else "❌"
            err = s.get("error", "") or ""
            # 截断过长的参数
            args_str = s.get("args", "")
            if len(args_str) > 40:
                args_str = args_str[:37] + "..."
            lines.append(f"| {s['step']} | {s['op']} | {args_str} | {icon} | {s['duration_ms']}ms | {err} |")
        lines.append(f"")

    # 问题分析
    lines.append(f"## 问题分析与改进建议")
    lines.append(f"")

    issues = []
    for r in results:
        # 未登录
        if not r["login_status"]:
            issues.append({
                "severity": "P1",
                "category": "登录",
                "account": r["account"],
                "desc": f"{r['account']} 未登录，部分互动操作可能受限",
                "fix": "手动登录该账号，或使用 --export-cookies 导出后切换"
            })
            # 步骤失败
        for s in r["steps"]:
            if not s["success"]:
                issues.append({
                    "severity": "P0" if s["op"] in ("goto_home", "search") else "P1",
                    "category": "操作失败",
                    "account": r["account"],
                    "desc": f"步骤 {s['step']} [{s['op']}] 失败: {s.get('error') or '未知原因'}",
                    "fix": _suggest_fix(s["op"], s.get("error"))
                })

    if issues:
        lines.append(f"| 严重度 | 类别 | 账号 | 问题 | 改进建议 |")
        lines.append(f"|--------|------|------|------|---------|")
        for iss in issues:
            lines.append(f"| {iss['severity']} | {iss['category']} | {iss['account']} | {iss['desc']} | {iss['fix']} |")
    else:
        lines.append(f"🎉 没有发现问题！所有测试通过。")

    lines.append(f"")

    # 系统检查
    lines.append(f"## 系统级检查")
    lines.append(f"")
    lines.append(f"| 检查项 | 状态 | 说明 |")
    lines.append(f"|--------|------|------|")

    # Chrome 版本
    try:
        result = subprocess.run([CHROME, '--version'], capture_output=True, text=True, timeout=5)
        chrome_ver = result.stdout.strip()
    except Exception:
        chrome_ver = "未检测到"
    lines.append(f"| Chrome 版本 | {'✅' if chrome_ver != '未检测到' else '❌'} | {chrome_ver} |")

    # Patchright
    try:
        from patchright import __version__ as pw_ver
        lines.append(f"| Patchright | ✅ | {pw_ver} |")
    except Exception:
        lines.append(f"| Patchright | ❌ | 未安装 |")

    # 数据库
    if DB_PATH.exists():
        lines.append(f"| 数据库 | ✅ | {DB_PATH} |")
    else:
        lines.append(f"| 数据库 | ❌ | 不存在 |")

    # 蓝图文件
    for bp in TEST_BLUEPRINTS:
        bp_path = BLUEPRINT_DIR / f"{bp}.json"
        lines.append(f"| 蓝图 {bp} | {'✅' if bp_path.exists() else '❌'} | {bp_path} |")

    lines.append(f"")

    return "\n".join(lines)


def _suggest_fix(op: str, error: str) -> str:
    """根据操作和错误提供建议"""
    error = error or ""
    if "未找到" in error or "not found" in error.lower():
        if op == "goto_home":
            return "检查抖音是否可访问，或页面加载超时"
        return "检查 data-e2e 选择器是否变更，运行选择器扫描"
    if "timeout" in error.lower():
        return "增加等待时间或检查网络连接"
    if "验证码" in error:
        return "评论频率过高，降低评论频率或跳过评论操作"
    if "connect" in error.lower():
        return "检查 Chrome CDP 端口是否开启"
    return "需要进一步调查"


async def main():
    parser = argparse.ArgumentParser(description="Matrix 全面测试")
    parser.add_argument("--skip-launch", action="store_true", help="跳过 Chrome 启动")
    parser.add_argument("--account-only", type=str, help="只测试指定账号")
    args = parser.parse_args()

    await run_full_test(skip_launch=args.skip_launch, account_only=args.account_only)


if __name__ == "__main__":
    asyncio.run(main())
