#!/usr/bin/env python3
"""互动测试：你点输入框 → 我读坐标 → fill → Alt+Enter"""
import asyncio, os, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()

    # Step 0-1: 进视频
    await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(4)
    card = page.locator('.discover-video-card-item').first
    await card.click(force=True); await asyncio.sleep(1)
    await card.click(force=True); await asyncio.sleep(4)

    # Step 2: 开评论
    await page.keyboard.press('x')
    await asyncio.sleep(2)

    print('='*50)
    print('请用鼠标点一下输入框（让光标闪烁）')
    print('然后在这里说  "点了"  ')
    print('='*50)

    # 等信号文件
    while not os.path.exists('/tmp/user_clicked'):
        await asyncio.sleep(0.5)
    os.remove('/tmp/user_clicked')

    # 读激活元素
    info = await page.evaluate("""() => {
        var ae = document.activeElement;
        if (!ae) return {ok:false};
        var r = ae.getBoundingClientRect();
        return {
            ok:true, tag:ae.tagName, cls:(ae.className||'').slice(0,40),
            center:{x:Math.round(r.left+r.width/2), y:Math.round(r.top+r.height/2)},
            rect:{l:Math.round(r.left), t:Math.round(r.top), w:Math.round(r.width), h:Math.round(r.height)},
            fromRight: Math.round(window.innerWidth - r.left - r.width/2),
            fromBottom: Math.round(window.innerHeight - r.top - r.height/2),
            contenteditable: ae.isContentEditable,
            textContent: (ae.textContent||'').slice(0,15),
        };
    }""")
    print(f'\n📊 激活元素: {json.dumps(info, ensure_ascii=False)}')

    if not info.get('ok'):
        print('❌ 未激活任何元素')
        await conn.browser.close()
        return

    # 如果激活了编辑器，用 keyboard.type 打字
    cx, cy = info['center']['x'], info['center']['y']
    print(f'\n🎯 编辑器坐标: ({cx}, {cy})')
    print(f'   窗口 702×783 → screen ({652+cx}, {cy})')
    print(f'   离右边缘: {info["fromRight"]}px  离底边缘: {info["fromBottom"]}px')

    # keyboard.type 打字（Draft.js 已激活）
    print('\n⌨️ 输入 "好内容"...')
    await page.keyboard.type('好内容', delay=50)
    await asyncio.sleep(2)

    txt = await page.evaluate('() => document.activeElement?.textContent || ""')
    print(f'  编辑器内容: "{txt}"')

    if txt:
        print('\n⌨️ Alt+Enter 发送...')
        await page.keyboard.press('Alt+Enter')
        await asyncio.sleep(3)

        has_v = await page.evaluate('() => !!document.querySelector("input[placeholder*=验证码]")')
        print(f'  验证码: {"✅" if has_v else "❌"}')

        if has_v:
            print('\n🎉 完整链路跑通！评论发送 → 短信验证码')
        else:
            # 检查输入框是否清空
            txt2 = await page.evaluate('() => document.activeElement?.textContent || ""')
            print(f'  发送后编辑器: "{txt2}"')
    else:
        print('❌ 文字输入失败')

    # 保持浏览器打开
    print('\n✅ 测试完成，浏览器保持打开')
    while True: await asyncio.sleep(10)

asyncio.run(main())
