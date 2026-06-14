#!/usr/bin/env python3
"""最后一轮：扫所有可见输入元素"""
import asyncio, os, json, sys
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

    all_inputs = await page.evaluate("""() => {
        var all = document.querySelectorAll('input, textarea, [contenteditable]');
        var result = [];
        for (var i = 0; i < all.length; i++) {
            var c = all[i];
            if (!c.offsetParent) continue;
            var ce = c.getAttribute('contenteditable');
            if (ce === 'false') continue;  // 跳过 contenteditable=false
            var r = c.getBoundingClientRect();
            result.push({
                tag: c.tagName,
                cls: (c.className||'').slice(0,35),
                rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
                ph: c.getAttribute('placeholder')||'',
                val: (c.value||c.textContent||'').slice(0,15),
            });
        }
        return result;
    }""")
    print(f'可见输入元素 ({len(all_inputs)}个):')
    for a in all_inputs:
        print(f'  {a["tag"]:6s} rect={a["rect"]} ph="{a["ph"]}" val="{a["val"]}" cls={a["cls"]}')

    await conn.browser.close()

asyncio.run(main())
