"""
xhs_login.py — 小红书 SMS 验证码登录原子操作

对照 sms_login.py（抖音）模式，为小红书提供完整的原子操作。

注意：小红书登录面板不勾选协议（无法准确定位复选框），
改用下方「同意并登录」弹出浮窗方案。

2026-06-16 用户新发现（待 DOM 扫描验证）:
  填手机号 → 点「继续」(SMS发) → 等6个验证码框
  → 找「同意并登录」(可能是弹窗按钮配合「登录」按钮触发)
  → 收验证码 → 逐个填6个框

原子操作列表：(对标 sms_login.py)
  has_login_panel         ✅
  has_sms_inputs          ✅ (6个input[type=number])
  has_resend_btn          ✅ 新增
  has_agree_text          ✅ 检测"同意"文字（v2备用）
  is_logged_in            ✅
  fill_phone              ✅ (page.fill + Tab)
  click_continue          ✅ (点「继续」触发SMS)
  click_agree_and_login   ✅ (v3核心: 点「同意并登录」)
  click_agreement_checkbox  ✅ (v2备用)
  click_resend            ✅ (点「重新获取」)
  click_login_system      ✅ 新增 (系统级鼠标兜底)
  fill_6_digit_code       ✅ (6个 input 逐个填)
  click_largest_login_btn ✅ (按面积找最大)
  wait_login_panel        ✅
  wait_sms_inputs         ✅
  get_visible_texts       ✅ (调试)
  debug_snapshot_texts    ✅ (调试)

用法:
  from xhs_login import xhs_login, has_login_panel, click_continue, ...
"""
import asyncio, subprocess, time
from typing import Optional, List
from pathlib import Path

# ═══════════════════════════════════════════════
# 配置常量
# ═══════════════════════════════════════════════

PHONE_PLACEHOLDER = '输入手机号'
CONTINUE_TEXT = '继续'
AGREE_LOGIN_TEXT = '同意并继续'
LOGIN_BTN_TEXTS = ['登录', '登 录']
RESEND_TEXTS = ['重新获取', '重发', '重新发送']
LOGIN_INDICATORS = ['.user-avatar', '.reds-count']

# 窗口偏移（由 xiaohongshu_login.py 传入的一致性窗口定位）
# 用于系统级鼠标点击
WINDOW_OFFSET_X = 652
WINDOW_OFFSET_Y = 0


# ═══════════════════════════════════════════════
# 状态检测
# ═══════════════════════════════════════════════

async def has_login_panel(page) -> bool:
    """检测登录面板是否弹出（含手机号输入框）"""
    try:
        return await page.evaluate(
            '() => !!document.querySelector(\'input[placeholder*="手机"]\')'
        )
    except Exception:
        return False


async def has_sms_inputs(page) -> bool:
    """检测6个数字验证码框是否出现（小红书6位输入框）"""
    try:
        info = await page.evaluate(
            """() => {
                var a = document.querySelectorAll('input');
                var nums = [];
                for (var i=0; i<a.length; i++) {
                    if (a[i].type==='number' && a[i].offsetParent) {
                        nums.push(i);
                    }
                }
                return nums;
            }"""
        )
        return isinstance(info, list) and len(info) >= 6
    except Exception:
        return False


async def has_resend_btn(page) -> bool:
    """检测"重新获取"按钮是否出现（验证码超时可点）"""
    return await page.evaluate(
        f"""() => {{
            var texts = {_js_list(RESEND_TEXTS)};
            var all = document.querySelectorAll('span,div,button,a');
            for (var i=0; i<all.length; i++) {{
                if (!all[i].offsetParent) continue;
                var t = all[i].textContent.trim();
                for (var j=0; j<texts.length; j++) {{
                    if (t.includes(texts[j])) return true;
                }}
            }}
            return false;
        }}"""
    )


async def has_agree_text(page) -> bool:
    """检测页面上是否有包含"同意"的文字（v2备用）"""
    try:
        return await page.evaluate(
            """() => {
                var s = document.querySelectorAll('span,div,label');
                for (var i=0; i<s.length; i++) {
                    var t = (s[i].textContent||'').trim();
                    if (t.includes('同意') && !t.includes('扫码') && s[i].offsetParent) {
                        return true;
                    }
                }
                return false;
            }"""
        )
    except Exception:
        return False


