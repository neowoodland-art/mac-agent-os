#!/usr/bin/env python3
"""快速分析抖音首页DOM结构（使用 Playwright Chromium，不依赖 Camoufox）"""
import asyncio, json, sys
sys.path.insert(0, '/Users/5kecheng/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts')
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 702, "height": 783})
        await page.goto('https://www.douyin.com/', timeout=30000, wait_until='domcontentloaded')
        await asyncio.sleep(10)  # 等JS渲染

        url = page.url
        print(f"\n📍 URL: {url}")

        info = await page.evaluate("""() => ({
            videoCount: document.querySelectorAll('video').length,
            videoLinks: [...document.querySelectorAll('a')]
                .filter(a => (a.href || '').includes('/video/'))
                .map(a => ({text: (a.textContent||'').slice(0,30), href: (a.href||'').slice(0,80)})),
            selectors: [
                {sel: '.discover-video-card-item', count: document.querySelectorAll('.discover-video-card-item').length},
                {sel: '[data-e2e="alink-item"]', count: document.querySelectorAll('[data-e2e="alink-item"]').length},
                {sel: '[class*="card"]', count: document.querySelectorAll('[class*="card"]').length},
                {sel: '[class*="video-card"]', count: document.querySelectorAll('[class*="video-card"]').length},
                {sel: '[class*="feed"]', count: document.querySelectorAll('[class*="feed"]').length},
            ],
            dataE2e: [...document.querySelectorAll('[data-e2e]')].map(e => e.getAttribute('data-e2e')).filter(Boolean).slice(0,40),
            title: document.title,
            bodyHTML: document.body.innerHTML.slice(0, 1000),
        })""")
        
        print(f"\n📊 页面分析:")
        print(f"  URL: {url}")
        print(f"  video: {info['videoCount']}")
        print(f"  标题: {info['title']}")
        print(f"\n  video链接:")
        for l in info['videoLinks']:
            print(f"    {l['text'][:20]:20s} → {l['href'][:60]}")
        print(f"\n  选择器匹配:")
        for s in info['selectors']:
            print(f"    {s['sel'][:35]:35s} × {s['count']}")
        print(f"\n  data-e2e (前40):")
        for e in info['dataE2e']:
            print(f"    {e}")
        print(f"\n  body HTML (前500): {info['bodyHTML'][:500]}")

        await page.screenshot(path='/tmp/douyin_chrome.png', full_page=False)
        print(f"\n📸 截图: /tmp/douyin_chrome.png")

        print(f"\n✅ 完成，浏览器保持打开")
        while True: await asyncio.sleep(10)

asyncio.run(main())
