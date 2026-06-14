#!/usr/bin/env python3
"""
auto_comment.py — 全自动评论（CoreGraphics 系统级输入）

流程：
  1. Playwright: 进视频 → 开评论
  2. CoreGraphics: 鼠标移到输入区 → 停顿 → 双击激活
  3. pbcopy + Cmd+V 粘贴中文
  4. CoreGraphics: Alt+Enter 发送
"""
import asyncio, os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector
import Quartz

LOG = '/tmp/auto_comment.log'
def log(m):
    with open(LOG, 'a') as f: f.write(f'[{time.strftime("%H:%M:%S")}] {m}\n')
    print(m, flush=True)

def cg_move(x, y):
    """CoreGraphics 移动鼠标"""
    p = Quartz.CGPointMake(x, y)
    e = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, p, 0)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, e)

def cg_click(x, y):
    """CoreGraphics 点击"""
    p = Quartz.CGPointMake(x, y)
    down = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseDown, p, 0)
    up = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseUp, p, 0)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    time.sleep(0.1)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)

def cg_key(code, down=True):
    """CoreGraphics 键盘按键"""
    e = Quartz.CGEventCreateKeyboardEvent(None, code, down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, e)

def cg_type(text):
    """CoreGraphics 输入文字"""
    for ch in text:
        cg_key(ord(ch.upper()), True)
        time.sleep(0.05)
        cg_key(ord(ch.upper()), False)
        time.sleep(0.05)

async def state(page):
    s = await page.evaluate("""() => {
        var ae = document.activeElement; var ed = document.querySelector('.public-DraftEditor-content');
        var hasCL = !!document.querySelector('[data-e2e="comment-list"]');
        return {
            aeTag: ae?.tagName||'none', aeIsEd: !!(ae && (ae.isContentEditable||ae.getAttribute('contenteditable')==='true')),
            edText: (ed?.textContent||'').trim().slice(0,30), hasEd: !!ed,
            hasCL: hasCL, hasVerify: !!document.querySelector('input[placeholder*="验证码"]'),
            aeRect: ae ? (function(){var r=ae.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})() : null,
        };
    }""")
    return s

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect(); page = conn.page; await conn.init_anti_detection()

    log('Step 1: 进视频')
    await page.goto('https://www.douyin.com/',timeout=20000); await asyncio.sleep(4)
    card = page.locator('.discover-video-card-item').first
    await card.click(force=True); await asyncio.sleep(1.5)
    vid = page.locator('video').first
    if await vid.count()>0: await vid.click(); await asyncio.sleep(1); await vid.click(); await asyncio.sleep(4)

    log('Step 2: 开评论')
    await page.keyboard.press('x'); await asyncio.sleep(2)
    s = await state(page)
    log(f'  CL={s["hasCL"]}')

    if not s['hasCL']:
        await page.evaluate("""()=>{var b=document.querySelector('[data-e2e="video-comment-count"]')||document.querySelector('[data-e2e="feed-comment-icon"]');if(b)b.click();}""")
        await asyncio.sleep(2)

    # Step 3: Playwright 鼠标激活输入框（用用户验证过的坐标）
    log('Step 3: 激活输入框')
    # 用用户双击验证过的精确坐标 (479, 687)
    cx, cy = 479, 687

    # 缓慢移动过去（模拟真人鼠标轨迹）
    for step in range(8):
        px = int(10 + (cx - 10) * (step+1) / 8)
        py = int(10 + (cy - 10) * (step+1) / 8)
        await page.mouse.move(px, py)
        await asyncio.sleep(0.1)
    await asyncio.sleep(0.5)  # 停顿让 hover 触发

    # 第1次单击
    await page.mouse.click(cx, cy)
    await asyncio.sleep(1)    # 停顿让页面响应

    s = await state(page)
    if s['aeIsEd']:
        log(f'  ✅ 第1次单击激活')
    else:
        # 第2次单击（双击模式）
        await page.mouse.click(cx, cy)
        await asyncio.sleep(1)

        s = await state(page)
        if s['aeIsEd']:
            log(f'  ✅ 双击激活')
        else:
            log(f'  ⚠️ 未激活(ae={s["aeTag"]})，试其他位置...')
            # 容器区域多点尝试
            for px, py in [(350,747), (300,747), (400,747), (250,747)]:
                await page.mouse.move(px, py)
                await asyncio.sleep(0.3)
                await page.mouse.click(px, py)
                await asyncio.sleep(0.5)
                await page.mouse.click(px, py)
                await asyncio.sleep(0.5)
                s = await state(page)
                if s['aeIsEd']:
                    log(f'  ✅ 位置({px},{py})激活')
                    break

    if not s['aeIsEd']:
        log('❌ 无法激活输入框')
        return

    log(f'  ✅ 输入框激活: ({s["aeRect"]["x"]}, {s["aeRect"]["y"]})')

    # Step 4: 粘贴中文
    log('Step 4: 粘贴中文')
    # 用 osascript 设置剪贴板（不需要辅助权限）
    subprocess.run(['osascript','-e','set the clipboard to "好内容"'], timeout=5)
    time.sleep(0.3)
    # 用 Playwright 的 Meta+V（浏览器内 Cmd+V，不依赖系统权限）
    await page.keyboard.press('Meta+v')
    await asyncio.sleep(2)

    s = await state(page)
    log(f'  粘贴后: edText="{s["edText"]}"')

    if s['edText']:
        log('Step 5: Alt+Enter 发送')
        # Alt+Enter = Option+Enter
        # Enter 的 key code = 36
        cg_key(58, True)   # Option key down
        time.sleep(0.1)
        cg_key(36, True)   # Enter down
        time.sleep(0.05)
        cg_key(36, False)  # Enter up
        cg_key(58, False)  # Option key up
        time.sleep(3)

        s = await state(page)
        log(f'  发送后: hasVerify={s["hasVerify"]}')
        if s['hasVerify']: log('\n🎉 完成！')
        else: log('\n⚠️ 未触发验证码')
    else:
        log('❌ 粘贴失败')

    log('\n✅ 浏览器保持打开')
    while True: await asyncio.sleep(10)

asyncio.run(main())
