#!/usr/bin/env python3
"""混合输入测试：AppleScript 打'a'激活 Draft.js → Playwright 打中文"""
import asyncio, os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

LOG = '/tmp/hybrid_input.log'
def log(m):
    with open(LOG, 'a') as f: f.write(f'[{time.strftime("%H:%M:%S")}] {m}\n')
    print(m, flush=True)

def activate():
    for _ in range(3):
        subprocess.run(['osascript','-e',
            'tell application "System Events" to set frontmost of every process whose name contains "camoufox" to true'],
            capture_output=True, timeout=3); time.sleep(0.3)

async def state(page):
    s = await page.evaluate("""() => {
        var ae = document.activeElement; var ed = document.querySelector('.public-DraftEditor-content');
        return {
            aeTag: ae?.tagName||'none', aeCls:(ae?.className||'').slice(0,30),
            aeIsEd: !!(ae && (ae.isContentEditable||ae.getAttribute('contenteditable')==='true')),
            edText: (ed?.textContent||'').trim().slice(0,30),
            hasVerify: !!document.querySelector('input[placeholder*="验证码"]'),
            aeRect: ae ? (function(){var r=ae.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})() : null,
        };
    }""")
    return s

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect(); page = conn.page; await conn.init_anti_detection()
    await page.goto('https://www.douyin.com/',timeout=20000); await asyncio.sleep(4)
    card = page.locator('.discover-video-card-item').first
    await card.click(force=True); await asyncio.sleep(1.5)
    vid = page.locator('video').first
    if await vid.count()>0: await vid.click(); await asyncio.sleep(1); await vid.click(); await asyncio.sleep(4)
    await page.keyboard.press('x'); await asyncio.sleep(2)

    log('请点输入框，然后写 /tmp/hybrid_go')
    while not os.path.exists('/tmp/hybrid_go'): await asyncio.sleep(0.3)
    os.remove('/tmp/hybrid_go')

    s = await state(page)
    log(f'点击后: aeIsEd={s["aeIsEd"]} aeRect={s["aeRect"]}')
    if not s['aeRect']: log('❌ 未激活'); return

    cx, cy = s['aeRect']['x'], s['aeRect']['y']
    scx, scy = 652 + cx, cy

    # ── AppleScript: 激活窗口 + 点编辑器 + 打'a'激活Draft.js ──
    log('Step 1: AppleScript 激活+点+打a')
    activate(); time.sleep(0.5)
    subprocess.run(['osascript','-e',f'tell application "System Events" to click at {{{scx},{scy}}}'], timeout=5)
    time.sleep(0.3)
    subprocess.run(['osascript','-e',f'tell application "System Events" to click at {{{scx},{scy}}}'], timeout=5)
    time.sleep(0.3)
    subprocess.run(['osascript','-e','tell application "System Events" to keystroke "a"'], timeout=5)
    time.sleep(1)

    s = await state(page)
    log(f'  打a后: edText="{s["edText"]}" aeIsEd={s["aeIsEd"]}')

    # 如果 'a' 打进去了，删掉它再打中文
    if 'a' in s['edText'] or s['aeIsEd']:
        log('  Draft.js 已激活！删a打中文')
        # Backspace 删掉 'a'
        subprocess.run(['osascript','-e','tell application "System Events" to keystroke "\b"'], timeout=5)
        time.sleep(0.3)

        # 剪贴板粘贴中文（Draft.js 认粘贴事件）
        log('  pbcopy + Cmd+V 粘贴中文...')
        subprocess.run(['bash','-c','echo -n "好内容" | pbcopy'], timeout=5)
        activate()
        time.sleep(0.3)
        subprocess.run(['osascript','-e','tell application "System Events" to keystroke "v" using command down'], timeout=5)
        await asyncio.sleep(2)

        s = await state(page)
        log(f'  中文输入后: edText="{s["edText"]}"')

        if s['edText']:
            log('  AppleScript Alt+Enter 发送...')
            activate()
            subprocess.run(['osascript','-e','tell application "System Events" to key code 36 using option down'], timeout=5)
            time.sleep(3)
            s = await state(page)
            log(f'  发送后: hasVerify={s["hasVerify"]}')
            if s['hasVerify']: log('🎉 完成！')
        else:
            log('❌ 中文没打进去')
    else:
        log('❌ 打a没激活Draft.js')

    log('\n✅ 浏览器保持打开')
    while True: await asyncio.sleep(10)

asyncio.run(main())
