"""
sms_login.py — SMS 验证码登录原子操作

流程：
  1. 检测登录面板 → 点"一键登录" → 触发短信
  2. ApiSMSHandler 轮询获取验证码
  3. 填入验证码 → 点确认 → 登录成功

支持：超时重新发送、系统级鼠标兜底
"""
import asyncio, time, subprocess
from typing import Optional

# ═══════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════

SMS_INPUT_SELECTOR = 'input[placeholder*="验证码"]'
LOGIN_PANEL_ID = '#login-panel-new'
ONEKEY_TEXT = '一键登录'
CONFIRM_BTN_TEXTS = ['确认', '提交', '验证', '登录']
RESEND_TEXTS = ['重新发送', '获取验证码', '重发']

# ═══════════════════════════════════════════════
# 状态检测
# ═══════════════════════════════════════════════

async def has_login_panel(page) -> bool:
    return await page.evaluate(f'() => !!document.querySelector("{LOGIN_PANEL_ID}")')

async def has_sms_input(page) -> bool:
    return await page.evaluate(f'() => !!document.querySelector("{SMS_INPUT_SELECTOR}")')

async def has_resend_btn(page) -> bool:
    """检测"重新发送"按钮是否出现（超时可点击）"""
    return await page.evaluate(f"""() => {{
        var texts = {RESEND_TEXTS};
        var all = document.querySelectorAll('button, span, div, a');
        for (var i = 0; i < all.length; i++) {{
            for (var t = 0; t < texts.length; t++) {{
                if (all[i].textContent.includes(texts[t]) && all[i].offsetParent) return true;
            }}
        }}
        return false;
    }}""")

async def is_logged_in(page) -> bool:
    """检测登录成功（面板消失+有头像）"""
    return not await has_login_panel(page) and await page.evaluate('() => !!document.querySelector("[data-e2e=user-avatar]")')

# ═══════════════════════════════════════════════
# 操作函数
# ═══════════════════════════════════════════════

async def click_onekey_login(page):
    """点"一键登录"按钮"""
    await page.evaluate(f"""() => {{
        var all = document.querySelectorAll('span, div, a, button');
        for (var i = 0; i < all.length; i++) {{
            if (all[i].textContent.trim() === '{ONEKEY_TEXT}') {{ all[i].click(); return true; }}
        }}
        return false;
    }}""")
    await asyncio.sleep(3)

async def click_resend(page):
    """点"重新发送"按钮（超时后）"""
    clicked = await page.evaluate(f"""() => {{
        var texts = {RESEND_TEXTS};
        var all = document.querySelectorAll('button, span, div, a');
        for (var i = 0; i < all.length; i++) {{
            if (!all[i].offsetParent) continue;
            for (var t = 0; t < texts.length; t++) {{
                if (all[i].textContent.includes(texts[t])) {{ all[i].click(); return true; }}
            }}
        }}
        return false;
    }}""")
    await asyncio.sleep(1)
    return clicked

async def fill_code(page, code: str):
    """填入验证码"""
    await page.evaluate(f"""() => {{
        var inp = document.querySelector('{SMS_INPUT_SELECTOR}');
        if (!inp) return;
        inp.value = '{code}';
        inp.dispatchEvent(new Event('input', {{bubbles: true}}));
    }}""")
    await asyncio.sleep(0.5)

async def click_confirm(page):
    """点确认/提交按钮"""
    return await page.evaluate(f"""() => {{
        var texts = {CONFIRM_BTN_TEXTS};
        var all = document.querySelectorAll('button, span, div, a');
        for (var i = 0; i < all.length; i++) {{
            if (!all[i].offsetParent) continue;
            for (var t = 0; t < texts.length; t++) {{
                if (all[i].textContent.includes(texts[t])) {{ all[i].click(); return true; }}
            }}
        }}
        return false;
    }}""")

async def click_confirm_system(page):
    """系统级鼠标点确认按钮（兜底）"""
    btn_info = await page.evaluate(f"""() => {{
        var texts = {CONFIRM_BTN_TEXTS};
        var all = document.querySelectorAll('button, span, div, a');
        for (var i = 0; i < all.length; i++) {{
            if (!all[i].offsetParent) continue;
            for (var t = 0; t < texts.length; t++) {{
                if (all[i].textContent.includes(texts[t])) {{
                    var r = all[i].getBoundingClientRect();
                    return {{x: Math.round(r.left+r.width/2), y: Math.round(r.top+r.height/2)}};
                }}
            }}
        }}
        return null;
    }}""")
    if btn_info:
        # 窗口位置 (652, 0)，视口起始 = 窗口起始
        sx, sy = 652 + btn_info['x'], btn_info['y']
        subprocess.run(['osascript','-e',f'tell application "System Events" to click at {{{sx},{sy}}}'], timeout=5)
        time.sleep(0.5)
        return True
    return False

# ═══════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════

async def sms_login(page, log_func=print) -> bool:
    """SMS 验证码登录完整流程

    Args:
        page: Playwright page
        log_func: 日志函数

    Returns:
        True=登录成功, False=失败
    """
    if await is_logged_in(page):
        log_func('✅ 已登录，跳过')
        return True

    if not await has_login_panel(page):
        log_func('❌ 未检测到登录面板')
        return False

    # ── Step 1: 点一键登录 ──
    log_func('📱 Step 1: 点击一键登录')
    await click_onekey_login(page)

    if not await has_sms_input(page):
        log_func('❌ 未弹出验证码输入框')
        return False
    log_func('✅ 验证码输入框已出现')

    # ── Step 2: 轮询获取验证码（含超时重发）──
    log_func('📡 Step 2: 获取验证码')
    from matrix_modules.account.sms import ApiSMSHandler
    handler = ApiSMSHandler()

    code = ''
    for attempt in range(3):  # 最多3次获取尝试
        code = await handler.wait('抖音登录', timeout=60)
        if code and len(code) in (4, 5, 6):
            log_func(f'✅ 获取到验证码: {code}')
            break

        log_func(f'⏰ 第{attempt+1}次超时，点重新发送...')
        await click_resend(page)
        await asyncio.sleep(2)

    if not code or len(code) not in (4, 5, 6):
        log_func('❌ 获取验证码失败')
        return False

    # ── Step 3: 填入验证码 ──
    log_func(f'📝 Step 3: 填入验证码 {code}')
    await fill_code(page, code)
    await asyncio.sleep(0.5)

    # ── Step 4: 点确认 ──
    log_func('🔘 Step 4: 点击确认')
    ok = await click_confirm(page)
    if not ok:
        log_func('⚠️ DOM点击失败，用系统级鼠标')
        ok = await click_confirm_system(page)
    await asyncio.sleep(2)

    # ── Step 5: 验证登录 ──
    if await is_logged_in(page):
        log_func('🎉 登录成功！')
        return True
    else:
        log_func('⚠️ 登录可能未完成，检查页面状态')
        return False
