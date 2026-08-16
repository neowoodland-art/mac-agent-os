#!/usr/bin/env python3
"""chrome_hide.py — 把 9222 采集 Chrome 的窗口移到屏幕外（CDP）

供 chrome_debug.sh 启动后调用。通过 Chrome DevTools Protocol 操作
9222 实例自己的窗口，绝不会影响用户日常 Chrome。

用法: python3 chrome_hide.py
"""
import asyncio
import sys

OFFSCREEN = {"left": 10000, "top": 10000, "width": 900, "height": 600, "windowState": "normal"}


async def main() -> int:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[chrome_hide] playwright 未安装，跳过窗口隐藏", file=sys.stderr)
        return 0
    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    except Exception as e:
        print(f"[chrome_hide] CDP 连接失败: {e}", file=sys.stderr)
        await pw.stop()
        return 1
    try:
        cdp = await browser.new_browser_cdp_session()
        targets = await cdp.send("Target.getTargets")
        moved = 0
        for t in targets.get("targetInfos", []):
            if t.get("type") != "page":
                continue
            try:
                win = await cdp.send("Browser.getWindowForTarget", {"targetId": t["targetId"]})
                wid = win.get("windowId")
                if wid:
                    await cdp.send("Browser.setWindowBounds", {"windowId": wid, "bounds": OFFSCREEN})
                    moved += 1
            except Exception as e:
                print(f"[chrome_hide] 窗口 {t.get('targetId', '')} 处理失败: {e}", file=sys.stderr)
        print(f"[chrome_hide] 已将 {moved} 个窗口移到屏幕外")
    finally:
        try:
            await browser.close()
        except Exception:
            pass
        await pw.stop()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
