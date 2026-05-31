#!/usr/bin/env python3
"""
搜索 → 打开第2个结果 → 连续5个视频点赞 (Camoufox 桌面版)
用法: /Users/5kecheng/.workbuddy/binaries/python/envs/default/bin/python3 scripts/search_like5.py
"""

import asyncio, json, sys, time
from pathlib import Path
from urllib.parse import quote
from camoufox.async_api import AsyncCamoufox

TOOL_DIR = Path(__file__).parent.parent
LOCAL_ROOT = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix"
COOKIE_FILE = LOCAL_ROOT / "data" / "cookies" / "douyin_camo01_cookies.json"
SEARCH_KEYWORD = "苏州肛泰"
LIKE_COUNT = 5

async def main():
    print(f"\n{'='*55}")
    print(f" 🔥 抖音搜索点赞测试 (桌面版)")
    print(f"{'='*55}")
    print(f"   搜索:    {SEARCH_KEYWORD}")
    print(f"   方法:    直接导航到搜索页(桌面视口)")
    print(f"   打开:    第2个搜索结果")
    print(f"   点赞:    连续 {LIKE_COUNT} 个视频")
    print()

    # ── 启动 Camoufox (桌面视口 1024x768) ──
    print(f"🦊 启动 Camoufox (桌面视口 1024x768)...")
    cf = AsyncCamoufox(
        headless=False,
        window=(1024, 768),
        os='windows',
        fonts=['STHeiti', 'Heiti SC', 'PingFang SC', 'Noto Sans CJK SC'],
        humanize=1.5,
    )
    browser = await cf.start()
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = context.pages[0] if context.pages else await context.new_page()
    print("✅ Camoufox 就绪")

    # ── Cookie 注入 ──
    if COOKIE_FILE.exists():
        cookies = json.loads(COOKIE_FILE.read_text())
        for c in cookies:
            try:
                await context.add_cookies([{
                    "name": c["name"], "value": c["value"],
                    "domain": c["domain"], "path": c.get("path", "/"),
                    "httpOnly": c.get("httpOnly", False),
                    "secure": c.get("secure", False),
                    "sameSite": c.get("sameSite", "Lax"),
                }])
            except:
                pass
        douyin_cookies = [c for c in cookies if 'douyin' in c.get('domain', '')]
        print(f"  ✅ Cookie 已注入 ({len(douyin_cookies)}个抖音cookie)")
    else:
        print("  ❌ Cookie 文件不存在!")
        await browser.close()
        return

    # ── 桌面版反检测 ──
    await page.set_viewport_size({"width": 1024, "height": 768})
    await page.evaluate("""() => {
        Object.defineProperty(navigator, 'userAgent', {
            get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        });
    }""")
    print("  ✅ 反检测已就绪 (桌面 1024x768 + Windows UA)")

    # ── 直接导航到搜索页 ──
    search_url = f"https://www.douyin.com/search/{quote(SEARCH_KEYWORD)}?type=video"
    print(f"\n  📍 直接导航到搜索页...")
    print(f"     URL: {search_url}")
    await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
    await asyncio.sleep(5)
    print(f"  当前URL: {page.url[:100]}")

    # 截图供分析
    await page.screenshot(path=str(LOCAL_ROOT / "screenshots" / "search_page.png"))
    print("  📸 截图已保存: screenshots/search_page.png")

    # ── 检查登录状态 ──
    has_avatar = await page.query_selector('[class*="avatar"], [class*="Avatar"], [class*="user-info"]')
    print(f"  {'✅ 已登录' if has_avatar else '⚠️ 可能未登录'}")

    # ── 等待搜索结果加载 ──
    print(f"\n  ⏳ 等待搜索结果加载...")
    for wait_sec in range(15):
        video_links = await page.evaluate("""() => {
            const all = document.querySelectorAll('a');
            const videos = new Set();
            for (const a of all) {
                const href = a.href || '';
                if (href.includes('/video/')) videos.add(href);
            }
            return [...videos];
        }""")
        if len(video_links) >= 5:
            print(f"  第 {wait_sec+1}s: 找到 {len(video_links)} 个视频链接 ✅")
            break
        await asyncio.sleep(1)
    else:
        print(f"  等待超时，最终找到 {len(video_links)} 个视频链接")

    # 打印链接
    for i, link in enumerate(video_links[:10]):
        print(f"    [{i+1}] {link[:70]}...")

    if len(video_links) < 2:
        print("\n  ❌ 搜索结果不足2个，截图保存中，请查看 screenshots/search_page.png")
        print("     可能原因: 视口大小/反检测指纹需要调整，或搜索词无结果")
        await asyncio.sleep(5)
        await browser.close()
        return

    target_idx = 1  # 第2个 (0-indexed)

    # ── 打开第2个视频 ──
    print(f"\n  📍 打开第 {target_idx+1} 个视频...")
    await page.goto(video_links[target_idx], timeout=30000, wait_until="domcontentloaded")
    await asyncio.sleep(4)
    print(f"  当前视频URL: {page.url[:80]}")

    # ── 连续点赞 ──
    print(f"\n{'='*55}")
    print(f" 👍 开始连续点赞 {LIKE_COUNT} 个视频")
    print(f"{'='*55}")
    
    liked = 0
    for i in range(LIKE_COUNT):
        if i > 0:
            print(f"\n  ⬇️ 翻到第 {i+1} 个视频 (ArrowDown)...")
            await page.evaluate("() => window.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown'}))")
            await asyncio.sleep(3)
        
        print(f"  👍 点赞第 {i+1} 个视频...")
        await asyncio.sleep(2)
        
        result = await page.evaluate("""() => {
            const selectors = [
                '[data-e2e="feed-active-video-double-like"]',
                '[data-e2e="like-count"]', 
                '[class*="digg"]',
                '[class*="like"] svg',
                'span[class*="digg"]',
            ];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el) {
                    el.click();
                    return '👍 clicked: ' + sel;
                }
            }
            return '- no like button found';
        }""")
        
        if 'clicked' in result:
            liked += 1
            print(f"    → {result}")
        else:
            print(f"    → {result}")
        
        await asyncio.sleep(1.5)
    
    print(f"\n{'='*55}")
    print(f" ✅ 测试完成")
    print(f"   搜索: {SEARCH_KEYWORD}")
    print(f"   点赞: {liked}/{LIKE_COUNT} 成功")
    print(f"{'='*55}")
    
    print("\n⏳ 浏览器保持30秒方便查看，可手动关闭")
    await asyncio.sleep(30)
    await browser.close()
    print("👋 浏览器已关闭")

if __name__ == "__main__":
    asyncio.run(main())
