"""
login_state_machine.py — 登录状态机 v2.0

架构 (2026-06-20 重构):

  LoginStateMachine (编排器)
    ├─ PlatformDetector (策略模式, 按平台可插拔)
    │   ├─ DouyinDetector  — DOM 锚点 + 页面标题 + Cookie
    │   └─ XhsDetector     — DOM 锚点 + Cookie
    └─ RecoveryChain (可配置恢复链)
        ├─ CookieRecovery     — 刷新/导航 user/self
        ├─ SmsRecovery        — 内置短信 API 轮询 + 浏览器操作
        └─ VisualRecovery     — 截图 + 视觉分析上报

设计原则:
  1. PlatformDetector 可插拔 — 加新平台只加一个类
  2. RecoveryChain 顺序可配 — 每步是一个"子蓝图"
  3. LoginStateMachine 类名保持 — engine.py 无需修改
  4. 状态上报 — 每一步调用 log_func 回传状态到父流程
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path

log = logging.getLogger("login_state_machine")

# ════════════════════════════════════════════════════════════
# 1. PlatformDetector — 平台登录状态检测（策略模式）
# ════════════════════════════════════════════════════════════


class PlatformDetector(ABC):
    """平台检测器基类 — 每个平台一个子类"""

    @abstractmethod
    async def detect(self, page, account_id: str) -> str:
        """检测登录状态 → 'logged_in' / 'not_logged' / 'unknown'"""
        ...

    @abstractmethod
    async def check_verify(self, page) -> str:
        """检测验证弹窗 → 'none' / 'sms' / 'captcha'"""
        ...


class DouyinDetector(PlatformDetector):
    """抖音登录检测 + 验证弹窗检测"""

    # 已登录 DOM 锚点（严格匹配，只取最可靠的）
    LOGGED_IN_ANCHORS = [
        '.user-info-avatar',         # 个人主页上的头像
        '.user-header-avatar',        # 顶栏用户头像（仅登录后显示）
        '.user-info-wrap',            # 用户信息容器
    ]

    # 未登录 DOM 锚点（命中任一即未登录）
    NOT_LOGGED_ANCHORS = [
        '.login-button',
        '.login-panel',
        '.login-guide',
        '[class*="login-box"]',
        '[class*="login-tip"]',
        '[class*="float-login"]',
        '[class*="login-modal"]',
        # 通行登录浮层相关
        '[class*="user-login"]',
        '[class*="account-login"]',
        '[class*="unlogin"]',
        # 各种登录提示
        'div:has-text("登录后")',
    ]

    # 验证弹窗选择器
    VERIFY_PANEL_SEL = '.second-verify-panel'
    VERIFY_INPUT_SEL = '.uc-ui-verify_sms-verify_input'

    async def detect(self, page, account_id: str) -> str:
        """四重检测：DOM 锚点 → 页面文本 → 页面标题 → Cookie（仅辅助）"""
        # 1) DOM 锚点（最可靠 — 严格筛选以防误判）
        logged_in = await self._check_dom_anchors(page, self.LOGGED_IN_ANCHORS)
        if logged_in:
            return "logged_in"

        not_logged = await self._check_dom_anchors(page, self.NOT_LOGGED_ANCHORS)
        if not_logged:
            return "not_logged"

        # 2) 页面文本（次可靠 — 检查"未登录"关键词）
        try:
            text = (await page.evaluate("document.body.innerText")) or ""
            # 未登录信号：页面包含"未登录"或"登录后"
            if "未登录" in text or "登录后" in text:
                return "not_logged"
            # 已登录信号：页面包含"我的喜欢"和"粉丝"（登录后导航特有）
            if "粉丝" in text and "关注" in text:
                return "logged_in"
        except Exception:
            pass

        # 3) 页面标题（辅助）
        try:
            title = await page.title()
            if "的抖音" in title and "记录美好生活" not in title:
                return "logged_in"
            if "记录美好生活" in title:
                return "not_logged"
        except Exception:
            pass

        # 4) Cookie 仅日志（不用于决策）
        try:
            cookies = await page.context.cookies()
            for c in cookies:
                name = c.get("name", "").lower()
                if any(k in name for k in ["session", "token", "sid", "webid"]):
                    print(f"  [Cookie] '{c['name']}' 存在但无法判断有效性, 走恢复链")
                    break
        except Exception:
            pass

        return "unknown"

    async def check_verify(self, page) -> str:
        """检测抖音验证弹窗"""
        try:
            if await page.locator(self.VERIFY_PANEL_SEL).count() > 0:
                if await page.locator(self.VERIFY_INPUT_SEL).count() > 0:
                    return "sms"
                return "captcha"
        except Exception:
            pass
        return "none"

    async def _check_dom_anchors(self, page, anchors: list) -> bool:
        for sel in anchors:
            try:
                cnt = await page.locator(sel).count()
                if cnt > 0:
                    vis = await page.locator(sel).first.is_visible()
                    if vis:
                        return True
            except Exception:
                continue
        return False

    async def _check_session_cookie(self, page) -> bool:
        """检查 page context 是否有 session cookie"""
        try:
            cookies = await page.context.cookies()
            for c in cookies:
                name = c.get("name", "").lower()
                if any(k in name for k in ["session", "token", "sid", "webid"]):
                    return True
        except Exception:
            pass
        return False


class XhsDetector(PlatformDetector):
    """小红书登录检测 + 验证弹窗检测"""

    LOGGED_IN_ANCHORS = [
        ".user-avatar",
        ".reds-count",
        '[class*="user-icon"]',
    ]
    NOT_LOGGED_ANCHORS = [
        'input[placeholder*="手机"]',
        '.login-container',
        '.reds-modal-open',
    ]

    async def detect(self, page, account_id: str) -> str:
        logged_in = await self._check_dom_anchors(page, self.LOGGED_IN_ANCHORS)
        if logged_in:
            return "logged_in"

        # 登录面板可见 → 肯定没登录
        if await self._check_dom_anchors(page, self.NOT_LOGGED_ANCHORS):
            return "not_logged"

        # Cookie 仅日志（不用于决策！过期 cookie 会误导）
        try:
            cookies = await page.context.cookies()
            for c in cookies:
                name = c.get("name", "").lower()
                if any(k in name for k in ["session", "token", "sid"]):
                    log.info(f"  🍪 [{account_id}] cookie '{c['name']}' 存在但无法判断有效性, 继续走恢复链")
                    break
        except Exception:
            pass

        return "unknown"

    async def check_verify(self, page) -> str:
        try:
            if await page.locator(".r-captcha-modal").count() > 0:
                return "captcha"
            if await page.locator('input[placeholder*="验证码"]').count() > 0:
                return "sms"
        except Exception:
            pass
        return "none"

    async def _check_dom_anchors(self, page, anchors: list) -> bool:
        for sel in anchors:
            try:
                cnt = await page.locator(sel).count()
                if cnt > 0:
                    vis = await page.locator(sel).first.is_visible()
                    if vis:
                        return True
            except Exception:
                continue
        return False

    async def _check_session_cookie(self, page) -> bool:
        try:
            cookies = await page.context.cookies()
            for c in cookies:
                name = c.get("name", "").lower()
                if any(k in name for k in ["session", "token", "web_session"]):
                    return True
        except Exception:
            pass
        return False


# 检测器注册表 — 加新平台在这里加一行
DETECTORS = {
    "douyin": DouyinDetector(),
    "xiaohongshu": XhsDetector(),
}

# ════════════════════════════════════════════════════════════
# 2. RecoveryChain — 恢复策略链
# ════════════════════════════════════════════════════════════


class RecoveryStep(ABC):
    """恢复策略基类 — 每个恢复动作一个子类"""

    @abstractmethod
    async def run(self, page, platform: str, account_id: str,
                  log_func) -> bool:
        """执行恢复 → True=恢复成功"""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称（用于日志和状态显示）"""
        ...

    @property
    @abstractmethod
    def timeout(self) -> int:
        """超时秒数"""
        ...


