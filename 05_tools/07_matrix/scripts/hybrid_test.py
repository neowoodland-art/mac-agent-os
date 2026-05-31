#!/usr/bin/env python3
"""
hybrid_test.py — Playwright + pyautogui 混合测试

Playwright: 浏览器控制 + 状态检测
pyautogui:  系统级鼠标/键盘（绕开 Draft.js）
"""
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector
import pyautogui

LOG = '/tmp/hybrid_test.log'
SIG = {'url':'','vc':0,'hasCommentList':False,'hasEditor':False,
       'aeIsEditor':False,'editorTextLen':0,'sendBtnText':'','hasVerify':False}

def log(m):
    with open(LOG, 'a') as f: f.write(f'[{time.strftime("%H:%M:%S")}] {m}\n')
    print(m, flush=True)

async def read_sig(page):
    """Playwright 读状态"""
    s = await page.evaluate("""() => {
        const url = location.href;
        const vc = document.querySelectorAll('video').length;
        const hasCL = !!document.querySelector('[data-e2e="comment-list"]');
        const ed = document.querySelector('.public-DraftEditor-content');
        return {
            url, vc, hasCommentList: hasCL, hasEditor: !!ed,
            aeIsEditor: document.activeElement && (document.activeElement.classList.contains('public-DraftEditor-content') || document.activeElement.getAttribute('contenteditable')==='true'),
            editorTextLen: ed ? (ed.textContent||'').trim().length : 0,
            sendBtnText: [...document.querySelectorAll('button')].find(b => b.textContent.includes('发送')||b.className.includes('send')||b.className.includes('arrow')||b.className.includes('submit'))?.textContent?.slice(0,10)||'',
            hasVerify: !!document.querySelector('input[placeholder*="验证码"]'),
            aeTag: document.activeElement?.tagName||'none',
        };
    }""")
    for k in s: SIG[k] = s[k]
    return s

async def report(page, step, status, msg=''):
    s = await read_sig(page)
    log(f'📄 [{step}] {status}: {msg}')
    log(f'     vc={s["vc"]} comment={s["hasCommentList"]} editorLen={s["editorTextLen"]} btn="{s["sendBtnText"]}" verify={s["hasVerify"]}')

def activate_window():
    """AppleScript 确保窗口在最前"""
    import subprocess
    for _ in range(3):
        try:
            script = 'tell application "System Events" to set frontmost of every process whose name contains "camoufox" to true'
            subprocess.run(['osascript', '-e', script], capture_output=True, timeout=3)
            time.sleep(0.3)
        except: pass

def viewport_to_screen(vx, vy):
    """viewport 坐标 → 屏幕坐标（Camoufox 视口起始=窗口位置，无 chrome 偏移）"""
    win_left = 652
    win_top = 0
    return (win_left + vx, win_top + vy)

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    log(f'\n{"="*55}')
    log(' 🦀 混合模式测试：Playwright + pyautogui')
    log(f'{"="*55}')

    # ── Step 0: 启动浏览器（Playwright）──
    log('\n📍 Step 0: 启动浏览器')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()
    await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(6)

    # ── Step 1: 进视频（Playwright）──
    log('\n📍 Step 1: 进视频页')
    card = page.locator('.discover-video-card-item').first
    await card.click(force=True); await asyncio.sleep(1)
    await card.click(force=True); await asyncio.sleep(4)
    await report(page, 1, '进入视频')

    # ── Step 2: 打开评论（Playwright）──
    log('\n📍 Step 2: 打开评论区')
    vid = page.locator('video').first
    if await vid.count() > 0:
        box = await vid.bounding_box()
        if box: await page.mouse.click(box['x']+box['width']//2, box['y']+box['height']//3)
    await asyncio.sleep(0.5)
    await page.keyboard.press('x')
    await asyncio.sleep(2)
    await report(page, 2, '打开评论')

    if not SIG['hasCommentList']:
        log('❌ 评论区未打开')
        return

    # ── Step 3: pyautogui 双击输入框──
    log('\n📍 Step 3: 系统鼠标双击输入框')
    activate_window()
    # 输入框在底部 bar (0,723,702,48) 居中
    INPUT_VX, INPUT_VY = 350, 747
    sx, sy = viewport_to_screen(INPUT_VX, INPUT_VY)
    log(f'   屏幕坐标: ({sx}, {sy})')
    pyautogui.click(sx, sy)
    time.sleep(1)
    pyautogui.click(sx, sy)  # 双击
    time.sleep(0.5)
    await report(page, 3, '双击输入框')
    if not SIG['aeIsEditor']:
        log(f'  ⚠️ 未聚焦编辑器，当前 activeTag={SIG.get("aeTag","?")}')

    # ── Step 4: pyautogui 输入文字──
    log('\n📍 Step 4: 系统键盘输入文字')
    activate_window()
    TEST_TEXT = '好内容'
    pyautogui.write(TEST_TEXT, interval=0.1)
    time.sleep(2)
    await report(page, 4, f'输入: {TEST_TEXT}')

    if SIG['editorTextLen'] == 0:
        log('⚠️ 文字没进去，尝试 execCommand 兜底')
        await page.evaluate("""() => {
            const ed = document.querySelector('.public-DraftEditor-content');
            if (!ed) return;
            ed.focus();
            const r = document.createRange(); r.selectNodeContents(ed);
            window.getSelection().removeAllRanges(); window.getSelection().addRange(r);
            document.execCommand('insertText', false, '好内容，已三连');
        }""")
        await asyncio.sleep(1)
        await report(page, 4, 'execCommand兜底')

    # ── Step 5: pyautogui 点发送按钮──
    log('\n📍 Step 5: 系统鼠标点发送按钮')
    activate_window()
    # 红色上箭头在输入框最右，离右边缘约 30px
    btn_x, btn_y = viewport_to_screen(670, 747)
    log(f'   发送按钮坐标: ({btn_x}, {btn_y})')
    pyautogui.click(btn_x, btn_y)
    time.sleep(3)
    await report(page, 5, '点击发送')

    if SIG['hasVerify']:
        log('\n📱 触发了验证码！评论发送成功（需验证码）')
    elif SIG['editorTextLen'] > 0 and not SIG['hasVerify']:
        log('\n⚠️ 文字在但没触发验证码，可能没发出去')
    else:
        log('\n❌ 未触发任何响应')

    log(f'\n{"="*55}')
    log(' ✅ 测试完成，浏览器保持打开')
    while True: await asyncio.sleep(10)

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: log('👋 退出')
    except Exception as e:
        import traceback; log(f'❌ {e}'); log(traceback.format_exc())