async def is_logged_in(page) -> bool:
    """检测小红书是否已登录（严格模式）"""
    try:
        # 登录面板可见 → 肯定没登录
        if await has_login_panel(page):
            return False
        return await page.evaluate("""() => {
            // 查用户头像 — 只在顶栏区域（不是 feed 里的创作者头像）
            const topAvatars = document.querySelectorAll(
                '.reds-count, [class*="reds-user"], ' +
                '[class*="user-sidebar"], .side-bar [class*="avatar"], ' +
                '[class*="user-info"] [class*="avatar"]'
            );
            if (topAvatars.length > 0) return true;

            // 兜底：找整体登录指示元素
            const indicators = document.querySelectorAll(
                '[class*="user-center"], [class*="user-profile"], ' +
                '[class*="my-info"], [data-testid*="user"]'
            );
            return indicators.length > 0;
        }""")
    except Exception:
        return False


# ═══════════════════════════════════════════════
# 操作函数
# ═══════════════════════════════════════════════

async def fill_phone(page, phone: str):
    """填入手机号 — 必须用 page.fill + Tab（React 框架不认 JS set value）"""
    try:
        inp = page.locator('input[placeholder*="手机"]')
        await inp.fill(phone)
        await page.keyboard.press("Tab")
    except Exception:
        # 兜底：按字符逐个输入
        await page.type('input[placeholder*="手机"]', phone, delay=30)
        await page.keyboard.press("Tab")


async def click_continue(page) -> bool:
    """点「继续」按钮（触发SMS发送）"""
    # 先检查是否有 oauth-tip（切换登录方式），有则先点它
    try:
        oauth = page.locator('div.oauth-tip')
        if await oauth.count() > 0 and await oauth.first.is_visible():
            await oauth.first.click()
            await asyncio.sleep(1)
    except:
        pass

    clicked = await page.evaluate(
        f"""() => {{
            var all = document.querySelectorAll('span,div,button');
            for (var i=0; i<all.length; i++) {{
                if (all[i].textContent.trim() === '{CONTINUE_TEXT}' && all[i].offsetParent) {{
                    all[i].click();
                    return 'OK';
                }}
            }}
            return 'NOT_FOUND';
        }}"""
    )
    return clicked == 'OK'


async def click_agree_and_login(page) -> bool:
    """
    点「同意并继续」按钮（先点登录后弹出的浮层按钮）
    先试 .foot-btn CSS 选择器，再搜文本
    """
    # 先试 CSS 选择器
    try:
        fb = page.locator('div.foot-btn')
        cnt = await fb.count()
        if cnt > 0 and await fb.first.is_visible():
            await fb.first.click()
            return True
    except:
        pass

    # 再搜文本（找 z-index 最高的可见元素）
    for _ in range(6):
        clicked = await page.evaluate(
            f"""() => {{
                var all = document.querySelectorAll('span,div,button');
                var found = null, maxZ = 0;
                for (var i=0; i<all.length; i++) {{
                    if (!all[i].offsetParent) continue;
                    var t = all[i].textContent.trim();
                    if (t.includes('同意并继续') || t.includes('同意并登录')) {{
                        var z = parseInt(window.getComputedStyle(all[i]).zIndex) || 0;
                        if (z > maxZ) {{ maxZ = z; found = all[i]; }}
                    }}
                }}
                if (found) {{ found.click(); return true; }}
                return false;
            }}"""
        )
        if clicked:
            return True
        await asyncio.sleep(1)
    return False


async def click_agreement_checkbox(page) -> bool:
    """
    (备用 v2) 鼠标点击"同意"文字左侧20px位置勾协议
    
    注意：小红书复选框是自定义元素，非原生 input[type=checkbox]，
    left-20px 定位极不可靠。仅作 v3 方案的兜底。
    """
    pos = await _get_agreement_element(page)
    if not pos:
        return False
    click_x = max(0, pos["x"] - 20)
    await page.mouse.click(click_x, pos["y"])
    return True


