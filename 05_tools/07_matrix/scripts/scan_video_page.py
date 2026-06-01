#!/usr/bin/env python3
import asyncio, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(0,0))
    await conn.connect(); page = conn.page; await conn.init_anti_detection()
    await page.goto('https://www.douyin.com/video/7482384211811241268', timeout=30000)
    await asyncio.sleep(6)
    await page.keyboard.press('x'); await asyncio.sleep(2)
    
    info = await page.evaluate("""() => {
        var h = window.innerHeight; var w = window.innerWidth;
        var all = document.querySelectorAll('input, textarea, [contenteditable]');
        var r = [];
        for (var i = 0; i < all.length; i++) {
            var c = all[i]; if (!c.offsetParent) continue;
            var rc = c.getBoundingClientRect();
            r.push({tag:c.tagName, cls:(c.className||'').slice(0,30),
                    rect:[Math.round(rc.left),Math.round(rc.top),Math.round(rc.width),Math.round(rc.height)],
                    ph:c.getAttribute('placeholder')||'', ce:c.getAttribute('contenteditable')||''});
        }
        return {win:[w,h], inputs:r};
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    await conn.browser.close()

asyncio.run(main())
