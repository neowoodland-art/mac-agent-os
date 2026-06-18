#!/usr/bin/env python3
"""
养号启动器 — 交互选择 + 参数模式

用法:
  # 交互模式（菜单选择）
  python yanghao_runner.py

  # 参数模式（直接运行）
  python yanghao_runner.py --account douyin_01 --blueprint douyin_browse_v2
  python yanghao_runner.py --account douyin_01 --blueprint douyin_browse_v2 --browser chrome
  python yanghao_runner.py --account douyin_camo01 --blueprint douyin_search_browse --browser camoufox
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# ─── 路径 ───
TOOL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = TOOL_DIR / "scripts"
from matrix_mgmt import AGENT_LOCAL
LOCAL_ROOT = AGENT_LOCAL / "tools" / "matrix"
CONFIG_DIR = LOCAL_ROOT / "config"
BP_DIR = TOOL_DIR / "blueprints"
sys.path.insert(0, str(SCRIPTS_DIR))

# ─── 加载配置 ───

def load_accounts():
    import yaml
    with open(CONFIG_DIR / "accounts.yaml") as f:
        data = yaml.safe_load(f)
    return [a for a in data.get("accounts", []) if a.get("enabled") and a.get("platform") == "douyin"]


def load_blueprints():
    bps = []
    for f in sorted(BP_DIR.glob("*.json")):
        bp = json.loads(f.read_text())
        bps.append({
            "id": bp.get("id", bp.get("name", f.stem)),
            "name": bp.get("name", f.stem),
            "steps": len(bp.get("steps", [])),
            "desc": bp.get("description", ""),
            "file": str(f),
        })
    return bps


# ─── 交互菜单 ───

def pick_account(accounts):
    print("\n" + "=" * 55)
    print(" 📋 请选择账号")
    print("=" * 55)
    for i, ac in enumerate(accounts, 1):
        browser = ac.get("browser_type", "chrome")
        nick = ac.get("display_name", "?")
        phone = ac.get("phone", "")
        notes = ac.get("notes", "")
        status = "🟢" if ac.get("enabled") else "⚪"
        print(f"  [{i}] {status} {nick:12s} | {phone:15s} | {browser:8s} | {notes}")
    print()
    
    while True:
        try:
            choice = input(f"  请输入编号 (1-{len(accounts)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(accounts):
                return accounts[idx]
        except ValueError:
            pass
        print(f"  ⚠️ 请输入 1-{len(accounts)}")


def pick_blueprint(blueprints):
    print("\n" + "=" * 55)
    print(" 📋 请选择蓝图")
    print("=" * 55)
    for i, bp in enumerate(blueprints, 1):
        print(f"  [{i}] {bp['name']:30s} ({bp['steps']}步) - {bp['desc'][:40]}")
    print()
    
    while True:
        try:
            choice = input(f"  请输入编号 (1-{len(blueprints)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(blueprints):
                return blueprints[idx]
        except ValueError:
            pass
        print(f"  ⚠️ 请输入 1-{len(blueprints)}")


# ─── 执行 ───

async def run_yanghao(account, blueprint, browser_type=None):
    """执行养号流程"""
    from cdp_connector import CDPConnector
    from douyin_ops import DouyinOps
    
    # 确定浏览器类型
    bt = browser_type or account.get("browser_type", "chrome")
    is_camoufox = bt in ("camoufox", "firefox")
    
    acct_id = account["id"]
    nick = account.get("display_name", acct_id)
    port = account.get("port", 9222)
    bp_name = blueprint["name"]
    bp_file = blueprint["file"]
    
    print(f"\n{'='*55}")
    print(f" 🔥 启动养号")
    print(f"{'='*55}")
    print(f"  账号:   {nick} ({acct_id})")
    print(f"  浏览器: {'Camoufox (Firefox)' if is_camoufox else 'Chrome'}")
    print(f"  蓝图:   {bp_name}")
    print()
    
    # 连接浏览器
    if is_camoufox:
        conn = CDPConnector(browser_type="camoufox", headless=False, window=(702, 783))
    else:
        # Chrome 模式：检测 CDP 端口
        import urllib.request, subprocess, os, signal
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            opener.open(f"http://localhost:{port}/json/version", timeout=3)
            print(f"  ✅ Chrome 已在端口 {port} 运行")
        except:
            print(f"  ⏳ 启动 Chrome (端口 {port})...")
            chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            profile_dir = str(LOCAL_ROOT / "profiles" / account.get("profile_dir", acct_id))
            subprocess.Popen(
                [chrome, f"--remote-debugging-port={port}", f"--user-data-dir={profile_dir}",
                 "--no-first-run", "--no-default-browser-check", "--window-size=702,783",
                 "about:blank"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            await asyncio.sleep(6)
        
        conn = CDPConnector(port=port)
    
    await conn.connect()
    
    if is_camoufox:
        # 加载 Cookie（Chrome 保存的登录态）
        cookie_file = LOCAL_ROOT / "data" / "cookies" / f"{acct_id}_cookies.json"
        if cookie_file.exists():
            cookies = json.loads(cookie_file.read_text())
            for c in cookies:
                try:
                    await conn.context.add_cookies([{
                        "name": c["name"], "value": c["value"],
                        "domain": c["domain"], "path": c.get("path", "/"),
                        "httpOnly": c.get("httpOnly", False),
                        "secure": c.get("secure", False),
                        "sameSite": c.get("sameSite", "Lax"),
                    }])
                except: pass
            print(f"  ✅ Cookie 已注入 ({len([c for c in cookies if 'douyin' in c.get('domain','')])}个)")
    
    # 反检测
    await conn.init_anti_detection()
    
    # 加载蓝图步骤
    bp = json.loads(Path(bp_file).read_text())
    steps_list = bp.get("steps", [])
    
    dyops = DouyinOps(conn.page)
    
    # 先导航到首页
    print(f"\n  📍 访问抖音首页...")
    await conn.page.goto("https://www.douyin.com/", timeout=20000, wait_until="domcontentloaded")
    await asyncio.sleep(5)
    
    # 找第一个视频进入播放模式
    video_links = await conn.page.evaluate("""() => {
        const all = document.querySelectorAll('a');
        const videos = [];
        for (const a of all) {
            if (a.href && a.href.includes('/video/')) videos.push(a.href);
        }
        return [...new Set(videos)].slice(0, 3);
    }""")
    
    if video_links:
        print(f"  📍 打开视频...")
        await conn.page.goto(video_links[0], timeout=15000, wait_until="domcontentloaded")
        await asyncio.sleep(3)
    
    # 执行流程
    print(f"\n{'='*55}")
    print(f" 养号执行中... ({bp_name})")
    print(f"{'='*55}")
    
    passed = 0
    for step in steps_list:
        sn = step.get("step_id", "?")
        op = step.get("op", "?")
        args = step.get("args", {})
        
        try:
            result = "OK"
            
            if op == "goto_home":
                await conn.page.goto("https://www.douyin.com/", timeout=15000)
                await asyncio.sleep(3)
            elif op == "wait_watch":
                await dyops.wait_watch(step_id=sn, seconds=args.get("seconds", 5))
            elif op in ("like",):
                r = await conn.page.evaluate("""() => {
                    const b = document.querySelector('[data-e2e="feed-active-video-double-like"]');
                    if (b) { b.click(); return '👍'; }
                    const b2 = document.querySelector('[data-e2e="like-count"]');
                    if (b2) { b2.click(); return '👍'; }
                    return '-';
                }""")
                result = r
            elif op in ("collect",):
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
            elif op == "wait":
                await asyncio.sleep(args.get("seconds", 2))
            elif op in ("click_search",):
                await conn.page.evaluate("""() => {
                    const b = document.querySelector('button');
                    if (b) b.click();
                }""")
                await asyncio.sleep(3)
            elif op in ("search",):
                kw = args.get("keyword", "热门")
                await conn.page.evaluate(f"(k) => {{ const i = document.querySelector('input'); if(i) {{ i.value=k; i.dispatchEvent(new Event('input')); }} }}")
                await asyncio.sleep(2)
            elif op == "random_scroll":
                import random
                await conn.page.evaluate(f"() => window.scrollBy(0, {200+random.random()*300})")
                await asyncio.sleep(2)
            else:
                result = f"skip({op})"
            
            print(f"  ✅ [{sn:2d}] {op:15s} → {str(result)[:15]}")
            passed += 1
        except Exception as e:
            print(f"  ⚠️ [{sn:2d}] {op:15s} → {type(e).__name__}")
        
        await asyncio.sleep(1.5)
    
    print(f"\n{'='*55}")
    print(f" 结果: {passed}/{len(steps_list)} 步完成")
    print(f" 账号: {nick} | 浏览器: {'Camoufox' if is_camoufox else 'Chrome'}")
    print(f" 蓝图: {bp_name}")
    print(f"{'='*55}")
    print()
    
    await conn.close()


# ─── 主入口 ───

def main():
    parser = argparse.ArgumentParser(description="抖音养号启动器")
    parser.add_argument("--account", "-a", help="账号ID (douyin_01)")
    parser.add_argument("--blueprint", "-b", help="蓝图ID (douyin_browse_v2)")
    parser.add_argument("--browser", "-B", choices=["auto", "chrome", "camoufox"], default="auto",
                        help="浏览器类型 (默认自动判断)")
    args = parser.parse_args()
    
    accounts = load_accounts()
    blueprints = load_blueprints()
    
    # 参数模式
    if args.account and args.blueprint:
        acct = next((a for a in accounts if a["id"] == args.account), None)
        bp = next((b for b in blueprints if b["id"] == args.blueprint), None)
        if not acct:
            print(f"❌ 账号不存在: {args.account}")
            sys.exit(1)
        if not bp:
            print(f"❌ 蓝图不存在: {args.blueprint}")
            sys.exit(1)
        asyncio.run(run_yanghao(acct, bp, args.browser if args.browser != "auto" else None))
        return
    
    # 交互模式
    print("\n" + "=" * 55)
    print(" 🎯 抖音养号启动器")
    print("=" * 55)
    print(f"  可用账号: {len(accounts)}")
    print(f"  可用蓝图: {len(blueprints)}")
    
    acct = pick_account(accounts)
    bp = pick_blueprint(blueprints)
    
    # 确认
    bt = acct.get("browser_type", "chrome")
    print(f"\n  确认: {acct.get('display_name', acct['id'])} @ {bp['name']}")
    confirm = input("  开始运行? (Y/n): ").strip().lower()
    if confirm and confirm != 'y' and confirm != '':
        print("已取消")
        return
    
    asyncio.run(run_yanghao(acct, bp))


if __name__ == "__main__":
    main()
