#!/usr/bin/env python3
"""常驻扫描器：信号控制，不重启浏览器"""
import asyncio, os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

LOG = '/tmp/scanner.log'; SIG = '/tmp/scanner_cmd'; RPT = '/tmp/scanner_rpt'
def log(m):
    with open(LOG,'a') as f: f.write(f'[{time.strftime("%H:%M:%S")}] {m}\n')
    print(m, flush=True)
def rpt(d):
    with open(RPT,'w') as f: json.dump(d,f,ensure_ascii=False,indent=2)
    log(f'📄 报告已写入')

async def scan_deep(page):
    """深度扫描：所有浮层、弹窗、登录面板"""
    return await page.evaluate("""() => {
        var r = {url: location.href.slice(0,60)};
        // 所有 visible 的浮层/弹窗（z-index高、fixed定位、或class含overlay/modal/popup）
        var overlays = [...document.querySelectorAll('*')].filter(el => {
            if (!el.offsetParent) return false;
            var z = getComputedStyle(el).zIndex;
            var pos = getComputedStyle(el).position;
            return (parseInt(z) > 100 || pos === 'fixed') && el.children.length > 0;
        });
        r.overlayCount = overlays.length;
        // 找最上层的弹窗内容
        var topEls = overlays.slice(-5).map(el => {
            var r2 = el.getBoundingClientRect();
            var hasInput = !!el.querySelector('input');
            var btns = [...el.querySelectorAll('button')].map(b => b.textContent.trim().slice(0,15));
            var inputs = [...el.querySelectorAll('input')].map(i => ({ph:i.placeholder||'', cls:i.className.slice(0,30)}));
            return {
                cls: el.className.slice(0,40), tag: el.tagName,
                rect: [Math.round(r2.left), Math.round(r2.top), Math.round(r2.width), Math.round(r2.height)],
                btns: btns, inputs: inputs, hasInput: hasInput,
                html: el.innerHTML.replace(/\\s+/g,' ').slice(0,200),
            };
        });
        r.topElements = topEls;

        // 专门检测登录/验证码相关
        r.loginBtn = [...document.querySelectorAll('button, a, [class*="login"]')].filter(el => el.offsetParent && el.textContent.includes('登录')).map(e => ({t:e.textContent.trim().slice(0,20), cls:e.className.slice(0,30)}));
        r.oneClickBtn = [...document.querySelectorAll('button')].filter(b => b.offsetParent && b.textContent.includes('一键')).map(b => ({t:b.textContent.trim().slice(0,20), cls:b.className.slice(0,30), rect:Object.values(b.getBoundingClientRect()).map(Math.round)}));
        r.allBtns = [...document.querySelectorAll('button')].filter(b => b.offsetParent).slice(0,15).map(b => ({t:b.textContent.trim().slice(0,15), cls:b.className.slice(0,25)}));
        r.allInputs = [...document.querySelectorAll('input')].filter(i => i.offsetParent).slice(0,10).map(i => ({ph:i.placeholder||'', cls:i.className.slice(0,25)}));
        return r;
    }""")

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_02_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(0,0))
    await conn.connect(); page = conn.page; await conn.init_anti_detection()
    await page.goto('https://www.douyin.com/', timeout=30000, wait_until='domcontentloaded')
    await asyncio.sleep(6)
    log('🟢 浏览器就绪，等待信号 /tmp/scanner_cmd')

    while True:
        if os.path.exists(SIG):
            cmd = open(SIG).read().strip()
            os.remove(SIG)
            log(f'📡 收到: {cmd}')

            if cmd == 'scan':
                s = await scan_deep(page)
                rpt(s)
            elif cmd == 'click_login':
                await page.evaluate("""() => {
                    var all = document.querySelectorAll('button, a, [class*="login"]');
                    for (var i = 0; i < all.length; i++) {
                        if (all[i].textContent.includes('登录')) { all[i].click(); return; }
                    }
                }""")
                await asyncio.sleep(2)
                rpt(await scan_deep(page))
            elif cmd == 'click_onekey':
                clicked = await page.evaluate("""() => {
                    var els = document.querySelectorAll('span, div, a, button');
                    for (var i = 0; i < els.length; i++) {
                        if (els[i].textContent.trim() === '一键登录') { els[i].click(); return true; }
                    }
                    return false;
                }""")
                log(f'  ✅ 点击一键登录: {clicked}')
                await asyncio.sleep(4)
                rpt(await scan_deep(page))
            elif cmd == 'scan_sms':
                rpt(await scan_deep(page))
            elif cmd == 'exit':
                break
        await asyncio.sleep(0.3)

    await conn.browser.close()

asyncio.run(main())
