#!/usr/bin/env python3
"""
comment_sender.py v2 — 状态感知的评论发送器

流程（锚点驱动）:
1. 检测评论区是否打开 → 否则 KeyX
2. 检测输入框是否已激活 → 否则 JS focus
3. 检测是否有内容 → 否则键盘输入
4. Alt+Enter 发送
5. 验证码检测 → 手动输入
"""
import asyncio, os, random, sys, json
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(script_dir))
from cdp_connector import CDPConnector

LOG_FILE = '/tmp/comment_sender.log'
def log(m):
    with open(LOG_FILE, 'a') as f: f.write(m + '\n')
    print(m, flush=True)

async def check_state(page) -> dict:
    """检测评论区相关状态"""
    return await page.evaluate("""() => {
        const ae = document.activeElement;
        // 评论区面板
        const panel = document.querySelector('[class*="comment-header"]')
                   || document.querySelector('[class*="comment"]')
                   || document.querySelector('[class*="Comment"]');
        // Draft.js 编辑器
        const editor = document.querySelector('[contenteditable="true"][role="combobox"]')
                    || document.querySelector('[class*="DraftEditor"] [contenteditable]');
        // 输入框是否激活（activeElement 是编辑器或其子元素）
        const editorActive = ae && (ae.isContentEditable
            || ae.getAttribute('contenteditable') === 'true'
            || ae.closest('[contenteditable]'));
        return {
            has_comment_area: !!panel,
            has_editor: !!editor,
            editor_active: editorActive,
            active_tag: ae ? ae.tagName : 'none',
            active_cls: ae ? (ae.className||'').slice(0,50) : '',
            panel_rect: panel ? Object.values(panel.getBoundingClientRect()).map(Math.round) : null
        };
    }""")

async def focus_editor(page) -> bool:
    """尝试聚焦 Draft.js 编辑器，返回是否成功"""
    ok = await page.evaluate("""() => {
        // 直接找 contenteditable 且有 role 的
        let ed = document.querySelector('[contenteditable="true"][role="combobox"]');
        if (!ed) ed = document.querySelector('[class*="DraftEditor"] [contenteditable]');
        if (!ed) ed = document.querySelector('[contenteditable="true"]');
        if (ed) { ed.focus(); ed.click(); return true; }
        return false;
    }""")
    await asyncio.sleep(0.5)
    return ok