async def click_resend(page) -> bool:
    """点「重新获取」按钮（验证码超时后重发）"""
    clicked = await page.evaluate(
        f"""() => {{
            var texts = {_js_list(RESEND_TEXTS)};
            var all = document.querySelectorAll('span,div,button,a');
            for (var i=0; i<all.length; i++) {{
                if (!all[i].offsetParent) continue;
                var t = all[i].textContent.trim();
                for (var j=0; j<texts.length; j++) {{
                    if (t.includes(texts[j])) {{
                        all[i].click();
                        return true;
                    }}
                }}
            }}
            return false;
        }}"""
    )
    await asyncio.sleep(1)
    return clicked


async def fill_6_digit_code(page, code: str, log_func=print) -> bool:
    """
    逐个填入6位验证码

    策略：先一次 evaluate 捕获所有 input[type=number] 的 DOM 索引，
    再按索引逐个填入，防止 DOM 在迭代中变动。
    """
    indices = await page.evaluate(
        """() => {
            var a = document.querySelectorAll('input');
            var r = [];
            for (var j=0; j<a.length; j++) {
                if (a[j].type==='number' && a[j].offsetParent) {
                    r.push(j);
                    if (r.length >= 6) break;
                }
            }
            return r;
        }"""
    )
    log_func(f"  验证码框 DOM 索引: {indices}")

    for idx, digit in enumerate(code[:6]):
        if idx >= len(indices):
            break
        ok = await page.evaluate(
            f"""() => {{
                var all = document.querySelectorAll('input');
                var inp = all[{indices[idx]}];
                if (!inp) return 0;
                inp.focus();
                // 模仿手动输入
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                nativeInputValueSetter.call(inp, '{digit}');
                inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                return 1;
            }}"""
        )
        log_func(f"  第{idx+1}位: {digit} -> {'OK' if ok else 'FAIL'}")
        await asyncio.sleep(0.2)

    return True


async def click_largest_login_btn(page, log_func=print) -> bool:
    """按面积找最大的「登录」按钮（排除导航栏）"""
    btns = await _get_login_buttons(page)
    if not btns:
        log_func("  ⚠️ 无登录按钮")
        return False
    target = btns[0]
    await page.mouse.click(target["x"], target["y"])
    log_func(f"  ✅ 点登录 ({target['x']},{target['y']}) {target['w']}x{target['h']}")
    return True


async def click_login_system(page, log_func=print) -> bool:
    """
    系统级鼠标点登录按钮（DOM 点击失败时兜底）
    使用 osascript 在系统层模拟点击，绕过网页 JS 限制
    """
    btns = await _get_login_buttons(page)
    if not btns:
        return False
    target = btns[0]
    sx = WINDOW_OFFSET_X + target["x"]
    sy = WINDOW_OFFSET_Y + target["y"]
    log_func(f"  🔧 系统级鼠标点击 ({sx},{sy})")
    subprocess.run(
        ['osascript', '-e',
         f'tell application "System Events" to click at {{{sx},{sy}}}'],
        timeout=5
    )
    time.sleep(0.5)
    return True


async def wait_login_panel(page, timeout_sec: int = 30) -> bool:
    """等待登录面板弹出（含手机号输入框）"""
    for _ in range(timeout_sec):
        if await has_login_panel(page):
            return True
        await asyncio.sleep(1)
    return False


async def wait_sms_inputs(page, timeout_sec: int = 40) -> bool:
    """等待6个验证码输入框出现"""
    for _ in range(timeout_sec):
        if await has_sms_inputs(page):
            return True
        await asyncio.sleep(1)
    return False


# ═══════════════════════════════════════════════
# 调试辅助
# ═══════════════════════════════════════════════

