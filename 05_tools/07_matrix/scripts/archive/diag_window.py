#!/usr/bin/env python3
"""
窗口诊断工具 — 全面测试 Firefox 窗口控制各环节
"""
import asyncio, pickle, json, sys
from pathlib import Path

IDENTITY_DIR = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix" / "identities" / "douyin_camo01"
USER_DATA = str(IDENTITY_DIR / "user_data")
FP_PATH = IDENTITY_DIR / "fingerprint.pkl"

async def main():
    from camoufox.async_api import AsyncCamoufox

    fingerprint = None
    if FP_PATH.exists():
        with open(FP_PATH, "rb") as f:
            fingerprint = pickle.load(f)

    # 写 xulstore
    xul = IDENTITY_DIR / "user_data" / "xulstore.json"
    xul.write_text(json.dumps({
        "chrome://browser/content/browser.xhtml": {
            "main-window": {
                "screenX": "0", "screenY": "0",
                "width": "702", "height": "783", "sizemode": "normal"
            }
        }
    }, indent=2))

    async with AsyncCamoufox(
        persistent_context=True, user_data_dir=USER_DATA,
        headless=False, window=(702, 783),
        os="windows", fingerprint=fingerprint,
        i_know_what_im_doing=True, humanize=1.5,
        firefox_user_prefs={"dom.disable_window_move_resize": False},
        args=["--width=702", "--height=783"],
    ) as ctx:
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await asyncio.sleep(5)

        # T1: 基本信息
        i = await page.evaluate("""() => ({
            outerW: window.outerWidth, outerH: window.outerHeight,
            innerW: window.innerWidth, innerH: window.innerHeight,
            screenAW: screen.availWidth, screenAH: screen.availHeight,
            resizeToOK: typeof window.resizeTo === "function",
            moveToOK: typeof window.moveTo === "function"
        })""")
        print(f"[T1] 基本信息: outer={i['outerW']}x{i['outerH']} inner={i['innerW']}x{i['innerH']}")
        print(f"     screen.avail={i['screenAW']}x{i['screenAH']}")
        print(f"     resizeTo=功能正常={i['resizeToOK']} moveTo=功能正常={i['moveToOK']}")

        # T2: 执行 resizeTo + 立即检查
        r = await page.evaluate("""() => {
            let before = window.outerWidth + "x" + window.outerHeight;
            window.moveTo(0, 0);
            window.resizeTo(702, 783);
            let after = window.outerWidth + "x" + window.outerHeight;
            return {before, after};
        }""")
        print(f"[T2] resizeTo 前后: {r['before']} → {r['after']}")

        # T3: 延时 2s/5s/10s 后反复检查
        for sec in [2, 5, 10]:
            await asyncio.sleep(sec)
            sz = await page.evaluate("() => window.outerWidth + 'x' + window.outerHeight")
            print(f"[T3] +{sec}s后: {sz}")

        # T4: window.open 开新窗口
        r4 = await page.evaluate("""() => {
            let w = window.open("about:blank", "", "width=702,height=783,left=0,top=0");
            if (!w) return "blocked";
            return w.outerWidth + "x" + w.outerHeight;
        }""")
        print(f"[T4] window.open新窗: {r4}")

        # T5: 当前页面创建新 page 并调整
        page2 = await ctx.new_page()
        await page2.set_viewport_size({"width": 702, "height": 783})
        r5 = await page2.evaluate("() => window.innerWidth + 'x' + window.innerHeight")
        print(f"[T5] 新page的inner: {r5}")

        # T6: F11 切换测试
        await page.keyboard.press("F11")
        await asyncio.sleep(2)
        sz = await page.evaluate("() => window.outerWidth + 'x' + window.outerHeight")
        print(f"[T6] F11全屏后: {sz}")
        await page.keyboard.press("F11")
        await asyncio.sleep(2)
        sz = await page.evaluate("() => window.outerWidth + 'x' + window.outerHeight")
        print(f"[T6] F11恢复后: {sz}")

        # T7: 连续10次快速 resizeTo（暴力法）
        for i in range(10):
            await page.evaluate("window.resizeTo(702, 783)")
            await asyncio.sleep(0.3)
        sz = await page.evaluate("() => window.outerWidth + 'x' + window.outerHeight")
        print(f"[T7] 10次快速resizeTo后: {sz}")

        # T8: 读取 prefs.js 验证设置
        prefs_path = IDENTITY_DIR / "user_data" / "prefs.js"
        if prefs_path.exists():
            prefs = prefs_path.read_text()
            lines = [l for l in prefs.split("\n") if "disable_window_move_resize" in l.lower()]
            if lines:
                print(f"[T8] prefs.js中该选项: {lines[0][:80]}")

        print("\n诊断完成，窗口将保持 15 秒供你观察...")
        await asyncio.sleep(15)

asyncio.run(main())