async def send_comment(page, comment_text: str):
    """发送一条评论（状态感知版）"""
    # ── Step 1: 检测并确保评论区打开 ──
    state = await check_state(page)
    log(f'📊 初始状态: comment={state["has_comment_area"]} editor={state["has_editor"]} active={state["editor_active"]}')

    if not state['has_comment_area']:
        log('⌨️ KeyX 打开评论区')
        await page.keyboard.press('KeyX')
        await asyncio.sleep(2)
    else:
        log('✅ 评论区已打开，跳过KeyX')

    # ── Step 2: 用真实鼠标点击激活输入框 ──
    state = await check_state(page)
    if state['editor_active']:
        log('✅ 输入框已激活')
    else:
        # 找到编辑器位置 → 用 Playwright 真实鼠标点击
        rect = await page.evaluate("""() => {
            let el = document.querySelector('[contenteditable="true"][role="combobox"]');
            if (!el) el = document.querySelector('[class*="DraftEditor"] [contenteditable]');
            if (!el) el = document.querySelector('[contenteditable="true"]');
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return {x: r.x, y: r.y, w: r.width, h: r.height};
        }""")
        if rect and rect['w'] > 0 and rect['h'] > 0:
            # 用 Playwright 生成真实鼠标事件链
            x = rect['x'] + rect['w'] // 2
            y = rect['y'] + rect['h'] // 2
            log(f'🖱️ 真实鼠标点击编辑器: ({x:.0f}, {y:.0f})')
            await page.mouse.click(x, y)
            await asyncio.sleep(1)
            # 再次确认
            state = await check_state(page)
            if state['editor_active']:
                log('✅ 鼠标点击后输入框已激活')
            else:
                log('⚠️ 鼠标点击后仍未激活')
        else:
            log('⚠️ 找不到编辑器位置')
            return 'failed'

    await asyncio.sleep(0.5)

    # ── Step 3: JS 设置内容（不用键盘，不依赖焦点）──
    log(f'💬 JS设置内容: "{comment_text}"')
    result = await page.evaluate(f'''() => {{
        // 找 Draft.js 编辑器
        let ed = document.querySelector('[contenteditable="true"][role="combobox"]');
        if (!ed) ed = document.querySelector('[class*="DraftEditor"] [contenteditable]');
        if (!ed) ed = document.querySelector('[contenteditable="true"]');

        if (!ed) return {{ok: false, reason: 'no_editor'}};

        // focus + 清空 + 设置内容
        ed.focus();
        ed.textContent = '';
        ed.textContent = "{comment_text}";
        ed.dispatchEvent(new Event('input', {{bubbles: true}}));
        ed.dispatchEvent(new Event('change', {{bubbles: true}}));

        const finalText = ed.textContent;
        return {{ok: finalText.length > 0, text: finalText, tag: ed.tagName}};
    }}''')
    log(f'  结果: ok={result["ok"]} text="{result.get("text","")}" tag={result.get("tag","")}')

    if not result.get('ok'):
        log('⚠️ JS设置内容失败')
        return 'failed'

    await asyncio.sleep(0.5)

    # ── Step 4: JS 触发发送（先找发送按钮，没有则 Alt+Enter）──
    log('⌨️ JS触发发送...')
    send_result = await page.evaluate('''() => {
        // 找发送按钮
        const btns = [...document.querySelectorAll('button')];
        const sendBtn = btns.find(b =>
            b.textContent.includes('发送') || b.textContent.includes('发布')
        );
        if (sendBtn) {
            sendBtn.click();
            return 'click_send_btn';
        }
        // 没按钮 → 触发 Alt+Enter
        const ed = document.querySelector('[contenteditable="true"][role="combobox"]')
                || document.querySelector('[contenteditable="true"]');
        if (ed) {
            ed.dispatchEvent(new KeyboardEvent('keydown', {
                key: 'Enter', altKey: true, bubbles: true
            }));
            return 'alt_enter_event';
        }
        return 'failed';
    }''')
    log(f'  发送方式: {send_result}')
    await asyncio.sleep(2)

    # ── Step 5: 验证码 ──
    has_code = await page.evaluate(
        "() => !!document.querySelector('input[placeholder*=\"\\u9a8c\\u8bc1\\u7801\"]')"
    )
    if has_code:
        log('⚠️ 验证码弹窗！')
        return 'verify_code_required'

    # ── Step 6: 验证发送结果 ──
    found = await page.evaluate(
        f'() => document.body.innerText.includes("{comment_text}")'
    )
    if found:
        log('✅ 评论已发送')
        return 'success'
    else:
        log('❌ 未在页面找到评论')
        return 'failed'


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--account', '-a', default='douyin_01')
    parser.add_argument('--comment', '-c', default='好内容，已三连')
    parser.add_argument('--count', '-n', type=int, default=2)
    args = parser.parse_args()

    ID_DIR = os.path.expanduser(
        f'~/workbuddy-agent-os/agent-local/tools/matrix/identities/{args.account}_camo'
    )
    if not os.path.exists(ID_DIR):
        print(f'❌ 账号目录不存在: {ID_DIR}')
        return

    print(f'🦊 启动: {args.account}')
    conn = CDPConnector(browser_type='camoufox', identity_dir=ID_DIR,
                        headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()
    await page.goto('https://www.douyin.com/', timeout=30000)
    await asyncio.sleep(3)

    print('\n📌 请操作:')
    print('   1. 进入视频播放页')
    print('   2. 打开评论区（按 X）')
    print('   3. 手动点击激活评论输入框')
    print('   4. 回到终端按回车\n')
    input()

    # 检查是否在播放页
    v = await page.evaluate('document.querySelectorAll("video").length')
    if v < 2:
        print('❌ 未检测到播放页')
        return
    print(f'✅ 播放页确认 (video={v})')

    for i in range(args.count):
        print(f'\n——— 第{i+1}/{args.count}次评论 ———')
        result = await send_comment(page, args.comment)

        if result == 'verify_code_required':
            code = input('\n📱 验证码(6位): ').strip()
            if code and len(code) == 6:
                await page.evaluate(f'''() => {{
                    const inp = document.querySelector('input[placeholder*="验证码"]');
                    if (inp) {{
                        inp.value = "{code}";
                        inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                    }}
                    const btn = [...document.querySelectorAll('button')]
                        .find(b => b.textContent.includes('确认') || b.textContent.includes('提交'));
                    if (btn) btn.click();
                }}''')
                print('✅ 验证码已提交')
                await asyncio.sleep(2)

        if i < args.count - 1:
            print('⏳ 评论区保持打开，5秒后下一次...')
            await asyncio.sleep(5)

    print('\n✅ 完成，浏览器保持打开')
    print('按 Ctrl+C 退出')
    while True:
        await asyncio.sleep(10)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n👋 退出')
    except Exception as e:
        import traceback; traceback.print_exc()
