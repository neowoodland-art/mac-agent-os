#!/usr/bin/env python3
"""精确测试：controls-left input + Enter 发送"""
import asyncio, os, sys
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

    inp = page.locator('.douyin-player-controls-left input').first
    cc = await inp.count()
    print(f'controls-left input: {cc}')
    if cc == 0:
        print('❌ 未找到输入框')
        await conn.browser.close()
        return

    box = await inp.bounding_box()
    print(f'输入框: x={box["x"]:.0f} y={box["y"]:.0f} w={box["width"]:.0f} h={box["height"]:.0f}')

    await inp.click()
    await asyncio.sleep(0.3)
    await inp.fill('好内容')
    await asyncio.sleep(1)
    print(f'输入值: "{await inp.input_value()}"')

    # Enter 发送
    print('按 Enter...')
    await inp.press('Enter')
    await asyncio.sleep(3)

    has_v = await page.evaluate('() => !!document.querySelector("input[placeholder*=验证码]")')
    val2 = await inp.input_value()
    print(f'验证码: {"✅" if has_v else "❌"}, 输入框: "{val2}"')
    
    if not has_v and val2 == '':
        print('✅ 发送成功！输入框已清空')
    elif has_v:
        print('📱 触发了验证码')
    else:
        print('ℹ️ 未触发验证码，输入框仍有内容')
    
    await conn.browser.close()

asyncio.run(main())
