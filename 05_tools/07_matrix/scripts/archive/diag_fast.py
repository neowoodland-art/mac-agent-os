#!/usr/bin/env python3
"""快速诊断：点击视频卡片后页面有什么变化"""
import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()

    # 导航
    await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(6)

    # 先滚动画廊区
    await page.evaluate("""() => {
        const c = document.querySelector('[class*="feed"]') || 
                   document.querySelector('[class*="route-scroll"]') ||
                   document.querySelector('[class*="tab-content"]');
        if (c) c.scrollTop = 0;
        window.scrollTo(0, 0);
    }""")
    await asyncio.sleep(2)

    # 现在卡片应该可见了，点击
    card = page.locator('[data-e2e="alink-item"]').first
    await card.wait_for(state="visible", timeout=10000)
    await card.click()
    await asyncio.sleep(2)
    await card.click()
    await asyncio.sleep(5)

    # 诊断点击后的页面
    result = await page.evaluate("""() => {
        const url = location.href;
        const vc = document.querySelectorAll('video').length;
        const hasDigg = !!document.querySelector('[data-e2e="video-player-digg"]');
        const hasCollect = !!document.querySelector('[data-e2e="video-player-collect"]');
        const hasComment = !!document.querySelector('[data-e2e="feed-comment-icon"]');
        const hasDoubleLike = !!document.querySelector('[data-e2e="feed-active-video-double-like"]');
        const hasCard = !!document.querySelector('[data-e2e="alink-item"]');
        const nClass = document.querySelectorAll('*').length;

        // 所有 visible 带 video/player 关键词的元素
        const overlays = [...document.querySelectorAll('*')].filter(el => {
            const c = (el.className || '').toLowerCase();
            return el.offsetParent !== null && (c.includes('player') || c.includes('overlay') || c.includes('mask'));
        }).slice(0,10).map(el => ({
            tag: el.tagName,
            cls: (el.className || '').slice(0,40),
            w: Math.round(el.getBoundingClientRect().width),
            h: Math.round(el.getBoundingClientRect().height),
        }));

        return {url, vc, hasDigg, hasCollect, hasComment, hasDoubleLike, hasCard, nClass, overlays};
    }""")
    print(f'\n📊 点击卡片后:')
    for k, v in result.items():
        print(f'  {k}: {v}')

    print(f'\n✅ 完成，浏览器保持打开')
    while True: await asyncio.sleep(10)

asyncio.run(main())
