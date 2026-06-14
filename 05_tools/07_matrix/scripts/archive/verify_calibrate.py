#!/usr/bin/env python3
"""
verify_calibrate.py — 用校准过的坐标验证自动聚焦

发信号给 browser_keepalive 执行验证流程：
  1. 取消所有焦点
  2. 用坐标 (479, 687) 双击
  3. 检查 activeElement 是否为编辑器
"""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

LOG = '/tmp/verify_calibrate.log'
def log(m):
    with open(LOG, 'a') as f: f.write(m + '\n')
    print(m, flush=True)

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    log(f"\n{'='*55}")
    log(f" 🔄 坐标验证：自动聚焦测试")
    log(f"{'='*55}")

    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()

    # 导航到视频
    await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(3)
    card = page.locator('.discover-video-card-item').first
    if await card.count() > 0:
        await card.click(); await asyncio.sleep(1)
        await card.click(); await asyncio.sleep(4)
    log(f"✅ 播放页")

    # 打开评论区
    await page.evaluate("""() => {
        const btn = document.querySelector('[data-e2e="video-comment-count"]')
                || document.querySelector('[data-e2e="feed-comment-icon"]');
        if (btn) btn.click();
    }""")
    await asyncio.sleep(2)
    log(f"✅ 评论区已打开")

    # 先取消焦点（点左上角空白）
    await page.mouse.click(10, 10)
    await asyncio.sleep(0.5)
    before = await page.evaluate("() => ({tag: document.activeElement?.tagName, cls: (document.activeElement?.className||'').slice(0,40)})")
    log(f"  取消焦点后: {before}")

    # 用校准坐标点击
    x, y = 479, 687
    log(f"\n  🖱️ 双击 ({x}, {y})...")
    await page.mouse.move(x, y, steps=8)
    await asyncio.sleep(0.3)
    await page.mouse.click(x, y)
    await asyncio.sleep(0.5)
    await page.mouse.click(x, y)  # 连点两下
    await asyncio.sleep(0.8)

    # 检查 activeElement
    ae = await page.evaluate("""() => {
        const ae = document.activeElement;
        if (!ae) return {ok: false, reason: 'no activeElement'};
        const r = ae.getBoundingClientRect();
        return {
            ok: true,
            tag: ae.tagName,
            cls: (ae.className||'').slice(0,40),
            role: ae.getAttribute('role')||'',
            contenteditable: ae.isContentEditable,
            placeholder: ae.placeholder||'',
            center: {x: Math.round(r.left+r.width/2), y: Math.round(r.top+r.height/2)},
            hasText: (ae.textContent||ae.value||'').length > 0,
        };
    }""")
    log(f"\n📊 点击后 activeElement:")
    for k, v in ae.items():
        log(f"  {k}: {v}")

    if ae.get('ok') and ae.get('contenteditable'):
        log(f"\n✅ 验证通过！坐标 (479, 687) 成功聚焦编辑器")
    else:
        log(f"\n⚠️ 验证未完全通过")

    # 保持浏览器打开
    log(f"\n{'='*55}")
    log(f" 浏览器保持打开，按 Ctrl+C 退出")
    while True: await asyncio.sleep(10)

asyncio.run(main())