async def get_visible_texts(page, limit: int = 15) -> list:
    """获取页面上所有可见文字（调试用）"""
    try:
        return await page.evaluate(
            f"""() => {{
                var a = document.querySelectorAll('span,div,button');
                var r = [];
                for (var i=0; i<a.length; i++) {{
                    if (!a[i].offsetParent) continue;
                    var t = a[i].textContent.trim();
                    if (t) r.push(t);
                    if (r.length >= {limit}) break;
                }}
                return r;
            }}"""
        )
    except Exception:
        return []


async def debug_snapshot_texts(page, log_func=print):
    """快照当前页面: URL + 可见文字（调试用）"""
    try:
        url = await page.evaluate('window.location.href')
        texts = await get_visible_texts(page)
        log_func(f"  URL: {url}")
        log_func(f"  可见文字: {texts}")
    except Exception:
        pass


# ═══════════════════════════════════════════════
# 私有辅助
# ═══════════════════════════════════════════════

def _js_list(items: list) -> str:
    """生成 JS 数组字面量字符串，正确处理引号"""
    quoted = [f"'{x}'" for x in items]
    return "[" + ",".join(quoted) + "]"


async def _get_agreement_element(page) -> Optional[dict]:
    """找最小高度（最内层）包含"同意"的可见元素"""
    try:
        result = await page.evaluate(
            """() => {
                var s = document.querySelectorAll('span,div,label');
                var best = null;
                for (var i=0; i<s.length; i++) {
                    var t = (s[i].textContent||'').trim();
                    if (t.includes('同意') && !t.includes('扫码') && s[i].offsetParent) {
                        var b = s[i].getBoundingClientRect();
                        if (!best || b.height < best.h) {
                            best = {
                                x: Math.round(b.left),
                                y: Math.round(b.top + b.height/2),
                                h: b.height,
                                text: t.slice(0,20)
                            };
                        }
                    }
                }
                return best ? JSON.stringify(best) : null;
            }"""
        )
        if result:
            import json as _j
            return _j.loads(result)
    except Exception:
        pass
    return None


async def _get_login_buttons(page) -> list:
    """获取所有可见「登录」按钮信息（按面积降序）"""
    try:
        result = await page.evaluate(
            f"""() => {{
                var all = document.querySelectorAll('span,div,button');
                var r = [];
                for (var i=0; i<all.length; i++) {{
                    if (!all[i].offsetParent) continue;
                    var t = all[i].textContent.trim();
                    for (var j=0; j<{_js_list(LOGIN_BTN_TEXTS)}.length; j++) {{
                        if (t === {_js_list(LOGIN_BTN_TEXTS)}[j]) {{
                            var b = all[i].getBoundingClientRect();
                            r.push({{
                                x: Math.round(b.left + b.width/2),
                                y: Math.round(b.top + b.height/2),
                                w: Math.round(b.width),
                                h: Math.round(b.height)
                            }});
                        }}
                    }}
                }}
                r.sort(function(a,b){{return (b.w*b.h) - (a.w*a.h);}});
                return JSON.stringify(r);
            }}"""
        )
        import json as _j
        return _j.loads(result)
    except Exception:
        return []


# ═══════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════

async def _lookup_phone(account_name: str) -> str:
    """从 accounts.override.yaml 查找手机号"""
    import yaml, os
    home = os.path.expanduser('~')
    base = home + '/workbuddy-agent-os/agent-local/tools/matrix/config'
    for name in ['accounts.override.yaml', 'accounts.yaml']:
        path = base + '/' + name
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            for a in data.get('accounts', []):
                if a.get('id') == account_name:
                    phone = a.get('phone', '')
                    if phone:
                        return phone
        except Exception:
            pass
    return ''


