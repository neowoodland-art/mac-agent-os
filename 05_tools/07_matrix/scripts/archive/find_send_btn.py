#!/usr/bin/env python3
"""查找输入框周围的发送按钮"""
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

    inp = page.locator('input.YEhxqQNi').first
    await inp.click()
    await asyncio.sleep(0.3)
    await inp.fill('好内容')
    await asyncio.sleep(2)

    # 检查输入框周围结构
    info = await page.evaluate("""() => {
        var inp = document.querySelector('input.YEhxqQNi');
        if (!inp) return null;
        var result = {};
        // input 自身
        var r = inp.getBoundingClientRect();
        result.input = { rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)] };
        // 父级
        var parent = inp.parentElement;
        if (parent) {
            var pr = parent.getBoundingClientRect();
            result.parent = { tag: parent.tagName, cls: parent.className.slice(0,40), rect: [Math.round(pr.left), Math.round(pr.top), Math.round(pr.width), Math.round(pr.height)], childCount: parent.children.length };
            // 父级的所有子元素
            var kids = [];
            for (var i = 0; i < parent.children.length; i++) {
                var c = parent.children[i];
                var cr = c.getBoundingClientRect();
                var isButton = c.tagName === 'BUTTON' || c.getAttribute('role') === 'button';
                kids.push({
                    index: i, tag: c.tagName, cls: c.className.slice(0,30),
                    rect: [Math.round(cr.left), Math.round(cr.top), Math.round(cr.width), Math.round(cr.height)],
                    text: (c.textContent||'').trim().slice(0,15),
                    isButton: isButton,
                    html: (c.innerHTML||'').slice(0,80),
                });
            }
            result.parent.children = kids;
        }
        // 再往上1层
        var gp = parent ? parent.parentElement : null;
        if (gp) {
            var gr = gp.getBoundingClientRect();
            result.grandparent = { tag: gp.tagName, cls: gp.className.slice(0,40), rect: [Math.round(gr.left), Math.round(gr.top), Math.round(gr.width), Math.round(gr.height)] };
        }
        return result;
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=2))

    await conn.browser.close()

asyncio.run(main())
