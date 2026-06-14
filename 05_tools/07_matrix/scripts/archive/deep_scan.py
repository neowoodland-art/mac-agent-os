#!/usr/bin/env python3
"""深度扫描：输入栏左侧的结构"""
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

    # 深度扫描左侧区域
    info = await page.evaluate("""() => {
        const left = document.querySelector('.douyin-player-controls-left');
        if (!left) return {error: 'no left'};
        
        // 递归扫所有子孙元素
        function deep(el, depth=0) {
            if (depth > 3) return null;
            const r = el.getBoundingClientRect();
            const result = {
                tag: el.tagName, cls: (el.className||'').slice(0,40),
                rect: [Math.round(r.left||0), Math.round(r.top||0), Math.round(r.width||0), Math.round(r.height||0)],
                ce: el.getAttribute('contenteditable')||'',
                role: el.getAttribute('role')||'',
                ph: el.getAttribute('placeholder')||'',
                tabIndex: el.getAttribute('tabindex')||'',
                e2e: el.getAttribute('data-e2e')||'',
                text: String(el.textContent||'').replace(/\\s+/g,' ').slice(0,20).trim(),
                children: [],
            };
            for (const child of el.children) {
                const sub = deep(child, depth+1);
                if (sub) result.children.push(sub);
            }
            return result;
        }
        return deep(left);
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=2))

    await conn.browser.close()

asyncio.run(main())
