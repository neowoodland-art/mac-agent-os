#!/usr/bin/env python3
"""扫码登录/SMS验证弹窗"""
import asyncio, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

LOG = '/tmp/scan_login.log'
SIG = '/tmp/scan_go'
def log(m):
    with open(LOG,'a') as f: f.write(m+'\n')
    print(m, flush=True)

async def scan(page, label):
    s = await page.evaluate("""() => {
        var r = {url: location.href.slice(0,60), title: document.title};
        // 所有可见按钮
        r.buttons = [...document.querySelectorAll('button')].filter(b=>b.offsetParent).slice(0,10).map(b=>({t:b.textContent.trim().slice(0,20), cls:b.className.slice(0,30)}));
        // 所有input
        r.inputs = [...document.querySelectorAll('input')].filter(i=>i.offsetParent).slice(0,10).map(i=>({ph:i.placeholder||'', cls:i.className.slice(0,30), type:i.type||''}));
        // 验证码相关
        r.verifyPanel = !!document.querySelector('[class*="verify"i]');
        r.verifyInput = !!document.querySelector('input[placeholder*="验证码"i]');
        // 登录面板
        r.loginPanel = !!document.querySelector('[class*="login"i]');
        r.oneClickBtn = [...document.querySelectorAll('button')].some(b => b.textContent.includes('一键登录'));
        // SMS相关
        r.smsPanel = !!document.querySelector('[class*="sms"i],[class*="second-verify"i]');
        // 页面正文预览
        r.body = (document.body.innerText||'').replace(/\\s+/g,' ').slice(0,200);
        return r;
    }""")
    log(f'\n📸 [{label}] 扫描结果:')
    log(f'  URL: {s["url"]}')
    log(f'  验证码input: {s["verifyInput"]}  验证码面板: {s["verifyPanel"]}')
    log(f'  登录面板: {s["loginPanel"]}  一键登录: {s["oneClickBtn"]}')
    log(f'  SMS面板: {s["smsPanel"]}')
    log(f'  buttons: {json.dumps(s["buttons"], ensure_ascii=False)}')
    log(f'  inputs: {json.dumps(s["inputs"], ensure_ascii=False)}')
    log(f'  正文前200字: {s["body"][:150]}')
    return s

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_02_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(0,0))
    await conn.connect(); page = conn.page; await conn.init_anti_detection()
    await page.goto('https://www.douyin.com/', timeout=30000, wait_until='domcontentloaded')
    await asyncio.sleep(6)

    s = await scan(page, '首页')
    
    if s['loginPanel']:
        log('\n👉 发现登录面板')
        # 先找"登录"按钮/链接点击
        log('写 /tmp/scan_go 点击"登录"')
        while not os.path.exists(SIG): await asyncio.sleep(0.3)
        os.remove(SIG)

        # 点登录（找包含"登录"文字的元素）
        clicked = await page.evaluate("""() => {
            var all = document.querySelectorAll('a, button, [class*="login"], [class*="Login"]');
            for (var i = 0; i < all.length; i++) {
                if (all[i].textContent.includes('登录')) { all[i].click(); return true; }
            }
            return false;
        }""")
        await asyncio.sleep(3)
        await scan(page, '登录弹窗')

        log('\n👉 如看到一键登录，写 /tmp/scan_go 点击一键登录')
        while not os.path.exists(SIG): await asyncio.sleep(0.3)
        os.remove(SIG)

        btn = page.locator('button:has-text("一键登录")').first
        if await btn.count() > 0:
            await btn.click()
            log('  ✅ 点击了一键登录')
        else:
            log('  ⚠️ 未找到一键登录')
        await scan(page, '登录后')
        
        log('\n👉 如已触发短信验证，写 /tmp/scan_go 继续扫描验证码弹窗')
        while not os.path.exists(SIG): await asyncio.sleep(0.3)
        os.remove(SIG)
        await scan(page, 'SMS弹窗')

    log('\n✅ 浏览器保持打开')
    while True: await asyncio.sleep(10)

asyncio.run(main())
