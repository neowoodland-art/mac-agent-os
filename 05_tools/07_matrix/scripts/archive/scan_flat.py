#!/usr/bin/env python3
"""扫描输入栏左侧——平铺所有子元素"""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()
    await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(4)
    card = page.locator('.discover-video-card-item').first
    await card.click(force=True); await asyncio.sleep(1)
    await card.click(force=True); await asyncio.sleep(4)
    await page.keyboard.press('x'); await asyncio.sleep(2)

    # 平铺扫所有底部可见元素（不递归）
    info = await page.evaluate("""() => {
        const bottom = [];
        const h = window.innerHeight;
        const all = document.querySelectorAll('*');
        for (const el of all) {
            if (!el.offsetParent) continue;
            const r = el.getBoundingClientRect();
            if (r.bottom > h - 90 && r.top < h - 5 && r.width > 10 && r.height > 5) {
                // 只取叶节点（没有可见子元素的）
                let hasVisibleChild = false;
                for (const c of el.children) {
                    if (c.offsetParent) { hasVisibleChild = true; break; }
                }
                if (!hasVisibleChild || el.children.length === 0) {
                    bottom.push({
                        t: el.tagName,
                        cls: (el.getAttribute('class') || '').slice(0,35),
                        r: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
                        ce: el.getAttribute('contenteditable') || '',
                        ph: el.getAttribute('placeholder') || '',
                        txt: (el.textContent || '').replace(/\\s+/g,' ').slice(0,15).trim(),
                    });
                }
            }
        }
        return bottom;
    }""")
    print(f'\n底部叶节点 ({len(info)}个):')
    for e in info:
        print(f'  {e[\"t\"]:6s} cls={e[\"cls\"]:30s} rect={e[\"r\"]} ce={e[\"ce\"]} ph=\"{e[\"ph\"]}\" txt=\"{e[\"txt\"]}\"')

    await conn.browser.close()

asyncio.run(main())
