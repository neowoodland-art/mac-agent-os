#!/usr/bin/env python3
"""完整评论链测试：找底部输入 → fill → Alt+Enter"""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()

    # Step 1: 进视频
    await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(4)
    card = page.locator('.discover-video-card-item').first
    await card.click(force=True); await asyncio.sleep(1.5)
    await card.click(force=True); await asyncio.sleep(5)

    # Step 2: 打开评论区（先点视频确保焦点，再按 x）
    vid = page.locator('video').first
    if await vid.count() > 0:
        box = await vid.bounding_box()
        if box: await page.mouse.click(box['x']+box['width']//2, box['y']+box['height']//3)
    await asyncio.sleep(0.5)
    await page.keyboard.press('x')
    await asyncio.sleep(2)

    # 如果 x 没打开，点评论图标
    has_cl = await page.evaluate('() => !!document.querySelector("[data-e2e=comment-list]")')
    print(f'评论区: {has_cl}')
    if not has_cl:
        await page.evaluate("""() => {
            var btn = document.querySelector('[data-e2e="video-comment-count"]') ||
                       document.querySelector('[data-e2e="feed-comment-icon"]');
            if (btn) btn.click();
        }""")
        await asyncio.sleep(2)
        has_cl = await page.evaluate('() => !!document.querySelector("[data-e2e=comment-list]")')
        print(f'评论区(DOM): {has_cl}')

    # Step 3: 找底部输入框
    inp_info = await page.evaluate("""() => {
        var h = window.innerHeight;
        var all = document.querySelectorAll('input, textarea, [contenteditable=true], [class*=DraftEditor] [contenteditable]');
        for (var i = 0; i < all.length; i++) {
            var c = all[i];
            if (!c.offsetParent) continue;
            var r = c.getBoundingClientRect();
            if (r.bottom > h - 120) {
                return {tag: c.tagName, cls: (c.className||'').slice(0,35),
                        x: Math.round(r.left+r.width/2), y: Math.round(r.top+r.height/2),
                        w: Math.round(r.width), h: Math.round(r.height)};
            }
        }
        return null;
    }""")
    print(f'输入框: {inp_info}')

    if not inp_info:
        print('❌ 没找到输入框')
        await conn.browser.close()
        return

    # Step 4: 点击 + fill 文字
    await page.mouse.click(inp_info['x'], inp_info['y'])
    await asyncio.sleep(0.5)
    await page.mouse.click(inp_info['x'], inp_info['y'])
    await asyncio.sleep(0.5)

    if inp_info['tag'] in ('INPUT', 'TEXTAREA'):
        # 原生输入框
        focused = page.locator('input:focus, textarea:focus').first
        if await focused.count() > 0:
            await focused.fill('好内容')
        else:
            await page.keyboard.type('好内容', delay=50)
    else:
        await page.keyboard.type('好内容', delay=50)

    await asyncio.sleep(1)

    val = await page.evaluate('() => document.activeElement?.value || document.activeElement?.textContent || ""')
    print(f'输入值: "{val}"')

    if val:
        # Step 5: Alt+Enter 发送！
        print('⌨️ Alt+Enter 发送...')
        await page.keyboard.press('Alt+Enter')
        await asyncio.sleep(3)

        has_v = await page.evaluate('() => !!document.querySelector("input[placeholder*=验证码]")')
        val2 = await page.evaluate('() => document.activeElement?.value || document.activeElement?.textContent || ""')
        print(f'验证码: {"✅" if has_v else "❌"}, 输入框: "{val2}"')

        if has_v:
            print('🎉 完整链路跑通！评论发送 → 短信验证码')
        elif val2 == '' or val2 != val:
            print('✅ 发送成功，输入框已清空/变化')
        else:
            print('ℹ️ 输入框内容没变，可能未发送')
    else:
        print('❌ 文字输入失败')

    await conn.browser.close()

asyncio.run(main())
