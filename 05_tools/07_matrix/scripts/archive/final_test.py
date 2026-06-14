#!/usr/bin/env python3
"""最终测试：点击输入区域触发懒加载 → 等输入框出现 → fill → Alt+Enter"""
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

    # 扫底部所有可见元素，找到输入区域
    area = await page.evaluate("""() => {
        var h = window.innerHeight;
        var els = document.querySelectorAll('.douyin-player-controls-inner, .douyin-player-controls-left, [class*="input"], [class*="comment"]');
        for (var i = 0; i < els.length; i++) {
            var c = els[i];
            if (!c.offsetParent) continue;
            var r = c.getBoundingClientRect();
            if (r.bottom > h - 100 && r.width > 100) {
                return {tag: c.tagName, cls: c.className.slice(0,40),
                        x: Math.round(r.left+r.width*0.3), y: Math.round(r.top+r.height/2)};
            }
        }
        return null;
    }""")
    print(f'输入区域: {area}')

    if not area:
        print('❌ 没找到输入区域，尝试找底部最大的 DIV')
        # 回退：找底部最大的 DIV 的中心偏左位置
        area2 = await page.evaluate("""() => {
            var h = window.innerHeight;
            var all = document.querySelectorAll('div');
            var best = null, bestW = 0;
            for (var i = 0; i < all.length; i++) {
                var c = all[i];
                if (!c.offsetParent) continue;
                var r = c.getBoundingClientRect();
                if (r.bottom > h - 100 && r.width > bestW && r.width < h) {
                    bestW = r.width; best = c;
                }
            }
            if (!best) return null;
            var r = best.getBoundingClientRect();
            return {tag: best.tagName, cls: best.className.slice(0,40),
                    x: Math.round(r.left+r.width*0.3), y: Math.round(r.top+r.height/2)};
        }""")
        print(f'底部最大DIV: {area2}')
        area = area2

    if not area:
        print('❌ 彻底找不到输入区域')
        await conn.browser.close()
        return

    # 点击触发懒加载
    print(f'点击 ({area["x"]}, {area["y"]}) 触发懒加载...')
    await page.mouse.click(area['x'], area['y'])
    await asyncio.sleep(0.5)
    await page.mouse.click(area['x'], area['y'])
    await asyncio.sleep(1)

    # 现在找 input
    inp_info = await page.evaluate("""() => {
        var all = document.querySelectorAll('input, textarea, [contenteditable]');
        for (var i = 0; i < all.length; i++) {
            var c = all[i];
            if (!c.offsetParent) continue;
            var ce = c.getAttribute('contenteditable');
            if (ce === 'false') continue;
            var r = c.getBoundingClientRect();
            if (r.bottom > window.innerHeight - 90) {
                return {tag: c.tagName, cls: c.className.slice(0,30),
                        x: Math.round(r.left+r.width/2), y: Math.round(r.top+r.height/2),
                        w: Math.round(r.width), h: Math.round(r.height)};
            }
        }
        return null;
    }""")
    print(f'加载后输入框: {inp_info}')

    if not inp_info:
        print('❌ 懒加载后仍无输入框')
    else:
        # fill 文字
        if inp_info['tag'] in ('INPUT', 'TEXTAREA'):
            await page.keyboard.type('好内容', delay=40)
        else:
            await page.keyboard.type('好内容', delay=40)
        await asyncio.sleep(1)

        val = await page.evaluate('() => document.activeElement?.value || document.activeElement?.textContent || ""')
        print(f'输入值: "{val}"')

        if val:
            print('⌨️ Alt+Enter 发送...')
            await page.keyboard.press('Alt+Enter')
            await asyncio.sleep(3)

            has_v = await page.evaluate('() => !!document.querySelector("input[placeholder*=验证码]")')
            val2 = await page.evaluate('() => document.activeElement?.value || document.activeElement?.textContent || ""')
            print(f'验证码: {"✅" if has_v else "❌"}, 输入框: "{val2}"')

    await conn.browser.close()

asyncio.run(main())
