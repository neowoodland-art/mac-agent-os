#!/usr/bin/env python3
"""
interactive_test.py — 交互式原子操作测试

通过 /tmp/test_signal 文件控制流程：
  写入 "step1" → 执行第一个原子操作
  写入 "step2" → 执行第二个原子操作
  写入 "status" → 读取当前状态特征码
  写入 "exit" → 优雅关闭浏览器并退出

每次执行后写入 /tmp/test_report.json 报告结果
"""
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

SIGNAL = '/tmp/test_signal'
REPORT = '/tmp/test_report.json'
LOG = '/tmp/interactive_test.log'

page = None
conn = None

def log(m):
    with open(LOG, 'a') as f: f.write(f'[{time.strftime("%H:%M:%S")}] {m}\n')
    print(m, flush=True)

def report(data):
    with open(REPORT, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f'📄 报告已写入: {json.dumps(data, ensure_ascii=False)[:200]}')

async def read_signature(p):
    """读取当前页面特征码"""
    return await p.evaluate("""() => {
        const url = location.href;
        const vc = document.querySelectorAll('video').length;
        const cards = document.querySelectorAll('.discover-video-card-item').length;
        const alinkItems = document.querySelectorAll('[data-e2e="alink-item"]').length;
        const hasDigg = !!document.querySelector('[data-e2e="video-player-digg"]');
        const hasCommentList = !!document.querySelector('[data-e2e="comment-list"]');
        const hasEditor = !!document.querySelector('.public-DraftEditor-content');
        const ae = document.activeElement;
        const aeIsEditor = ae && (ae.classList.contains('public-DraftEditor-content') || ae.getAttribute('contenteditable')==='true');
        const hasAvatar = !!document.querySelector('[data-e2e="user-avatar"]');
        return {
            url, title: document.title, vc, cards, alinkItems, hasDigg,
            hasCommentList, hasEditor, aeIsEditor,
            aeTag: ae ? ae.tagName : 'none',
            hasAvatar, winW: window.innerWidth, winH: window.innerHeight,
            editorTextLen: (document.querySelector('.public-DraftEditor-content')?.textContent || '').trim().length,
            sendBtnText: [...document.querySelectorAll('button')].find(b => b.textContent.includes('发送') || b.className.includes('send') || b.className.includes('submit') || b.className.includes('arrow'))?.textContent?.slice(0,10) || '',
            hasVerify: !!document.querySelector('input[placeholder*="验证码"]'),
        };
    }""")

async def activate_window():
    """窗口置顶"""
    import subprocess
    try:
        script = 'tell application "System Events" to set frontmost of every process whose name contains "camoufox" to true'
        subprocess.run(['osascript', '-e', script], capture_output=True, timeout=3)
    except: pass

async def step_launch():
    """Step 0: 启动浏览器 → 精选页"""
    global page, conn
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    log('🚀 启动 Camoufox...')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()
    log('📍 导航到 douyin.com...')
    await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(6)
    sig = await read_signature(page)
    report({
        'step': '0_launch',
        'status': 'ready',
        'state': 'H_JINGXUAN',
        'signature': sig,
        'message': f'精选页已加载，卡片{sig["cards"]}个，video={sig["vc"]}'
    })

async def step_enter_video():
    """Step 1: 精选页 → 视频播放页（从远处移动鼠标→双击→检查跳转）"""
    await activate_window()
    log('🎯 从远处移动鼠标→双击卡片...')

    # 先获取卡片位置和卡片宽高
    card_info = await page.evaluate("""() => {
        const card = document.querySelector('.discover-video-card-item');
        if (!card) return null;
        const r = card.getBoundingClientRect();
        return {
            cx: Math.round(r.left + r.width / 2),
            cy: Math.round(r.top + r.height / 2),
            x: Math.round(r.left), y: Math.round(r.top),
            w: Math.round(r.width), h: Math.round(r.height),
        };
    }""")
    log(f'  卡片位置: ({card_info["cx"]}, {card_info["cy"]}) 大小:{card_info["w"]}×{card_info["h"]}')

    if not card_info:
        report({'step':'1_enter_video','status':'failed','reason':'无卡片'})
        return

    # 第1次点击：点卡片 → 预览播放
    log('  第1次点击：卡片→预览播放')
    card = page.locator('.discover-video-card-item').first
    await card.click(force=True, timeout=5000)
    await asyncio.sleep(1.5)

    # 第2次点击：直接点预览中的 video 元素（不是卡片）
    log('  第2次点击：点预览视频→进入播放器')
    try:
        vid = page.locator('video').first
        await vid.click(timeout=5000)
        await asyncio.sleep(1)
        await vid.click(timeout=5000)  # 双击视频
        await asyncio.sleep(3)
    except:
        log('  ⚠️ video元素不可点，用坐标跑')
        # 从卡片位置偏移一些，因为视频预览可能在卡片内偏下
        await page.mouse.click(card_info['cx'], card_info['cy'] + int(card_info['h']*0.3))
        await asyncio.sleep(1)
        await page.mouse.click(card_info['cx'], card_info['cy'] + int(card_info['h']*0.3))
        await asyncio.sleep(3)

    sig = await read_signature(page)
    is_full_player = '/video/' in sig['url'] or sig['hasDigg']
    report({
        'step': '1_enter_video',
        'status': 'ok' if is_full_player else ('preview_only' if sig['vc']>=2 else 'no_change'),
        'state': 'P_FULL' if is_full_player else ('P_OVERLAY' if sig['vc']>=2 else 'H_JINGXUAN'),
        'signature': sig,
        'message': f'video={sig["vc"]}, digg={"✅" if sig["hasDigg"] else "❌"}, /video/={"✅" if "/video/" in sig["url"] else "❌"}'
    })

