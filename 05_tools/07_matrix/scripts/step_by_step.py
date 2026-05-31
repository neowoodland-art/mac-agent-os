#!/usr/bin/env python3
"""step_by_step.py — 逐步骤执行，每步报告状态等你确认"""
import asyncio, os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

LOG = '/tmp/s2.log'; SIG = '/tmp/s2_go'
def log(m):
    with open(LOG, 'a') as f: f.write(f'[{time.strftime("%H:%M:%S")}] {m}\n')
    print(m, flush=True)
def wait():
    while not os.path.exists(SIG): time.sleep(0.3)
    os.remove(SIG)

async def state(page):
    return await page.evaluate("""() => {
        var ae = document.activeElement; var ed = document.querySelector('.public-DraftEditor-content');
        return {
            url: (location.href||'').slice(0,50), vc: document.querySelectorAll('video').length,
            cards: document.querySelectorAll('.discover-video-card-item').length,
            hasCL: !!document.querySelector('[data-e2e="comment-list"]'),
            hasEd: !!ed, edText: (ed?.textContent||'').trim().slice(0,15),
            aeTag: ae?.tagName||'none', aeCls:(ae?.className||'').slice(0,30),
            aeIsEd: !!(ae && (ae.isContentEditable||ae.getAttribute('contenteditable')==='true')),
            aeRect: ae ? (function(){var r=ae.getBoundingClientRect(); return {x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2),l:Math.round(r.left),t:Math.round(r.top),w:Math.round(r.width),h:Math.round(r.height)};})() : null,
            hasVerify: !!document.querySelector('input[placeholder*="验证码"]'),
        };
    }""")

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect(); page = conn.page; await conn.init_anti_detection()

    # Step 0: 启动
    log('Step 0: 启动→精选页')
    await page.goto('https://www.douyin.com/',timeout=20000,wait_until='domcontentloaded')
    await asyncio.sleep(5)
    s = await state(page)
    log(f'  URL={s["url"]} cards={s["cards"]} vc={s["vc"]}')
    log(f'  状态: H_JINGXUAN')
    log('继续? 写 /tmp/s2_go'); wait()

    # Step 1: 进视频
    log('Step 1: 进视频（卡片→video）')
    card = page.locator('.discover-video-card-item').first
    await card.click(force=True); await asyncio.sleep(1.5)
    vid = page.locator('video').first
    if await vid.count()>0: await vid.click(); await asyncio.sleep(1); await vid.click(); await asyncio.sleep(4)
    s = await state(page)
    log(f'  vc={s["vc"]} URL={s["url"]}')
    log(f'  状态: {"P_FULL" if s["vc"]>=2 else "H_JINGXUAN"}')
    log('继续? 写 /tmp/s2_go'); wait()

    # Step 2: 开评论
    log('Step 2: 开评论')
    vid2 = page.locator('video').first
    if await vid2.count()>0:
        box = await vid2.bounding_box()
        if box: await page.mouse.click(box['x']+box['width']//2,box['y']+box['height']//3)
    await asyncio.sleep(0.5); await page.keyboard.press('x'); await asyncio.sleep(2)
    s = await state(page)
    log(f'  hasCL={s["hasCL"]} hasEd={s["hasEd"]}')
    if not s['hasCL']:
        await page.evaluate("""()=>{var b=document.querySelector('[data-e2e="video-comment-count"]')||document.querySelector('[data-e2e="feed-comment-icon"]');if(b)b.click();}""")
        await asyncio.sleep(2); s = await state(page)
        log(f'  DOM后 hasCL={s["hasCL"]}')
    log(f'  状态: C_PANEL')
    log('请点输入框, 然后写 /tmp/s2_go'); wait()

    # Step 3: 读坐标
    log('Step 3: 读输入框坐标')
    s = await state(page)
    log(f'  aeTag={s["aeTag"]} aeIsEd={s["aeIsEd"]} aeCls={s["aeCls"]}')
    if s['aeRect']:
        cx,cy=s['aeRect']['x'],s['aeRect']['y']
        scx,scy=652+cx,cy
        log(f'  视口: ({cx},{cy})  屏幕: ({scx},{scy})')
        log(f'  元素: {s["aeRect"]["w"]}×{s["aeRect"]["h"]}  离右: {702-cx}px  离底: {783-cy}px')
    log('')
    log('下一步: AppleScript keystroke 系统级输入')
    log('  1. 窗口置前')
    log('  2. 点坐标确保焦点')
    log('  3. keystroke "好内容"')
    log('  4. key code Alt+Enter')
    log('执行? 写 /tmp/s2_go'); wait()

    # Step 4: AppleScript 打字
    log('Step 4: AppleScript 系统级输入')
    import subprocess
    for _ in range(3):
        subprocess.run(['osascript','-e',
            'tell application "System Events" to set frontmost of every process whose name contains "camoufox" to true'],
            capture_output=True, timeout=3)
        time.sleep(0.3)
    time.sleep(0.5)

    scx,scy = 652 + s['aeRect']['x'], s['aeRect']['y']
    subprocess.run(['osascript','-e',f'tell application "System Events" to click at {{{scx},{scy}}}'], timeout=5)
    time.sleep(0.3)
    subprocess.run(['osascript','-e',f'tell application "System Events" to click at {{{scx},{scy}}}'], timeout=5)
    time.sleep(0.3)
    subprocess.run(['osascript','-e','tell application "System Events" to keystroke "好内容"'], timeout=5)
    time.sleep(2)

    s = await state(page)
    log(f'  输入后: edText="{s["edText"]}"')
    log(f'  键入方案A完成, 是否有文字? {bool(s["edText"])}')

    if s['edText']:
        log('  Alt+Enter 发送...')
        subprocess.run(['osascript','-e',
            'tell application "System Events" to key code 36 using option down'],
            capture_output=True, timeout=5)
        time.sleep(3)
        s = await state(page)
        log(f'  发送后: hasVerify={s["hasVerify"]}')
        if s['hasVerify']: log('🎉 完整链路跑通！')
        else: log('⚠️ 未触发验证码')
    else:
        log('❌ AppleScript keystroke 没打进去,Draft.js不认')

    log('\n✅ 浏览器保持打开')
    while True: await asyncio.sleep(10)

asyncio.run(main())