class CookieRecovery(RecoveryStep):
    """Cookie 恢复 — 导航到 user/self 强制刷新登录态"""

    name = "Cookie 恢复"
    timeout = 40

    async def run(self, page, platform: str, account_id: str,
                  log_func) -> bool:
        target_name = "抖音" if platform != "xiaohongshu" else "小红书"
        log_func(f"  🔐 [{account_id}] Cookie恢复: 导航到{target_name}个人中心...")
        try:
            target = "https://www.douyin.com/user/self"
            if platform == "xiaohongshu":
                target = "https://www.xiaohongshu.com/explore"

            await page.goto(target, timeout=25000, wait_until="domcontentloaded")
            await asyncio.sleep(5)

            detector = DETECTORS.get(platform, DETECTORS["douyin"])
            status = await detector.detect(page, account_id)
            if status == "logged_in":
                log_func(f"  ✅ [{account_id}] Cookie恢复成功")
                return True
        except Exception as e:
            log_func(f"  ⚠️ Cookie恢复异常: {e}")

        return False


class SmsRecovery(RecoveryStep):
    """SMS 恢复 — 调用 sms_login 自动填手机+等验证码+登录（仅小红书）"""

    name = "SMS 重登"
    timeout = 90

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    async def run(self, page, platform: str, account_id: str,
                  log_func) -> bool:
        # 抖音由 DouyinLoginRecovery 处理
        if platform == "douyin":
            return False

        # 小红书：直接调用 xhs_login（6位验证码框专用版本）
        log_func(f"  📕 [{account_id}] 小红书SMS登录...")
        try:
            from matrix_modules.account.xhs_login import xhs_login
            ok = await xhs_login(page, account_name=account_id,
                                 log_func=log_func)
            if ok:
                # xhs_login 内部已验证登录成功，信任它
                log_func(f"  ✅ [{account_id}] 小红书登录成功")
                return True
            else:
                log_func(f"  ⚠️ xhs_login 返回 False")
        except Exception as e:
            log_func(f"  ❌ xhs_login 异常: {e}")
        return False


