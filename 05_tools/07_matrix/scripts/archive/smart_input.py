#!/usr/bin/env python3
"""
smart_input.py — 智能定位输入框

流程：
  1. 扫底部区域 → 找到输入框容器位置
  2. 鼠标移动触发懒加载 → 等编辑器出现
  3. 读编辑器精确坐标 → pyautogui 点击+打字
"""
import asyncio, os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector
import pyautogui

LOG = '/tmp/smart_input.log'
def log(m):
    with open(LOG, 'a') as f: f.write(f'[{time.strftime("%H:%M:%S")}] {m}\n')
    print(m, flush=True)

def activate_window():
    import subprocess
    for _ in range(3):
        try:
            subprocess.run(['osascript', '-e',
                'tell application "System Events" to set frontmost of every process whose name contains "camoufox" to true'],
                capture_output=True, timeout=3)
            time.sleep(0.3)
        except: pass

async def scan_bottom(page):
    """扫描底部 100px 区域，返回可能的输入框元素"""
    return await page.evaluate("""() => {
        const h = window.innerHeight;
        const els = [...document.querySelectorAll('*')].filter(el => {
            if (!el.offsetParent) return false;
            const r = el.getBoundingClientRect();
            return r.bottom > h - 100 && r.top < h - 5 && r.width > 200 && r.height > 15;
        });
        // 找最后一个宽元素（通常是输入条）
        const wide = els.filter(e => e.getBoundingClientRect().width > window.innerWidth * 0.5);
        return wide.slice(-3).map(e => {
            const r = e.getBoundingClientRect();
            return {
                tag: e.tagName, cls: (e.className||'').slice(0,40),
                x: Math.round(r.left+r.width/2), y: Math.round(r.top+r.height/2),
                rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
            };
        });
    }""")

async def find_editor(page):
    """找编辑器元素"""
    return await page.evaluate("""() => {
        const ed = document.querySelector('.public-DraftEditor-content')
                || document.querySelector('[contenteditable="true"]')
                || document.querySelector('[contenteditable]');
        if (!ed) return null;
        const r = ed.getBoundingClientRect();
        return {
            tag: ed.tagName, cls: (ed.className||'').slice(0,40),
            x: Math.round(r.left+r.width/2), y: Math.round(r.top+r.height/2),
            rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
        };
    }""")

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    log('='*55)
    log('🦀 智能定位输入框测试')
    log('='*55)

    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()
    await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(4)
    card = page.locator('.discover-video-card-item').first
    await card.click(force=True); await asyncio.sleep(1)
    await card.click(force=True); await asyncio.sleep(4)
    await page.keyboard.press('x'); await asyncio.sleep(2)

    # ── 1. 扫底部找到输入框容器 ──
    log('\n📡 Step 1: 扫描底部输入框容器')
    containers = await scan_bottom(page)
    for c in containers:
        log(f'  容器: {c["tag"]} rect={c["rect"]} cls={c["cls"]}')
    if not containers:
        log('❌ 未找到输入框容器')
        return
    target = containers[-1]  # 最后一个大容器通常是输入条
    log(f'🎯 目标容器: ({target["x"]}, {target["y"]}) rect={target["rect"]}')
    cx, cy = target['x'], target['y']

    # ── 2. 用 Playwright 点输入容器（触发编辑器懒加载）──
    log('\n📡 Step 2: 点击输入容器触发编辑器')
    await page.mouse.click(cx, cy)
    await asyncio.sleep(0.5)
    await page.mouse.click(cx, cy)  # 双击
    await asyncio.sleep(1.5)

    # 检查编辑器是否出现
    ed = await find_editor(page)
    if ed:
        log(f'✅ 编辑器已加载: ({ed["x"]}, {ed["y"]}) rect={ed["rect"]}')
        target = ed
    else:
        log('⚠️ 编辑器未加载，重试点击...')
        # 在输入区域横向多点尝试
        for x_off in [-80, -40, 0, 40, 80, -60, 60]:
            await page.mouse.click(cx + x_off, cy)
            await asyncio.sleep(0.3)
            ed = await find_editor(page)
            if ed:
                log(f'✅ 偏移{x_off}px后编辑器出现: ({ed["x"]}, {ed["y"]})')
                target = ed
                break

    # ── 3. 点编辑器 ──
    log(f'\n📡 Step 3: 点击编辑器 ({target["x"]}, {target["y"]})')
    sx, sy = 652 + target['x'], 0 + target['y']
    pyautogui.click(sx, sy)
    time.sleep(0.5)
    pyautogui.click(sx, sy)
    time.sleep(0.5)

    ae = await page.evaluate('() => document.activeElement?.tagName || "none"')
    log(f'  activeElement: {ae}')

    # ── 4. pyautogui 输入文字 ──
    log('\n📡 Step 4: 系统键盘输入')
    activate_window()
    pyautogui.write('好内容', interval=0.1)
    time.sleep(2)

    editor_text = await page.evaluate('() => document.querySelector(".public-DraftEditor-content")?.textContent?.trim()?.length || 0')
    log(f'  editor 文字长度: {editor_text}')

    if editor_text > 0:
        log('\n✅ 文字输入成功！')
        # 点发送按钮（寻找底部右侧的红色箭头）
        btn = await page.evaluate("""() => {
            const btns = [...document.querySelectorAll('button')];
            const send = btns.find(b => b.className.includes('send')||b.className.includes('arrow')||b.className.includes('submit'));
            if (!send) return null;
            const r = send.getBoundingClientRect();
            return {x: Math.round(r.left+r.width/2), y: Math.round(r.top+r.height/2)};
        }""")
        if btn:
            log(f'  🖱️ 点发送按钮 ({btn["x"]}, {btn["y"]})')
            sbtn_x, sbtn_y = 652 + btn['x'], 0 + btn['y']
            pyautogui.click(sbtn_x, sbtn_y)
            time.sleep(3)
            has_v = await page.evaluate("() => !!document.querySelector('input[placeholder*=\"验证码\"]')")
            log(f'  📱 验证码触发: {"✅" if has_v else "❌"}')
        else:
            log('  ⚠️ 未找到发送按钮')
    else:
        log('❌ 文字输入失败')

    log('\n✅ 完成，浏览器保持打开')
    while True: await asyncio.sleep(10)

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: log('👋 退出')
    except Exception as e:
        import traceback; log(f'❌ {e}'); log(traceback.format_exc())