async def step_open_comments():
    """Step 2: 视频播放页 → 打开评论区"""
    await activate_window()

    # 先点视频获取焦点
    log('🖱️ 点击视频区域获取焦点...')
    vid = page.locator('video').first
    if await vid.count() > 0:
        box = await vid.bounding_box()
        if box:
            await page.mouse.click(box['x'] + box['width']//2, box['y'] + box['height']//3)
            await asyncio.sleep(0.5)

    # 策略A: 键盘 x
    log('⌨️ 按 x 键打开评论区...')
    await page.keyboard.press('x')
    await asyncio.sleep(2)
    sig = await read_signature(page)
    if sig['hasCommentList']:
        report({
            'step': '2_open_comments',
            'status': 'ok', 'method': 'keyboard_x', 'state': 'C_PANEL',
            'signature': sig,
            'message': f'键盘x打开成功, editor={"✅" if sig["hasEditor"] else "❌"}'
        })
        return

    # 策略B: DOM 点评论图标
    log('🎯 DOM 点评论图标...')
    clicked = await page.evaluate("""() => {
        const btn = document.querySelector('[data-e2e="video-comment-count"]')
                || document.querySelector('[data-e2e="feed-comment-icon"]');
        if (btn) { btn.click(); return true; }
        return false;
    }""")
    await asyncio.sleep(2)
    sig = await read_signature(page)
    if clicked and sig['hasCommentList']:
        report({'step':'2_open_comments','status':'ok','method':'dom_click','state':'C_PANEL','signature':sig})
    else:
        report({'step':'2_open_comments','status':'failed','method':'both','signature':sig})

async def step_focus_editor():
    """Step 3: 评论面板 → 聚焦输入框"""
    await activate_window()
    log('🎯 双击输入框聚焦...')

    # 策略1: Playwright locator 点 .public-DraftEditor-content
    try:
        editor = page.locator('.public-DraftEditor-content').first
        if await editor.count() > 0:
            log('  locator 找到编辑器')
            await editor.click(timeout=5000)
            await asyncio.sleep(1)
            await editor.click(timeout=5000)
            await asyncio.sleep(0.5)
            sig = await read_signature(page)
            if sig['aeIsEditor']:
                report({'step':'3_focus_editor','status':'ok','method':'locator','state':'INPUT_FOCUSED','signature':sig})
                return
    except: pass

    # 策略2: 坐标双击（479, 687）
    log('  坐标双击 (479, 687)')
    from matrix_modules.nurture.ui_layout import calc_input_position
    tx, ty = calc_input_position(702, 783)
    log(f'  坐标: ({tx}, {ty})')

    # 先移到远处，再快速移到坐标
    await page.mouse.move(10, 10)
    await asyncio.sleep(0.3)
    await page.mouse.move(tx, ty)
    await asyncio.sleep(0.3)
    await page.mouse.click(tx, ty)
    await asyncio.sleep(1)
    await page.mouse.click(tx, ty)
    await asyncio.sleep(0.5)

    sig = await read_signature(page)
    if sig['aeIsEditor']:
        report({'step':'3_focus_editor','status':'ok','method':'coordinate','state':'INPUT_FOCUSED','signature':sig})
    else:
        report({'step':'3_focus_editor','status':'failed','method':'both','signature':sig,
                'message':f'aeIsEditor={sig["aeIsEditor"]}, activeTag={sig["aeTag"]}'})

async def step_type_comment():
    """Step 4: 输入文字"""
    await activate_window()
    TEST_TEXT = '好内容，已三连'

    # 方案A: execCommand 写入文字 + 空格触发 Draft.js
    log(f'🔧 execCommand 写入 + 空格触发')
    # 逐字模拟键盘事件（beforeinput + input，Draft.js 识别的）
    log(f'⌨️ 逐字模拟键盘事件')
    try:
        await page.evaluate(f'''() => {{
            const ed = document.querySelector('.public-DraftEditor-content');
            if (!ed) return;
            ed.focus();
            ed.click();
            for (const ch of "{TEST_TEXT}") {{
                ed.dispatchEvent(new InputEvent('beforeinput', {{
                    bubbles: true, cancelable: true,
                    inputType: 'insertText', data: ch
                }}));
                document.execCommand('insertText', false, ch);
                ed.dispatchEvent(new InputEvent('input', {{
                    bubbles: true, cancelable: true,
                    inputType: 'insertText', data: ch
                }}));
            }}
        }}''')
        await asyncio.sleep(1.5)
    except Exception as e:
        log(f'  ⚠️ 逐字模拟异常: {e}')
    except Exception as e:
        log(f'  ⚠️ execCommand 异常: {e}')

    # 空格触发 Draft.js 检测内容变化
    log(f'⌨️ 空格触发刷新')
    await page.keyboard.press('Space')
    await asyncio.sleep(2)

    sig = await read_signature(page)
    report({'step':'4_type_comment','status':'ok' if sig.get('editorTextLen','') else 'warn',
            'method':'execCommand+Space',
            'signature':sig,
            'message':f'textLen={sig.get("editorTextLen",0)}, sendBtn="{sig.get("sendBtnText","")}"'})

async def step_send_comment():
    """Step 5: 发送评论"""
    await activate_window()
    log('📤 发送评论')

    # 点击空白处（评论面板标题区域）→ 让 Draft.js 失去焦点
    log('🖱️ 点空白区域')
    await page.mouse.click(200, 300)
    await asyncio.sleep(0.5)

    # 再点回输入框 → Draft.js 重新检测内容
    log('🎯 再点回输入框')
    await page.mouse.click(479, 687)
    await asyncio.sleep(0.5)
    await page.mouse.click(479, 687)  # 双击确保
    await asyncio.sleep(0.5)

    # 找发送按钮点击
    log('🔍 找发送按钮')
    for attempt in range(3):
        clicked = await page.evaluate("""() => {
            const btns = [...document.querySelectorAll('button, [class*="send"], [class*="submit"]')];
            const send = btns.find(b =>
                b.textContent.includes('发送') || b.className.includes('send')
                || b.className.includes('submit') || b.className.includes('arrow')
                || b.className.includes('confirm'));
            if (send) { send.click(); return true; }
            return false;
        }""")
        if clicked:
            log(f'  ✅ 第{attempt+1}次尝试: 发送按钮已点击')
            break
        await asyncio.sleep(0.5)
    else:
        log('  ⚠️ 未找到发送按钮')

    await asyncio.sleep(3)

    # 检测验证码
    sig = await read_signature(page)

    # 专门检测验证码弹窗
    has_verify = await page.evaluate("() => !!(document.querySelector('input[placeholder*=\"验证码\"]') || document.querySelector('.second-verify-panel'))")
    log(f'  📱 验证码弹窗: {"✅" if has_verify else "❌"}')

    report({'step':'5_send_comment',
            'status':'verify_code' if has_verify else 'sent',
            'signature':sig,
            'message':f'hasVerify={"✅" if has_verify else "❌"}, sendBtn="{sig.get("sendBtnText","")}"'})

# ── 执行映射 ──
STEPS = {
    'launch': step_launch,
    'enter_video': step_enter_video,
    'open_comments': step_open_comments,
    'focus_editor': step_focus_editor,
    'type_comment': step_type_comment,
    'send_comment': step_send_comment,
}

async def main():
    log('='*50)
    log('🔄 交互测试脚本已启动')
    log('信号文件: /tmp/test_signal')
    log('报告文件: /tmp/test_report.json')
    log('='*50)

    # 先启动浏览器
    await step_launch()
    log('\n✅ 浏览器已就绪，等待信号...\n')

    while True:
        if os.path.exists(SIGNAL):
            cmd = open(SIGNAL).read().strip()
            os.remove(SIGNAL)
            log(f'📡 收到信号: {cmd}')

            if cmd == 'exit':
                log('👋 优雅关闭浏览器...')
                if conn and conn.browser:
                    try: await conn.browser.close()
                    except: pass
                break
            elif cmd in STEPS:
                await STEPS[cmd]()
            elif cmd == 'status':
                sig = await read_signature(page)
                report({'step':'status','signature':sig})
            else:
                log(f'⚠️ 未知命令: {cmd}')

        await asyncio.sleep(0.5)

    log('✅ 已退出')

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: log('👋 用户中断')
    except Exception as e:
        import traceback
        log(f'❌ 异常: {e}')
        log(traceback.format_exc())