class VisualRecovery(RecoveryStep):
    """视觉分析恢复 — 截图 + AI 分析后上报（需人工介入）"""

    name = "视觉分析上报"
    timeout = 30

    async def run(self, page, platform: str, account_id: str,
                  log_func) -> bool:
        log_func(f"  📸 [{account_id}] 截图上报...")
        try:
            p = f"/tmp/login_fail_{account_id}.png"
            await page.screenshot(path=p)
            log_func(f"  📸 截图保存: {p}")

            try:
                from vision_bridge import analyze_screenshot
                result = await analyze_screenshot(p,
                    "What is on this page? Why can't the system log in?")
                log_func(f"  👁️ 视觉分析: {result[:200]}")
            except Exception:
                pass
        except Exception as e:
            log_func(f"  ⚠️ 截图失败: {e}")

        log_func(f"  ❌ [{account_id}] 需手动登录处理")
        return False  # 视觉分析不会自动恢复


class DouyinLoginRecovery(RecoveryStep):
    """抖音专用登录恢复 — 处理短期过期 + 全新登录两种场景

    流程:
      全新登录: 点击登录按钮 → 选手机号登录 → 填手机 → 获验证码 → 填码 → 登录
      短期过期: 检测到一键登录按钮 → 点击 → 等验证码 → 填码 → 登录
    """

    name = "抖音登录"
    timeout = 300  # 5分钟（含4分钟验证码轮询）

    # ── 通用选择器（不依赖特定 class）──
    LOGIN_BTN_TEXT = "登录"
    ONEKEY_TEXT = "一键登录"
    PHONE_INPUT = "input[placeholder*='手机']"  # 标准 input
    SMS_INPUT = "input[placeholder*='验证码']"  # 标准 input
    PHONE_PLACEHOLDER = "请输入手机号"           # 视觉确认的 placeholder
    SMS_PLACEHOLDER = "请输入验证码"             # 视觉确认的 placeholder
    PHONE_LOGIN_TEXT = "手机号登录"              # 切换到手机号登录
    GET_CODE_TEXT = "获取验证码"
    CONFIRM_TEXTS = ["确认登录", "登录", "确认", "提交", "验证", "立即登录", "下一步"]

    # 判断登录面板是否已弹出的文本特征
    PANEL_INDICATORS = ["获取验证码", "请输入验证码", "请输入手机号"]

    async def run(self, page, platform: str, account_id: str,
                  log_func) -> bool:
        if platform != "douyin":
            return False

        phone = self._get_phone(account_id)
        print(f"  [DouyinLoginRecovery] 手机号: {phone}")
        if not phone:
            print(f"  [DouyinLoginRecovery] ❌ 未找到手机号")
            return False

        # 1. 触发登录面板 — 点击"登录"按钮
        print(f"  [DouyinLoginRecovery] 触发登录面板...")

        panel_visible = await self._is_panel_visible(page)
        if panel_visible:
            print(f"  [DouyinLoginRecovery] 登录面板已自动弹出, 跳过点击登录")
        else:
            if not await self._trigger_login(page, log_func):
                print(f"  [DouyinLoginRecovery] ❌ 无法触发登录面板")
                return False
        await asyncio.sleep(2)

        # 快速检查：点击登录后是否已经登录（一键登录场景）
        logged_in = await self._check_logged_in_after_click(page)
        if logged_in:
            log_func(f"  ✅ [{account_id}] 点击登录后已自动登录（一键登录）")
            return True

        # 2. 检查是否需要切换到手机号登录（二维码默认可见）
        if await self._has_text(page, self.PHONE_LOGIN_TEXT):
            print(f"  [DouyinLoginRecovery] 切换到手机号登录...")
            await self._click_by_text(page, self.PHONE_LOGIN_TEXT, log_func)
            await asyncio.sleep(2)

        # 3. 判断场景：有一键登录 → 短期过期；否则全新登录
        has_onekey = await self._has_onekey(page)
        print(f"  [DouyinLoginRecovery] 一键登录={has_onekey}")

        if has_onekey:
            log_func(f"  🔑 [{account_id}] 短期过期, 点一键登录...")
            if not await self._click_by_text(page, self.ONEKEY_TEXT, log_func):
                return False
            await asyncio.sleep(3)
        else:
            log_func(f"  📱 [{account_id}] 全新登录, 准备发送验证码...")
            # 先确认手机号正确填入
            phone_ok = await self._ensure_phone(page, phone, log_func)
            if not phone_ok:
                log_func(f"  ❌ [{account_id}] 手机号未就绪")
                return False
            # 点获取验证码
            clicked = await self._click_by_text(page, self.GET_CODE_TEXT, log_func)
            if not clicked:
                log_func(f"  ⚠️ 未找到获取验证码按钮, 再试一次...")
                await asyncio.sleep(1)
                if not await self._click_by_text(page, self.GET_CODE_TEXT, log_func):
                    log_func(f"  ❌ 仍无法获取验证码")
                    return False

        # 3. 等待验证码输入框出现
        sms_ready = await self._wait_for_sms_input(page, log_func)
        if not sms_ready:
            return False

        # 4. 获取验证码
        code = await self._get_sms_code(page, phone, account_id, log_func)
        if not code:
            return False

        # 5. 填验证码（6位数字，可能自动提交）
        if not await self._fill_input(page, self.SMS_INPUT, code, log_func):
            return False
        await asyncio.sleep(3)

        # 6. 尝试提交
        await self._click_confirm(page, log_func)
        await asyncio.sleep(3)
        try:
            await page.keyboard.press("Enter")
        except:
            pass
        await asyncio.sleep(1)

        # 7. 验证 — 导航到 user/self 确认登录（最多2次）
        for attempt in range(2):
            try:
                await page.goto("https://www.douyin.com/user/self",
                                timeout=15000, wait_until="domcontentloaded")
                await asyncio.sleep(3)
            except:
                await asyncio.sleep(2)
            detector = DETECTORS.get("douyin")
            status = await detector.detect(page, account_id)
            if status == "logged_in":
                log_func(f"  ✅ [{account_id}] 抖音登录成功")
                return True
            log_func(f"  ⏳ 第{attempt+1}次验证未通过 (status={status})")

        log_func(f"  ❌ [{account_id}] 登录失败, 需手动处理")
        log_func(f"    可能原因: 验证码过期 / 网络延迟 / 需要滑块验证")
        return False

        log_func(f"  ⚠️ [{account_id}] 登录后状态仍为 {status}")
        # 不返回 False — 让后续恢复链（CookieRecovery）导航到 user/self 验证
        return False

    # ── 内部方法 ──────────────────────────────────────

    def _get_phone(self, account_id: str) -> str:
        """从 accounts.yaml 读手机号"""
        try:
            import yaml, os
            cfg = os.path.expanduser(
                '~/workbuddy-agent-os/agent-local/tools/matrix/config/accounts.yaml')
            with open(cfg) as f:
                data = yaml.safe_load(f)
            for a in data.get("accounts", []):
                if a.get("id") == account_id:
                    return a.get("phone", "")
        except Exception:
            pass
        return ""

    async def _trigger_login(self, page, log_func) -> bool:
        """触发登录：点击页面右上角的"登录"文字/按钮"""
        print(f"  [DouyinLoginRecovery] 查找「登录」按钮...")
        # 用 has-text 匹配（宽松匹配, 优先级高）
        for sel in [
            f'button:has-text("{self.LOGIN_BTN_TEXT}"):not(:has(button))',
            f'span:has-text("{self.LOGIN_BTN_TEXT}"):not(:has(span))',
            f'div:has-text("{self.LOGIN_BTN_TEXT}"):not(:has(div))',
            f'a:has-text("{self.LOGIN_BTN_TEXT}")',
            f'text="{self.LOGIN_BTN_TEXT}"',
        ]:
            try:
                cnt = await page.locator(sel).count()
                if cnt > 0:
                    vis = await page.locator(sel).first.is_visible()
                    if vis:
                        print(f"  [DouyinLoginRecovery] 点击「{sel}」")
                        await page.locator(sel).first.click(timeout=5000)
                        await asyncio.sleep(2)
                        return True
            except Exception as e:
                print(f"  [DouyinLoginRecovery] 尝试 {sel} 失败: {e}")
                continue

        # 兜底：用 JS 找任何包含"登录"文字的可见元素
        try:
            clicked = await page.evaluate(f"""() => {{
                var all = document.querySelectorAll('span, div, a, button, li');
                for (var i = 0; i < all.length; i++) {{
                    var txt = (all[i].textContent || '').trim();
                    if (txt.includes('{self.LOGIN_BTN_TEXT}') && all[i].offsetParent) {{
                        all[i].click();
                        return true;
                    }}
                }}
                return false;
            }}""")
            if clicked:
                print(f"  [DouyinLoginRecovery] JS点击登录成功")
                await asyncio.sleep(2)
                return True
        except Exception as e:
            print(f"  [DouyinLoginRecovery] JS点击失败: {e}")
        return False

    async def _has_onekey(self, page) -> bool:
        """检查是否有一键登录按钮"""
        try:
            cnt = await page.locator(f'text="{self.ONEKEY_TEXT}"').count()
            return cnt > 0
        except Exception:
            return False

    async def _click_by_text(self, page, text: str, log_func) -> bool:
        """按文本内容点击按钮 — CSS + JS 兜底"""
        log_func(f"  🖱️ 点击「{text}」...")
        for sel in [
            f'text="{text}"',
            f'button:has-text("{text}")',
            f'span:has-text("{text}")',
            f'div:has-text("{text}")',
        ]:
            try:
                cnt = await page.locator(sel).count()
                if cnt > 0:
                    vis = await page.locator(sel).first.is_visible()
                    if vis:
                        await page.locator(sel).first.click(timeout=5000)
                        return True
            except Exception:
                continue

        # JS 兜底：遍历所有可见元素找文本匹配
        try:
            clicked = await page.evaluate(f"""() => {{
                const all = document.querySelectorAll('button, span, div, a, label');
                for (const el of all) {{
                    if (!el.offsetParent) continue;
                    const txt = (el.textContent || '').trim();
                    if (txt.includes('{text}')) {{
                        el.click();
                        return true;
                    }}
                }}
                return false;
            }}""")
            if clicked:
                log_func(f"  ✅ JS点击「{text}」")
                return True
        except Exception:
            pass
        return False

    async def _has_phone_input(self, page) -> bool:
        """检测是否有手机号输入框（多种方式）"""
        for sel in [self.PHONE_INPUT, f'[placeholder*="{self.PHONE_PLACEHOLDER[:2]}"]']:
            try:
                if await page.locator(sel).count() > 0:
                    return True
            except:
                pass
        # JS 兜底：找包含"手机"文字的输入框
        return await self._find_input_by_placeholder(page, self.PHONE_PLACEHOLDER) is not None

    async def _has_sms_input(self, page) -> bool:
        """检测是否有验证码输入框"""
        for sel in [self.SMS_INPUT, f'[placeholder*="{self.SMS_PLACEHOLDER[:2]}"]']:
            try:
                if await page.locator(sel).count() > 0:
                    return True
            except:
                pass
        return await self._find_input_by_placeholder(page, self.SMS_PLACEHOLDER) is not None

    async def _find_input_by_placeholder(self, page, text: str) -> str:
        """通过 JS 查找包含指定 placeholder 文本的输入框, 返回选择器模式"""
        try:
            sel = await page.evaluate(f"""() => {{
                const els = document.querySelectorAll('input, [contenteditable], [role="textbox"]');
                for (const el of els) {{
                    const p = (el.placeholder || el.getAttribute('aria-label') || '').trim();
                    if (p.includes('{text[:2]}')) {{
                        // 返回类名或 ID 作为标识
                        if (el.id) return '#{{el.id}}';
                        if (typeof el.className === 'string' && el.className) {{
                            return '.{{el.className.split(/\\s+/)[0]}}';
                        }}
                        return 'input';
                    }}
                }}
                return '';
            }}""")
            return sel if sel else None
        except:
            return None

    async def _has_text(self, page, text: str) -> bool:
        """检查页面是否有指定文本"""
        try:
            cnt = await page.locator(f':has-text("{text}")').count()
            return cnt > 0
        except:
            return False

    async def _is_panel_visible(self, page) -> bool:
        """检查登录面板是否已经自动弹出"""
        for indicator in self.PANEL_INDICATORS:
            try:
                if await page.locator(f':has-text("{indicator}")').count() > 0:
                    return True
            except:
                pass
        return False

    async def _check_logged_in_after_click(self, page) -> bool:
        """点击登录后快速检查是否已自动登录"""
        try:
            await asyncio.sleep(2)
            detector = DETECTORS.get("douyin")
            status = await detector.detect(page, "")
            return status == "logged_in"
        except:
            return False

    async def _ensure_phone(self, page, phone: str, log_func) -> bool:
        """确认手机号已填入，否则重新填写"""
        # 用 JS 检查当前手机号输入框的值
        current_phone = ""
        try:
            current_phone = await page.evaluate(f"""() => {{
                const els = document.querySelectorAll('input, [contenteditable], [role="textbox"]');
                for (const el of els) {{
                    if (el.offsetParent === null) continue;
                    const val = (el.value || el.textContent || '').trim();
                    if (val.length >= 11 && /^1\\d{{10}}$/.test(val)) {{
                        return val;  // 找到已填入的手机号
                    }}
                }}
                return '';
            }}""")
        except:
            pass

        if current_phone == phone:
            log_func(f"  ✅ 手机号已正确填入: {phone}")
            return True

        log_func(f"  ⚠️ 手机号不对 (当前={current_phone}, 期望={phone}), 重新填写...")
        # 清空并重新填入
        ok = await self._fill_input(page, self.PHONE_INPUT, phone, log_func)
        if not ok:
            # JS 兜底：用 evaluate 强制填值
            try:
                filled = await page.evaluate(f"""() => {{
                    const els = document.querySelectorAll('input, [contenteditable], [role="textbox"]');
                    for (const el of els) {{
                        if (el.offsetParent === null) continue;
                        const p = (el.placeholder || '').trim();
                        if (p.includes('手机') || p.includes('号')) {{
                            el.focus();
                            el.value = '{phone}';
                            el.dispatchEvent(new Event('input', {{bubbles: true}}));
                            el.dispatchEvent(new Event('change', {{bubbles: true}}));
                            return true;
                        }}
                    }}
                    return false;
                }}""")
                if filled:
                    log_func(f"  ✏️ 手机号已填入 (JS): {phone}")
                    ok = True
            except Exception as e:
                log_func(f"  ❌ 填手机号失败: {e}")

        await asyncio.sleep(1)
        return ok

    async def _fill_input(self, page, selector: str, value: str,
                          log_func) -> bool:
        """填输入框 — CSS 选择器优先, JS 兜底"""
        # 先试标准 fill
        try:
            inp = page.locator(selector)
            if await inp.count() > 0:
                await inp.first.fill(value)
                log_func(f"  ✏️ 已填入 (CSS): {value}")
                return True
        except Exception:
            pass

        # JS 兜底：遍历所有可见输入框, 填第一个可见且无值的
        try:
            ok = await page.evaluate(f"""() => {{
                const els = document.querySelectorAll('input, [contenteditable], [role="textbox"]');
                for (const el of els) {{
                    if (el.offsetParent === null) continue;
                    if (el.value && el.value.length > 3) continue;  // 已有值
                    const p = (el.placeholder || '').trim();
                    const label = el.getAttribute('aria-label') || '';
                    // 只填手机号或通用输入框
                    el.focus();
                    el.value = '{value}';
                    el.dispatchEvent(new Event('input', {{bubbles: true}}));
                    el.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return true;
                }}
                return false;
            }}""")
            if ok:
                log_func(f"  ✏️ 已填入 (JS): {value[:4]}...")
                return True
        except Exception as e:
            log_func(f"  ❌ JS填值失败: {e}")
        return False

    async def _wait_for_sms_input(self, page, log_func) -> bool:
        """等待验证码输入框出现"""
        log_func(f"  ⏳ 等待验证码输入框...")
        for _ in range(30):  # 最长等 30 秒
            try:
                cnt = await page.locator(self.SMS_INPUT).count()
                if cnt > 0 and await page.locator(self.SMS_INPUT).first.is_visible():
                    log_func(f"  ✅ 验证码输入框已出现")
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
        log_func(f"  ❌ 验证码输入框未出现")
        return False

    async def _get_sms_code(self, page, phone: str, account_id: str,
                            log_func) -> str:
        """通过 SMS API 获取最新验证码 — 10秒轮询, 最长4分钟"""
        log_func(f"  📡 请求新验证码 ({phone})...")

        try:
            from matrix_modules.account.sms.api import ApiSMSHandler
            handler = ApiSMSHandler(phone=phone)

            # 获取当前最大ID，只接受比它大的新消息
            msgs = handler._fetch_messages()
            min_id = max((m.get("id", 0) for m in msgs), default=0)
            log_func(f"  ⏱️  轮询新消息 (ID > {min_id}), 每10秒, 最长4分钟")

            for attempt in range(24):  # 24次 × 10秒 = 4分钟
                await asyncio.sleep(10)
                msgs = handler._fetch_messages()
                if not msgs:
                    continue
                for m in msgs:
                    mid = m.get("id", 0)
                    if mid <= min_id:
                        continue
                    content = m.get("content", "")
                    code = handler._extract_code(content)
                    if code:
                        log_func(f"  ✅ 新验证码: {code} (ID={mid})")
                        return code
                elapsed = (attempt + 1) * 10
                if elapsed % 30 == 0:
                    log_func(f"  ⏳ 等待验证码... ({elapsed}s / 240s)")

            log_func(f"  ❌ 验证码获取超时 (4分钟)")
            return ""
        except Exception as e:
            log_func(f"  ❌ 获取验证码失败: {e}")
            return ""

    async def _click_confirm(self, page, log_func) -> bool:
        """点击真正的登录提交按钮"""
        log_func(f"  🔘 点击登录按钮...")

        # 策略0: 按唯一 ID 匹配（最可靠，大厂改ID时通过录制更新）
        try:
            has_id = await page.evaluate("() => { var b = document.querySelector('#douyin_login_comp_btn_id'); return b ? b.offsetParent ? 'visible' : 'hidden' : 'none'; }")
            if has_id == 'visible':
                await page.evaluate("() => document.querySelector('#douyin_login_comp_btn_id').click()")
                log_func(f"  ✅ 已点击登录按钮 (by ID)")
                return True
        except:
            pass
        
        # 策略1: Playwright 选择器（文本优先）
        texts = ["确认登录", "登录"]
        for attempt in range(2):
            for txt in texts:
                for sel in [
                    f'button:has-text("{txt}")',
                    f'div:has-text("{txt}")',
                    f'span:has-text("{txt}")',
                ]:
                    try:
                        btn = page.locator(sel)
                        if await btn.count() > 0:
                            await btn.last.click(timeout=5000)
                            log_func(f"  ✅ 已点击「{txt}」")
                            return True
                    except:
                        continue
            await asyncio.sleep(1)

        # 策略2: JS 找文本包含"确认登录"或"登录"的元素
        try:
            clicked = await page.evaluate("""() => {
                const targets = ['确认登录', '登录'];
                const all = document.querySelectorAll('button, div, span, a');
                for (const target of targets) {
                    for (const el of all) {
                        if (!el.offsetParent) continue;
                        const txt = (el.textContent || '').trim().replace(/\\s+/g, '');
                        if (txt === target) {
                            el.click();
                            return target;
                        }
                    }
                }
                return '';
            }""")
            if clicked:
                log_func(f"  ✅ JS点击「{clicked}」")
                return True
        except:
            pass
        return False


