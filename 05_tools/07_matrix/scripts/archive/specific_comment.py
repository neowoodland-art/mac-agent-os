#!/usr/bin/env python3
"""特定视频搜索评论任务"""
import asyncio, os, sys, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

URL = 'https://v.douyin.com/A96RNOqINtU/'
LOG = '/tmp/specific_comment.log'
def log(m):
    with open(LOG,'a') as f: f.write(m+'\n'); print(m,flush=True)

async def state(p):
    return await p.evaluate("""() => {
        var ae=document.activeElement; var ed=document.querySelector('.public-DraftEditor-content');
        return {
            url:(location.href||'').slice(0,60), vc:document.querySelectorAll('video').length,
            hasCL:!!document.querySelector('[data-e2e="comment-list"]'),
            hasEd:!!ed, aeIsEd:!!(ae&&(ae.isContentEditable||ae.getAttribute('contenteditable')==='true')),
            edText:(ed?.textContent||'').trim().slice(0,20),
            hasVerify:!!document.querySelector('input[placeholder*="验证码"]'),
        };
    }""")

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(0,0))
    await conn.connect(); p = conn.page; await conn.init_anti_detection()

    log('📍 Step 1: 打开视频')
    await p.goto(URL, timeout=30000, wait_until='domcontentloaded')
    await asyncio.sleep(6)

    s = await state(p)
    log(f'  URL: {s["url"]}  vc={s["vc"]}')

    # 等页面完全加载（视频播放页可能需要额外时间）
    if s['vc'] < 2:
        log('  ⏳ 等视频加载...')
        await asyncio.sleep(5)
        s = await state(p)
        log(f'  URL: {s["url"]}  vc={s["vc"]}')

    if s['vc'] < 2:
        log('❌ 未进入视频播放页')
        return

    log('📍 Step 2: 开评论')
    v = p.locator('video').first
    if await v.count()>0:
        bx = await v.bounding_box()
        if bx: await p.mouse.click(bx['x']+bx['width']//2, bx['y']+bx['height']//3)
    await asyncio.sleep(0.5)
    await p.keyboard.press('x')
    await asyncio.sleep(2)
    s = await state(p)
    log(f'  hasCL={s["hasCL"]}')
    if not s['hasCL']:
        await p.evaluate("""()=>{var b=document.querySelector('[data-e2e="video-comment-count"]')||document.querySelector('[data-e2e="feed-comment-icon"]');if(b)b.click();}""")
        await asyncio.sleep(2)
        s = await state(p)
        log(f'  DOM后 hasCL={s["hasCL"]}')
    
    if not s['hasCL']:
        log('❌ 打不开评论区')
        return

    log('📍 Step 3: 激活输入框')
    for step in range(8):
        await p.mouse.move(10+(479-10)*(step+1)/8, 10+(687-10)*(step+1)/8); await asyncio.sleep(0.1)
    await asyncio.sleep(0.5)
    await p.mouse.click(479,687); await asyncio.sleep(1)
    s = await state(p)
    if not s['aeIsEd']:
        await p.mouse.click(479,687); await asyncio.sleep(1)
        s = await state(p)
    log(f'  aeIsEd={s["aeIsEd"]} hasEd={s["hasEd"]}')

    if not s['aeIsEd']:
        log('❌ 无法激活输入框')
        return

    log('📍 Step 4: 粘贴评论')
    subprocess.run(['osascript','-e','set the clipboard to "找朋友手势舞太有趣了，格局打开！"'], timeout=5)
    await p.keyboard.press('Meta+v'); await asyncio.sleep(2)
    s = await state(p)
    log(f'  粘贴后: edText="{s["edText"]}"')

    if s['edText']:
        log('📍 Step 5: Alt+Enter 发送')
        subprocess.run(['osascript','-e','tell application "System Events" to key code 36 using option down'], timeout=5)
        await asyncio.sleep(3)
        s = await state(p)
        log(f'  发送后: hasVerify={s["hasVerify"]}')
        if s['hasVerify']:
            log('📱 触发了验证码')
        else:
            log('✅ 评论已发送（无验证码）')
    else:
        log('❌ 粘贴失败')

    log('\n✅ 完成，浏览器保持打开')
    while True: await asyncio.sleep(10)

asyncio.run(main())