async def xhs_login(page, phone: str = '', account_name: str = '',
                    log_func=print) -> bool:
    """小红书 SMS 验证码登录完整流程

    Args:
        page: Playwright page 对象
        phone: 手机号（可选，空则从 accounts.yaml 查）
        account_name: 账号 ID（用于日志/查手机号）
        log_func: 日志输出函数

    Returns:
        True=登录成功, False=失败
    """
    # ── 获取手机号 ──
    if not phone and account_name:
        phone = await _lookup_phone(account_name)
    log_func(f'📞 手机号: {phone or "未指定"} ({account_name})')

    # ── 检测已登录 ──
    if await is_logged_in(page):
        log_func('✅ 已登录，跳过')
        return True

    # ── Step 1: 等登录面板 ──
    if not await wait_login_panel(page):
        log_func('❌ 登录面板未弹出')
        return False
    log_func('✅ 登录面板已弹出')

    # ── Step 2: 填手机号 ──
    if phone:
        log_func(f'📱 Step 2: 填手机号 {phone}')
        await fill_phone(page, phone)
        await asyncio.sleep(1.5)

    # ── 创建 SMS handler + 记录当前时间（点继续之前，用于时间过滤）──
    import time
    from matrix_modules.account.sms.api import ApiSMSHandler
    handler = ApiSMSHandler(phone=phone) if phone and phone.strip() else ApiSMSHandler()
    handler.poll_interval = 5
    sms_after_time = time.time()
    log_func(f'  📡 记录时间戳 {time.strftime("%H:%M:%S")}，只接受之后的验证码')

    # ── Step 3: 点继续（触发 SMS）──
    log_func('👉 Step 3: 点继续')
    if not await click_continue(page):
        log_func('⚠️ 未找到继续按钮，重试...')
        await asyncio.sleep(2)
        await click_continue(page)
    await asyncio.sleep(3)

    # 调试快照
    await debug_snapshot_texts(page, log_func)

    # ── Step 4: 等6个验证码框 ──
    log_func('⏳ Step 4: 等6个验证码框...')
    if not await wait_sms_inputs(page):
        log_func('❌ 验证码框未出现')
        return False
    log_func('✅ 验证码框已出现')

    code = ''
    for attempt in range(2):  # 最多2次（第3次封禁3分钟）
        code = await handler.wait(f'小红书 {account_name}', timeout=180, after_time=sms_after_time)
        if code and len(code) in (4, 5, 6):
            log_func(f'✅ 验证码: {code}')
            break

        log_func(f'⏰ 第{attempt+1}次超时，等待180秒后点重新获取...')
        # 等180秒倒计时 → 点重新获取
        for _ in range(180):
            if await click_resend(page):
                log_func('  ✅ 已点"重新获取"')
                break
            await asyncio.sleep(1)
        else:
            log_func('  ⚠️ 未找到"重新获取"按钮')
    else:
        log_func('❌ 验证码获取失败')
        return False

    if not code or len(code) not in (4, 5, 6):
        return False

    # ── Step 6: 填6位验证码 ──
    log_func(f'📝 Step 6: 填验证码 {code}')
    await fill_6_digit_code(page, code[:6], log_func)
    await asyncio.sleep(0.5)

    # ── Step 7: 点「登录」按钮（触发「同意并登录」浮层）──
    #   先点登录，会弹出「同意并登录」浮动层，然后再点它
    log_func('🔘 Step 7: 点击登录')
    ok = await click_largest_login_btn(page, log_func)
    if not ok:
        log_func('  ⚠️ DOM 点击失败，尝试系统级鼠标点击')
        ok = await click_login_system(page, log_func)
    await asyncio.sleep(2)

    # ── Step 8: 点「同意并继续」（登录后弹出的浮层）──
    #   等浮层出现（最多5秒），点击后即完成登录
    log_func('📄 Step 8: 同意并继续')
    await asyncio.sleep(0.5)
    v3_ok = await click_agree_and_login(page)
    if v3_ok:
        log_func('  ✅ 已点「同意并登录」')
    else:
        log_func('  ⚠️ 未找到"同意并继续"按钮，尝试继续...')

    await asyncio.sleep(3)

    # ── Step 9: 验证登录 ──
    if await is_logged_in(page):
        log_func('🎉 登录成功！')
        return True

    # 再试一次（可能页面跳转慢）
    log_func('⏳ 等待登录完成...')
    for _ in range(5):
        await asyncio.sleep(2)
        if await is_logged_in(page):
            log_func('🎉 登录成功！')
            return True
    else:
        log_func('⚠️ 登录可能未完成，需检查页面状态')
        return False
