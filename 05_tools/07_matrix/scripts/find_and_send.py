#!/usr/bin/env python3
"""鲁棒方案：扫底部找输入框 → fill → Enter"""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

async def find_bottom_input(page):
    """在页面底部100px内找任何输入元素"""
    return await page.evaluate("""() => {
        var h = window.innerHeight;
        var candidates = document.querySelectorAll('input, textarea, [contenteditable="true"]');
        for (var i = 0; i < candidates.length; i++) {
            var c = candidates[i];
            if (!c.offsetParent) continue;
            var r = c.getBoundingClientRect();
            if (r.bottom > h - 120 && r.top > h - 120) {
                return {
                    tag: c.tagName,
                    cls: (c.className || '').slice(0,40),
                    x: Math.round(r.left + r.width/2),
                    y: Math.round(r.top + r.height/2),
                    w: Math.round(r.width),
                    h: Math.round(r.height),
                };
            }
        }
        return null;
    }""")

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

    # 验证评论区是否打开
    has_cl = await page.evaluate('() => !!document.querySelector("[data-e2e=comment-list]")')
    print(f'评论区打开: {has_cl}')
    if not has_cl:
        print('评论区未打开，尝试点评论图标')
        await page.evaluate("""() => {
            var btn = document.querySelector('[data-e2e="video-comment-count"]') || 
                       document.querySelector('[data-e2e="feed-comment-icon"]');
            if (btn) btn.click();
        }""")
        await asyncio.sleep(2)

    # 扫底部找输入框
    info = await find_bottom_input(page)
    print(f'底部输入框: {info}')
    if not info:
        # 没有原生输入元素 → 可能是 Draft.js
        print('没有原生输入，检查 contenteditable...')
        ce = await page.evaluate("""() => {
            var h = window.innerHeight;
            var all = document.querySelectorAll('[contenteditable]');
            for (var i = 0; i < all.length; i++) {
                var c = all[i];
                if (!c.offsetParent) continue;
                var r = c.getBoundingClientRect();
                if (r.bottom > h - 120) {
                    return {
                        tag: c.tagName, cls: (c.className||'').slice(0,40),
                        x: Math.round(r.left+r.width/2), y: Math.round(r.top+r.height/2)
                    };
                }
            }
            return null;
        }""")
        print(f'contenteditable: {ce}')
        if ce: info = ce

    if not info:
        print('❌ 底部没有任何输入元素')
        await conn.browser.close()
        return

    # 点击 + fill
    x, y = info['x'], info['y']
    print(f'点击 ({x}, {y})')
    await page.mouse.click(x, y)
    await asyncio.sleep(0.3)
    await page.mouse.click(x, y)
    await asyncio.sleep(0.3)

    ae = await page.evaluate('() => document.activeElement?.tagName || "none"')
    print(f'activeElement: {ae}')

    if info['tag'] in ('INPUT', 'TEXTAREA'):
        # 原生输入框：直接用 fill
        vp = page.locator('input, textarea').filter(has=page.locator(':focus')).first
        cc = await vp.count()
        if cc > 0:
            await vp.fill('好内容')
        else:
            # fallback: 用 activeElement
            await page.evaluate('() => { var e = document.activeElement; if (e) e.value = "好内容"; }')
        await asyncio.sleep(1)
        val = await page.evaluate('() => document.activeElement?.value || ""')
        print(f'输入值: "{val}"')
        
        if val:
            print('按 Enter...')
            await page.keyboard.press('Enter')
            await asyncio.sleep(3)
            
            has_v = await page.evaluate('() => !!document.querySelector("input[placeholder*=验证码]")')
            val2 = await page.evaluate('() => document.activeElement?.value || ""')
            print(f'验证码: {"✅" if has_v else "❌"}, 输入框: "{val2}"')
    else:
        # contenteditable: 用 keyboard.type
        print('contenteditable 编辑器，用 keyboard.type')
        await page.keyboard.type('好内容', delay=50)
        await asyncio.sleep(1)
        txt = await page.evaluate('() => document.activeElement?.textContent || ""')
        print(f'输入内容: "{txt}"')

    await conn.browser.close()

asyncio.run(main())
