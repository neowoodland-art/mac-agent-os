#!/usr/bin/env python3
"""
browser_keepalive.py — 保持浏览器打开，等待坐标读取信号

流程：
  1. 启动 Camoufox → 进入视频 → 打开评论区
  2. 保持浏览器运行
  3. 检测 /tmp/calibrate.signal 文件
  4. 有信号 → 读 activeElement → 写 /tmp/input_coord.json → 删信号
  5. 继续等待下一个信号
"""
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

LOG = '/tmp/browser_keepalive.log'
def log(m):
    with open(LOG, 'a') as f: f.write(m + '\n')
    print(m, flush=True)

SIGNAL = '/tmp/calibrate.signal'
OUTPUT = '/tmp/input_coord.json'

async def read_active(page):
    return await page.evaluate("""() => {
        const ae = document.activeElement;
        if (!ae || ae === document.body || ae === document.documentElement)
            return {ok: false, reason: 'no active element'};
        const r = ae.getBoundingClientRect();
        return {
            ok: true,
            tag: ae.tagName,
            id: ae.id || '',
            cls: (ae.className || '').slice(0, 50),
            ph: (ae.placeholder || ''),
            role: ae.getAttribute('role') || '',
            contenteditable: ae.isContentEditable || ae.getAttribute('contenteditable'),
            hasFocus: document.activeElement === ae,
            rect: {
                left: Math.round(r.left),
                top: Math.round(r.top),
                width: Math.round(r.width),
                height: Math.round(r.height),
            },
            center: {
                x: Math.round(r.left + r.width / 2),
                y: Math.round(r.top + r.height / 2),
            },
            fromRight: Math.round(window.innerWidth - r.left - r.width/2),
            fromBottom: Math.round(window.innerHeight - r.top - r.height/2),
            winSize: {w: window.innerWidth, h: window.innerHeight},
        };
    }""")

async def scan_bottom(page):
    """扫描底部区域"""
    return await page.evaluate("""() => {
        const h = window.innerHeight;
        const els = [...document.querySelectorAll('*')].filter(el => {
            if (!el.offsetParent) return false;
            const r = el.getBoundingClientRect();
            return r.bottom > h - 120 && r.top < h - 20 && r.width > 30;
        });
        const seen = new Set();
        return [...els].filter(el => {
            const key = el.tagName + (el.className||'') + el.getAttribute('placeholder')||'';
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        }).slice(0, 20).map(el => ({
            t: el.tagName, c: (el.className||'').slice(0,35),
            ph: (el.placeholder||''), r: Object.values(el.getBoundingClientRect()).map(Math.round),
            txt: (el.textContent||'').slice(0,15),
        }));
    }""")

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')

    log(f"\n{'='*55}")
    log(f" 🦀 浏览器保持运行 — 等你点输入框")
    log(f"{'='*55}")

    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()

    # 进入播放页
    await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(4)
    card = page.locator('.discover-video-card-item').first
    if await card.count() > 0:
        await card.click(); await asyncio.sleep(1)
        await card.click(); await asyncio.sleep(4)
    log(f"✅ 播放页 (video={await page.evaluate('document.querySelectorAll(\"video\").length')})")

    # 先扫底部
    bottom = await scan_bottom(page)
    log(f"\n📋 底部元素:")
    for e in bottom:
        log(f"  {e['t']:8s} cls={e['c'][:30]:30s} ph=\"{e['ph']}\" rect={e['r']} txt=\"{e['txt']}\"")

    # 打开评论区
    await page.evaluate("""() => {
        const btn = document.querySelector('[data-e2e="video-comment-count"]')
                || document.querySelector('[data-e2e="feed-comment-icon"]');
        if (btn) btn.click();
    }""")
    await asyncio.sleep(2)
    log(f"\n✅ 评论区已打开")
    log(f' 👆 请用鼠标点评论输入框（让光标闪烁）')
    log(f'    点完后在这里说"点了"')
    log(f"{'─'*55}")

    # 保持运行，等待信号
    while True:
        if os.path.exists(SIGNAL):
            log(f"\n📡 收到信号，读取坐标...")
            try:
                info = await read_active(page)
                with open(OUTPUT, 'w') as f:
                    json.dump(info, f, ensure_ascii=False, indent=2)
                log(f"✅ 坐标已写入 {OUTPUT}")
                for k, v in info.items():
                    if k != 'ok':
                        log(f"  {k}: {json.dumps(v, ensure_ascii=False)}")
            except Exception as e:
                log(f"⚠️ 读取异常: {e}")
            os.remove(SIGNAL)
        await asyncio.sleep(1)

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\n👋 退出")
    except Exception as e:
        import traceback; traceback.print_exc()