class RecoveryChain:
    """可配置的恢复链 — 按顺序执行恢复策略"""

    def __init__(self, steps: list = None):
        # 默认恢复顺序（抖音专用在前）
        self.steps = steps or [
            DouyinLoginRecovery(),    # 抖音专用：点击登录 + 填手机 + 验证码
            CookieRecovery(),         # 导航 user/self 刷新 cookie
            SmsRecovery(max_retries=2),  # 通用 SMS 恢复（小红书备用）
            VisualRecovery(),         # 截图上报
        ]

    async def run(self, page, platform: str, account_id: str,
                  log_func) -> bool:
        """执行恢复链, 任一成功返回 True"""
        for step in self.steps:
            # 小红书跳过抖音专用步骤
            if platform == "xiaohongshu" and isinstance(step, DouyinLoginRecovery):
                continue
            log_func(f"  ⏳ [{account_id}] → {step.name}")
            try:
                ok = await asyncio.wait_for(
                    step.run(page, platform, account_id, log_func),
                    timeout=step.timeout
                )
                if ok:
                    return True
            except asyncio.TimeoutError:
                log_func(f"  ⏰ [{account_id}] {step.name} 超时 ({step.timeout}s)")
            except Exception as e:
                log_func(f"  ⚠️ [{account_id}] {step.name} 异常: {e}")

        return False


