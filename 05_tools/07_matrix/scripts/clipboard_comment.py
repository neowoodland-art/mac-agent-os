#!/usr/bin/env python3
"""
clipboard_comment.py — 剪贴板粘贴式输入（绕开中文输入法）

流程：
  1. Playwright: 进视频 → 开评论
  2. 你点输入框
  3. pbcopy + Cmd+V 粘贴中文（系统级，绕开输入法）
  4. AppleScript Alt+Enter 发送
"""
import asyncio, os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

LOG = '/tmp/clipboard_comment.log'
SIG = '/tmp/clipboard_go'
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

    log('Step 0-1: 进视频')
    await page.goto('https://www.douyin.com/',timeout=20000); await asyncio.sleep(4)
    card = page.locator('.discover-video-card-item').first
    await card.click(force=True); await asyncio.sleep(1.5)
    vid = page.locator('video').first
    if await vid.count()>0: await vid.click(); await asyncio.sleep(1); await vid.click(); await asyncio.sleep(4)

    log('Step 2: 开评论')
    await page.keyboard.press('x'); await asyncio.sleep(2)
    s = await state(page)
    log(f'  评论: hasEd={s["aeIsEd"]} CL={await page.evaluate("()=>!!document.querySelector(\"[data-e2e=comment-list]\")")}')

    log('\n请点输入框，然后写 /tmp/clipboard_go')
    while not os.path.exists(SIG): await asyncio.sleep(0.3)
    os.remove(SIG)

    s = await state(page)
    if not s.get('aeRect'):
        log('❌ 未激活输入框')
        return
    cx, cy = s['aeRect']['x'], s['aeRect']['y']
    scx, scy = 652 + cx, cy
    log(f'输入框: ({cx},{cy}) 屏幕({scx},{scy}) aeIsEd={s["aeIsEd"]}')

    # ── 核心：剪贴板粘贴 ──
    log('\nStep 3: 剪贴板粘贴中文')
    activate(); time.sleep(0.5)

    # 再点一下确保焦点
    subprocess.run(['osascript','-e',f'tell application "System Events" to click at {{{scx},{scy}}}'], timeout=5)
    time.sleep(0.3)
    subprocess.run(['osascript','-e',f'tell application "System Events" to click at {{{scx},{scy}}}'], timeout=5)
    time.sleep(0.3)

    # 复制到剪贴板 + Cmd+V 粘贴
    TEXT = '好内容'
    subprocess.run(['bash','-c',f'echo -n "{TEXT}" | pbcopy'], timeout=5)
    time.sleep(0.2)
    subprocess.run(['osascript','-e','tell application "System Events" to keystroke "v" using command down'], timeout=5)
    time.sleep(2)

    s = await state(page)
    log(f'  粘贴后: edText="{s["edText"]}"')

    if s['edText']:
        log('\nStep 4: Alt+Enter 发送')
        activate()
        subprocess.run(['osascript','-e','tell application "System Events" to key code 36 using option down'], timeout=5)
        time.sleep(3)

        s = await state(page)
        log(f'  发送后: hasVerify={s["hasVerify"]}')
        if s['hasVerify']: log('\n🎉 完成！短信验证码已触发')
        else: log('\n⚠️ 未触发验证码')
    else:
        log('\n❌ 粘贴失败')

    log('\n✅ 浏览器保持打开')
    while True: await asyncio.sleep(10)

asyncio.run(main())
