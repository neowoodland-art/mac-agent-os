#!/usr/bin/env python3
"""
calibrate_input.py — 配合对话的坐标校准

流程：
  1. 启动浏览器 → 进入视频
  2. 打开评论区
  3. 你点输入框 → 我读坐标
  4. 自动回测一次
"""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector
from playwright.async_api import async_playwright

LOG = '/tmp/calibrate.log'
def log(m):
    with open(LOG, 'a') as f: f.write(m + '\n')
    print(m, flush=True)

async def read_active(page):
    r = await page.evaluate("""() => {
        const ae = document.activeElement;
        if (!ae || ae === document.body) return {ok:false, reason:'body'};
        const r = ae.getBoundingClientRect();
        return {
            ok: true,
            tag: ae.tagName,
            cls: (ae.className||'').slice(0,40),
            ph: (ae.placeholder||''),
            contenteditable: !!ae.isContentEditable || (ae.getAttribute('contenteditable')==='true'),
            rect: {l:Math.round(r.left), t:Math.round(r.top), w:Math.round(r.width), h:Math.round(r.height)},
            center: {x:Math.round(r.left+r.width/2), y:Math.round(r.top+r.height/2)},
            fromRight: Math.round(window.innerWidth - r.left - r.width/2),
            fromBottom: Math.round(window.innerHeight - r.top - r.height/2),
            win: {w:window.innerWidth, h:window.innerHeight},
        };
    }""")
    return r

async def scan_comment_panel(page):
    """扫描评论区底部区域，找所有可能的输入元素"""
    r = await page.evaluate("""() => {
        // 所有可见的 input-like 元素
        const candidates = [...document.querySelectorAll('input, textarea, [contenteditable], [class*="editor"], [class*="input"]')]
            .filter(el => el.offsetParent !== null && el.getBoundingClientRect().width > 20);
        
        // 扫描底部区域（离底部<100px的所有可交互元素）
        const h = window.innerHeight;
        const bottomEls = [...document.querySelectorAll('*')].filter(el => {
            if (el.offsetParent === null) return false;
            const r = el.getBoundingClientRect();
            return r.bottom > h - 100 && r.top < h - 20 && r.width > 30 && r.height > 15;
        });
        
        const uniqueBottom = [...new Map(bottomEls.map(e => [(e.className||'')+e.tagName, {
            tag: e.tagName, cls: (e.className||'').slice(0,40),
            role: e.getAttribute('role')||'', ph: (e.placeholder||''),
            rect: Object.values(e.getBoundingClientRect()).map(Math.round),
            text: (e.textContent||'').slice(0,15).trim(),
        }])).values()].slice(0,15);
        
        return {
            inputCandidates: candidates.map(c => ({
                tag: c.tagName, cls: (c.className||'').slice(0,30),
                ph: (c.placeholder||''), rect: Object.values(c.getBoundingClientRect()).map(Math.round),
            })),
            bottomElements: uniqueBottom,
        };
    }""")
    return r

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    log(f"\n{'='*55}")
    log(f" 🎯 评论输入框校准 — 对话模式")
    log(f"{'='*55}")

    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()

    # ── 进入播放页 ──
    await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(3)
    card = page.locator('.discover-video-card-item').first
    await card.click(); await asyncio.sleep(1)
    await card.click(); await asyncio.sleep(4)
    log(f"✅ 播放页 (video={await page.evaluate('document.querySelectorAll(\"video\").length')})")

    # ── 打开评论区 ──
    await page.evaluate("""() => {
        const btn = document.querySelector('[data-e2e="video-comment-count"]')
                || document.querySelector('[data-e2e="feed-comment-icon"]');
        if (btn) btn.click();
    }""")
    await asyncio.sleep(2)
    log(f"✅ 评论区已打开")

    # 先扫一遍底部区域，看看输入框长什么样
    scan = await scan_comment_panel(page)
    log(f"\n📋 输入候选:")
    for c in scan['inputCandidates']:
        log(f"  {c['tag']:8s} cls={c['cls'][:30]:30s} ph=\"{c['ph']}\" rect={c['rect']}")
    log(f"\n📋 底部元素:")
    for e in scan['bottomElements']:
        log(f"  {e['tag']:8s} cls={e['cls'][:30]:30s} role={e['role']:15s} text=\"{e['text']}\" rect={e['rect']}")

    # 现在你来点输入框
    log(f' 👆 请用鼠标点一下评论输入框（让光标闪）')
    log(f'    然后在这里告诉我"点了"')
    log(f"{'─'*55}")

asyncio.run(main())
