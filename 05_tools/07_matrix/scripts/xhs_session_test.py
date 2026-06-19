#!/usr/bin/env python3
"""
小红书登录态维护 — 视觉测试（自动步进）

策略：你看着浏览器窗口，我一步步操作并截图分析。
      哪里不对你就喊停，我马上改代码。

步骤：
  1. 打开小红书
  2. 截图 + 视觉分析当前状态
  3. 尝试检测登录态 / 重新验证弹窗
  4. 如果触发了验证 → 视觉定位验证码框 → 等SMS → 填入
"""
import sys, os, json, time, asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vision_bridge import analyze_screenshot, text_chat
from playwright.async_api import async_playwright

SNAP_DIR = Path("/tmp/xhs_auto_test")
SNAP_DIR.mkdir(exist_ok=True)
_log = []

def log(msg):
    _log.append(msg)
    print(f"  {msg}")

async def snap(page, name):
    path = str(SNAP_DIR / f"{name}.png")
    await page.screenshot(path=path, full_page=False)
    return path

async def vision(page, name, question):
    path = await snap(page, name)
    r = analyze_screenshot(path, question)
    log(f"[视觉] {r.get('text','')[:200]}")
    return r

async def main():
    print("=" * 60)
    print("  小红书自动步进测试 — 你看着浏览器窗口")
    print("  每5秒一步，哪里不对你告诉我")
    print("=" * 60)

    async with async_playwright() as p:
        # 使用 Camoufox（Firefox 内核 + 反检测指纹）─ 三台机器统一
        from camoufox import AsyncCamoufox
        browser = await AsyncCamoufox(headless=False).__aenter__()
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()

        try:
            # ═══ Step 1: 打开 ═══
            print(f"\n{'─'*40}\n📌 Step 1/5: 打开小红书")
            await page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)
            log(f"URL: {page.url}")

            # ═══ Step 2: 视觉分析 ═══
            print(f"\n{'─'*40}\n📌 Step 2/5: 视觉分析页面状态")
            await page.wait_for_timeout(3000)
            r = await vision(page, "01_state", """
                Current page state:
                1. Is there a login popup? Describe it.
                2. Is there a user avatar showing logged-in state?
                3. If login dialog: is it showing QR code or phone input?
                4. Is there "已有账号登录" or "短信登录" option?
                5. Any "同意并登录" button?
            """)
            log(f"结论: {'有登录弹窗' if 'login popup' in r.get('text','').lower() or '登录' in r.get('text','')[:50] else '可能已登录'}")

            # ═══ Step 3: 检测登录态 ═══
            print(f"\n{'─'*40}\n📌 Step 3/5: 检测具体登录态")
            has_avatar = await page.evaluate(
                "() => !!document.querySelector('.user-avatar, [class*=avatar], .reds-count, [class*=user-icon], [class*=profile]')"
            )
            has_login_input = await page.evaluate(
                "() => !!document.querySelector('input[placeholder*=\"手机\"], input[type=text][class*=phone]')"
            )
            log(f"  avatar={has_avatar} phone_input={has_login_input}")

            # ═══ Step 4: 尝试切换到短信登录 ═══
            print(f"\n{'─'*40}\n📌 Step 4/5: 尝试短信登录通道")
            # 先看看页面上有什么可点的
            r2 = await vision(page, "02_login_options", """
                If there's a login dialog, look for clickable options:
                1. Is there a tab or button for "短信登录" or "手机号登录"?
                2. Is there "已有账号登录" button?
                3. What tabs/options are at the top of the dialog?
                Describe what the user needs to click to reach SMS login.
            """)

            # 尝试点"已有账号登录"
            clicked = await page.evaluate("""
                () => {
                    var all = document.querySelectorAll('span,div,button');
                    for (var i=0; i<all.length; i++) {
                        var t = (all[i].textContent||'').trim();
                        if ((t.includes('已有账号') || t.includes('短信') || t.includes('手机')) && all[i].offsetParent) {
                            all[i].click();
                            return t.slice(0,30);
                        }
                    }
                    return '';
                }
            """)
            if clicked:
                log(f"点击了: {clicked}")
                await page.wait_for_timeout(3000)
                r3 = await vision(page, "03_after_switch", """
                    After clicking, what changed?
                    1. Are there phone number input fields now?
                    2. Is there a "获取验证码" or "继续" button?
                    3. Is there a "同意并登录" button?
                """)

            # ═══ Step 5: 提交报告 ═══
            print(f"\n{'─'*40}\n📌 Step 5/5: 本轮测试完成")
            print(f"\n✅ 浏览器窗口保持打开，你可以查看当前状态。")
            print(f"📸 截图保存在: {SNAP_DIR}/")
            print(f"\n告诉我下一步方向，我继续。")

            # 保持浏览器打开
            await asyncio.sleep(9999)

        except Exception as e:
            log(f"❌ 异常: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(30)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