# ════════════════════════════════════════════════════════════
# 3. LoginStateMachine — 编排器（类名保持兼容）
# ════════════════════════════════════════════════════════════

class LoginStateMachine:
    """
    登录状态机 — 编排检测 + 恢复链

    engine.py 用法（不变）:
      lsm = LoginStateMachine()
      ok = await lsm.ensure_login(page, account_id, platform)
      vt = await lsm.check_verify_dialog(page)
    """

    def __init__(self, recovery_chain: RecoveryChain = None):
        self._detectors = DETECTORS
        self._recovery = recovery_chain or RecoveryChain()
        self._last_status = "unknown"
        self._account_id = None
        self._platform = None

    # ── 公共入口 ──────────────────────────────────────────

    async def ensure_login(self, page, account_id: str,
                           platform: str = "douyin") -> bool:
        """确保登录，返回 True=已登录可用"""
        self._account_id = account_id
        self._platform = platform
        detector = self._detectors.get(platform, self._detectors["douyin"])

        # 1. 检测当前状态
        status = await detector.detect(page, account_id)
        if status == "logged_in":
            self._last_status = "logged_in"
            return True

        log.warning(f"  🔐 [{account_id}] 未登录 (status={status}), 恢复中...")

        # 2. 走恢复链
        ok = await self._recovery.run(page, platform, account_id, log.info)
        self._last_status = "logged_in" if ok else "failed"
        return ok

    async def check_verify_dialog(self, page) -> str:
        """检测执行中的验证弹窗 → 'none' / 'sms' / 'captcha'"""
        detector = self._detectors.get(self._platform, self._detectors["douyin"])
        return await detector.check_verify(page)

    async def recover_sms(self, page, account_id: str = None) -> bool:
        """公开的 SMS 恢复入口（engine.py 钩子2调用）"""
        aid = account_id or self._account_id
        sms = SmsRecovery(max_retries=2)
        ok = await sms.run(page, self._platform or "douyin", aid, log.info)
        if ok:
            self._last_status = "logged_in"
        return ok

    # ── 状态查询 ──────────────────────────────────────────

    @property
    def last_status(self) -> str:
        return self._last_status

    def get_detector(self, platform: str) -> PlatformDetector:
        """获取平台检测器（外部可配置）"""
        return self._detectors.get(platform, self._detectors["douyin"])

    def set_recovery_chain(self, chain: RecoveryChain):
        """替换恢复链（外部可配置顺序/超时）"""
        self._recovery = chain
