#!/usr/bin/env python3
"""
final_chain.py — 完整链路最终测试

Playwright: 启动 → 进视频 → 开评论 → 状态检测
pyautogui:  打字（系统级） → Alt+Enter（系统级）
你:         点输入框（手动）
"""
import asyncio, os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector
import pyautogui

LOG = '/tmp/final_chain.log'
def log(m):
    with open(LOG, 'a') as f: f.write(f'[{time.strftime("%H:%M:%S")}] {m}\n')
    print(m, flush=True)

def activate():
    import subprocess
    for _ in range(3):
        try:
            subprocess.run(['osascript', '-e',
                'tell application "System Events" to set frontmost of every process whose name contains "camoufox" to true'],
                capture_output=True, timeout=3)
            time.sleep(0.3)
        except: pass

async def read_sig(page):
    s = await page.evaluate("""() => ({
        url: location.href,
        vc: document.querySelectorAll('video').length,
        hasCL: !!document.querySelector('[data-e2e="comment-list"]'),
        hasEd: !!document.querySelector('.public-DraftEditor-content'),
        aeTag: document.activeElement?.tagName||'none',
        aeIsEd: document.activeElement && (document.activeElement.classList.contains('public-DraftEditor-content')||document.activeElement.getAttribute('contenteditable')==='true'),
        editorText: (document.querySelector('.public-DraftEditor-content')?.textContent||'').trim().slice(0,20),
        hasVerify: !!document.querySelector('input[placeholder*="验证码"]'),
    })""")
    return s

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()

    # Playwright: 进视频 + 开评论
    log('📍 Step 1: 进视频')
    await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(4)
    # 第1次点卡片→预览
    card = page.locator('.discover-video-card-item').first
    await card.click(force=True); await asyncio.sleep(1.5)
    # 第2次点 video→进播放器（不是点卡片）
    vid = page.locator('video').first
    if await vid.count() > 0:
        await vid.click(timeout=5000); await asyncio.sleep(1)
        await vid.click(timeout=5000); await asyncio.sleep(3)
    log('📍 Step 2: 开评论')
    await page.keyboard.press('x'); await asyncio.sleep(2)

    s = await read_sig(page)
    log(f'状态: commentList={s["hasCL"]} editor={s["hasEd"]} ae={s["aeTag"]}')

    log('\n' + '='*50)
    log('请用鼠标点一下输入框（让光标闪烁）')
    log('然后告诉我"点了"')
    log('='*50)

    # 等用户信号
    while not os.path.exists('/tmp/chain_signal'):
        await asyncio.sleep(0.3)
    os.remove('/tmp/chain_signal')

    # 读激活元素坐标
    ae_info = await page.evaluate("""() => {
        var ae = document.activeElement;
        if (!ae) return null;
        var r = ae.getBoundingClientRect();
        return {x: Math.round(r.left+r.width/2), y: Math.round(r.top+r.height/2),
                tag: ae.tagName, cls: (ae.className||'').slice(0,30)};
    }""")
    log(f'📊 激活元素: {ae_info}')

    # pyautogui: 先点编辑器确保焦点 + 打字
    log('\n📍 Step 3: pyautogui 点击+输入文字')
    activate()
    time.sleep(0.5)  # 等窗口完全置前

    # 先点一下编辑器位置确保焦点
    sx, sy = 652 + ae_info['x'], ae_info['y']
    log(f'  点击编辑器屏幕坐标: ({sx}, {sy})')
    pyautogui.click(sx, sy)
    time.sleep(0.5)
    pyautogui.click(sx, sy)  # 双击确保
    time.sleep(0.3)

    # 打字
    log('  ⏎ 输入文字...')
    pyautogui.write('好内容', interval=0.08)
    time.sleep(1.5)

    s = await read_sig(page)
    log(f'输入后: editorText="{s["editorText"]}"')

    if not s['editorText']:
        log('⚠️ pyautogui 没打进去，试试 execCommand 兜底')
        await page.evaluate("""() => {
            var ed = document.querySelector('.public-DraftEditor-content');
            if (!ed) return;
            ed.focus();
            var r = document.createRange(); r.selectNodeContents(ed);
            window.getSelection().removeAllRanges(); window.getSelection().addRange(r);
            document.execCommand('insertText', false, '好内容');
        }""")
        await asyncio.sleep(1)
        s = await read_sig(page)
        log(f'execCommand后: editorText="{s["editorText"]}"')

    if s['editorText']:
        # pyautogui: Alt+Enter
        log('\n📍 Step 4: pyautogui Alt+Enter 发送')
        activate()
        pyautogui.keyDown('alt')
        pyautogui.press('enter')
        pyautogui.keyUp('alt')
        time.sleep(3)

        s = await read_sig(page)
        log(f'发送后: verify={s["hasVerify"]}')

        if s['hasVerify']:
            log('\n🎉 完整链路跑通！短信验证码已触发')
        else:
            log('⚠️ 未触发验证码')
    else:
        log('❌ 文字输入失败')

    log('\n✅ 浏览器保持打开')
    while True: await asyncio.sleep(10)

asyncio.run(main())
