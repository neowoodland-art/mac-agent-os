#!/usr/bin/env python3
"""快速分析抖音首页DOM结构"""
import asyncio, os, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_camo01')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page

    await page.goto('https://www.douyin.com/', timeout=25000, wait_until='domcontentloaded')
    await asyncio.sleep(8)  # 等页面完全加载

    url = page.url
    print(f"\n📍 URL: {url}")

    # 检查视频链接
    info = await page.evaluate("""() => ({
        videoCount: document.querySelectorAll('video').length,
        linksWithVideo: [...document.querySelectorAll('a')]
            .filter(a => (a.href || '').includes('/video/'))
            .map(a => ({text: (a.textContent||'').slice(0,20), href: (a.href||'').slice(0,60)})),
        cardSelectors: [
            '.discover-video-card-item',
            '[data-e2e="alink-item"]',
            '[class*="card"]',
        ].map(s => ({sel: s, count: document.querySelectorAll(s).length})),
        dataE2e: [...document.querySelectorAll('[data-e2e]')]
            .map(el => el.getAttribute('data-e2e'))
            .filter(Boolean)
            .slice(0, 30),
        title: document.title,
        bodyFirstClass: (document.body.className || '').slice(0, 80),
    })""")
    print(f"\n📊 页面分析:")
    print(f"  video元素: {info['videoCount']}")
    print(f"  视频链接: {json.dumps(info['linksWithVideo'], ensure_ascii=False, indent=4)}")
    print(f"  卡片选择器匹配: {json.dumps(info['cardSelectors'], ensure_ascii=False, indent=4)}")
    print(f"  data-e2e (前30): {json.dumps(info['dataE2e'], ensure_ascii=False, indent=4)}")
    print(f"  标题: {info['title']}")
    print(f"  body class: {info['bodyFirstClass']}")

    print(f"\n⏸️  按回车查看截图路径...")
    input()

    await page.screenshot(path='/tmp/douyin_jingxuan.png')
    print(f"📸 截图: /tmp/douyin_jingxuan.png")

    print(f"\n✅ 完成，浏览器保持打开")
    while True: await asyncio.sleep(10)

asyncio.run(main())
