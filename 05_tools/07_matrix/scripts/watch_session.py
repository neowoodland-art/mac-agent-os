#!/usr/bin/env python3
"""
watch_session.py — 小红书会话监控（使用现有基础设施）

用 CDPConnector + GracefulBrowser 打开 xhs_01 身份，
截图 + vision_bridge 分析，报告当前页面状态。

不修改任何现有代码。
"""
import sys, os, time, asyncio, json
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from cdp_connector import CDPConnector
from browser_utils import GracefulBrowser
from vision_bridge import analyze_screenshot

SNAP_DIR = Path("/tmp/xhs_watch")
SNAP_DIR.mkdir(exist_ok=True)

async def snap(page, name):
    path = str(SNAP_DIR / f"{name}.png")
    await page.screenshot(path=path, full_page=False)
    return path

async def vision(page, name, question):
    path = await snap(page, name)
    r = analyze_screenshot(path, question)
    text = r.get("text", "")
    print(f"\n📸 截图: {name}.png")
    print(f"🤖 分析 ({r.get('elapsed',0):.1f}s): {text[:300]}")
    return r

async def main():
    print("=" * 60)
    print("  小红书会话监控 — watch_session")
    print("  用现有 CDPConnector + GracefulBrowser")
    print("  账号: xhs_01  身份目录: identities/xhs_01/")
    print("=" * 60)

    # ── 用现有基础设施启动 ──
    identity_dir = str(Path.home() / "workbuddy-agent-os/agent-local/tools/matrix/identities/xhs_01")
    conn = CDPConnector(
        identity_dir=identity_dir,
        browser_type="camoufox",
        headless=False,
        window=(702, 783),
        window_position=(0, 0),
    )
    gb = GracefulBrowser(conn, account_id="xhs_01", timeout_minutes=30)
    await gb.setup(check_running=True)
    await conn.connect()

    page = conn.page
    if not page:
        print("❌ 无法获取 page 对象")
        return

    try:
        # ── Step 1: 打开小红书 ──
        print("\n📌 Step 1: 打开小红书首页")
        await page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)

        # ── Step 2: 视觉分析 ──
        print("\n📌 Step 2: 分析当前状态")
        r1 = await vision(page, "01_state", """
            Current page state: 
            1. Is there a user avatar in top-right (logged in)?
            2. Any login popup/dialog visible?
            3. Any re-verification popup?
            4. Is the main content (notes feed) visible?
            5. Describe what's on screen.
        """)

        # ── Step 3: 检测登录态 ──
        print("\n📌 Step 3: 检测登录态")
        has_avatar = await page.evaluate(
            "() => !!document.querySelector('.user-avatar, [class*=avatar], .reds-count, [class*=user-icon]')"
        )
        print(f"  JS检测 avatar: {has_avatar}")

        # ── Step 4: 如果已登录，标记状态 ──
        if has_avatar:
            print("\n📌 Step 4: ✅ 已登录状态确认")
            print("  浏览器保持打开，你可手动操作或观察")
            print("  如果触发重新验证弹窗，截图分析会报告")
        else:
            print("\n📌 Step 4: 未检测到头像，检查登录弹窗")
            r2 = await vision(page, "02_not_logged", """
                Not logged in. What login options are available?
                Is there a phone number input or SMS login option?
                Describe what the user needs to click for SMS login.
            """)

        # ── Step 5: 保持打开，持续监控 ──
        print(f"\n{'='*60}")
        print(f"  ✅ 浏览器已打开，窗口: 702×783")
        print(f"  ✅ 账号: xhs_01")
        print(f"  ✅ 状态: {'已登录' if has_avatar else '未登录'}")
        print(f"  📸 截图: {SNAP_DIR}/")
        print(f"  💡 你可以在浏览器中操作，我每30秒检查一次状态")
        print(f"{'='*60}")

        check_interval = 30
        while True:
            await asyncio.sleep(check_interval)
            r = await vision(page, f"check_{int(time.time())}", """
                Has anything changed?
                1. Any login/re-verification popup?
                2. Is the avatar still visible (still logged in)?
                3. Any error messages or unexpected dialogs?
            """)
            # 简单的关键词检测
            text = r.get("text", "")
            if any(kw in text for kw in ["重新验证", "登录过期", "验证码", "请登录"]):
                print("  ⚠️ 检测到可能需要重新验证！")
            elif "avatar" in text.lower() or "profile" in text.lower():
                print("  ✅ 登录状态正常")

    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await gb.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
