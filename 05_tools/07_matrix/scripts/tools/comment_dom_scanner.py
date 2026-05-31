"""
comment_dom_scanner.py — 扫描评论区DOM结构
"""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'matrix_modules'))

async def main():
    from cdp_connector import CDPConnector

    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    conn = CDPConnector(browser_type='camoufox', identity_dir=ID_DIR,
                        headless=False, window=(702,783), window_position=(652,0))
    print('🦊 启动...')
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()
    await page.goto('https://www.douyin.com/', timeout=15000)
    await asyncio.sleep(3)

    print('\n📌 手动进入播放页，然后回车继续...')
    input()

    # 按X打开评论区
    await page.keyboard.press('KeyX')
    print('\n⌨️ KeyX 打开了评论区')
    await asyncio.sleep(2)

    # 扫描所有元素的class，找包含comment的
    classes = await page.evaluate("""() => {
        const all = document.querySelectorAll('*');
        const commentRelated = [...all].filter(el => {
            const c = (el.className || '').toLowerCase();
            const t = (el.tagName || '');
            return c.includes('comment') || c.includes('chat') || c.includes('reply') || c.includes('input');
        });
        return commentRelated.map(el => ({
            tag: el.tagName,
            cls: (el.className || '').slice(0,80),
            visible: el.offsetParent !== null,
            rect: Object.values(el.getBoundingClientRect()).map(Math.round),
            text: (el.textContent || '').slice(0,30)
        }));
    }""")
    print(f'\n📊 找到 {len(classes)} 个评论相关元素:')
    for c in classes:
        print(f'  {c["tag"]:8s} cls={c["cls"][:40]:40s} vis={c["visible"]} rect={c["rect"]} \"{c["text"]}\"')

    # 保存到文件
    out = '/tmp/comment_dom_scan.json'
    with open(out, 'w') as f:
        json.dump(classes, f, ensure_ascii=False, indent=2)
    print(f'\n💾 已保存到 {out}')

    print('\n✅ 扫描完成，浏览器保持打开')
    print('按 Ctrl+C 退出')

    while True:
        await asyncio.sleep(10)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print('\n👋 退出')
