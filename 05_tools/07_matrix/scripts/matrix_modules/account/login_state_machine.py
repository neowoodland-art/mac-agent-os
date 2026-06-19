"""
login_state_machine.py — 登录状态机 v1.0

职责:
  1. 检测当前登录状态 (DOM锚点 + Cookie)
  2. 如果未登录，按链恢复: Cookie刷新 → SMS重登 → 视觉分析 → 上报
  3. 返回 bool (是否已登录)

依赖:
  - sms_login.py: is_logged_in(), sms_login() — 通用SMS检测
  - xhs_login.py: is_logged_in(), xhs_login() — 小红书专用
  - douyin_ops.py: is_verify_shown() — 抖音验证弹窗检测
  - vision_bridge.py: 截图视觉分析（降级）

用法:
  lsm = LoginStateMachine()
  ok = await lsm.ensure_login(page, account_id="xhs_01", platform="xiaohongshu")
  if not ok:
      # 上报用户手动处理
"""

import asyncio
import logging
from pathlib import Path

log = logging.getLogger("login_state_machine")

# ── 每平台登录锚点 ──────────────────────────────────────────
LOGIN_ANCHORS = {
    "xiaohongshu": {
        "logged_in":  [".user-avatar", ".reds-count", '[class*="user-icon"]'],
        "not_logged": ['input[placeholder*="手机"]', '.login-container'],
    },
    "douyin": {
        "logged_in":  ['[data-e2e="user-avatar"]', '.user-info-avatar'],
        "not_logged": ['.login-button', '[class*="login"]'],
    },
}


# ════════════════════════════════════════════════════════════
# LoginStateMachine
# ════════════════════════════════════════════════════════════

class LoginStateMachine:
    """登录状态机 — 检测 + 恢复"""

    def __init__(self):
        self._last_status = "unknown"   # unknown / logged_in / failed
        self._retry_count = 0
        self.max_retries = 2

    # ── 公共入口 ──────────────────────────────────────────

    async def ensure_login(self, page, account_id: str,
                           platform: str = "douyin") -> bool:
        """确保登录，返回 True=已登录可用"""

        self._account_id = account_id
        self._platform = platform

        # 1. 检测当前状态
        status = await self._detect(page)
        if status == "logged_in":
            self._last_status = "logged_in"
            self._retry_count = 0
            return True

        log.warning(f"  🔐 [{account_id}] 未登录 (status={status}), 尝试恢复...")

        # 2. 恢复链: Cookie → SMS → 视觉 → 上报
        if await self._recover_cookie(page):
            self._last_status = "logged_in"
            return True

        if await self._recover_sms(page, account_id):
            self._last_status = "logged_in"
            return True

        # 3. 视觉分析
        await self._report_unknown(page, account_id)
        self._last_status = "failed"
        return False

    # ── 状态检测 ──────────────────────────────────────────

    async def _detect(self, page) -> str:
        """检测登录状态 → 'logged_in' / 'not_logged' / 'unknown'"""
        anchors = LOGIN_ANCHORS.get(self._platform, LOGIN_ANCHORS["douyin"])

        # 已登录锚点: 命中任一即认为已登录
        for sel in anchors["logged_in"]:
            try:
                count = await page.locator(sel).count()
                if count > 0:
                    visible = await page.locator(sel).first.is_visible()
                    if visible:
                        return "logged_in"
            except Exception:
                continue

        # 未登录锚点: 命中任一即认为未登录
        for sel in anchors["not_logged"]:
            try:
                count = await page.locator(sel).count()
                if count > 0:
                    visible = await page.locator(sel).first.is_visible()
                    if visible:
                        return "not_logged"
            except Exception:
                continue

        # 无法判断
        return "unknown"

    # ── 恢复链 ──────────────────────────────────────────

    async def _recover_cookie(self, page) -> bool:
        """刷新页面让已有 cookie 生效"""
        log.info(f"  🔐 [{self._account_id}] Cookie恢复: 刷新页面...")

        try:
            current_url = page.url
            # 重新加载
            await page.goto(current_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(5)

            status = await self._detect(page)
            if status == "logged_in":
                log.info(f"  ✅ [{self._account_id}] Cookie恢复成功")
                return True
        except Exception as e:
            log.warning(f"  ⚠️ Cookie恢复: {e}")

        return False

    async def _recover_sms(self, page, account_id: str) -> bool:
        """SMS 验证码登录 — 复用现有 sms_login.py"""
        log.info(f"  📱 [{account_id}] SMS重登...")

        try:
            from matrix_modules.account.sms_login import sms_login
            # sms_login 会处理填手机 → 等验证码 → 填码 → 点同意
            ok = await sms_login(page, account_name=account_id, log_func=log.info)
            if ok:
                await asyncio.sleep(3)
                status = await self._detect(page)
                if status == "logged_in":
                    log.info(f"  ✅ [{account_id}] SMS登录成功")
                    return True
                log.warning(f"  ⚠️ SMS登录后检测到状态仍为 {status}")
            else:
                log.warning(f"  ⚠️ sms_login 返回 False")
        except ImportError:
            log.warning(f"  ⚠️ sms_login 不可用，尝试 xhs_login...")
            try:
                from matrix_modules.account.xhs_login import xhs_login
                ok = await xhs_login(page, account_id=account_id, log_func=log.info)
                if ok:
                    status = await self._detect(page)
                    return status == "logged_in"
            except ImportError:
                log.warning(f"  ⚠️ xhs_login 也不可用")
        except Exception as e:
            log.warning(f"  ⚠️ SMS登录异常: {e}")

        self._retry_count += 1
        if self._retry_count < self.max_retries:
            log.info(f"  🔄 第{self._retry_count}次失败，重试...")
            await asyncio.sleep(3)
            return await self._recover_sms(page, account_id)

        return False

    async def _report_unknown(self, page, account_id: str):
        """截图 + 视觉分析 + 日志上报"""
        log.warning(f"  📸 [{account_id}] 无法自动恢复，截图上报...")

        try:
            screenshot_path = f"/tmp/login_fail_{account_id}.png"
            await page.screenshot(path=screenshot_path)
            log.warning(f"  📸 截图保存: {screenshot_path}")

            # 尝试视觉分析
            try:
                from vision_bridge import analyze_screenshot
                result = await analyze_screenshot(
                    screenshot_path,
                    "What is on this page? Why can't the system log in?"
                )
                log.warning(f"  👁️ 视觉分析: {result[:200]}")
            except Exception:
                pass
        except Exception as e:
            log.warning(f"  ⚠️ 截图失败: {e}")

        log.warning(f"  ❌ [{account_id}] 需手动登录处理")

    # ── 验证弹窗检测 ──────────────────────────────────────

    async def check_verify_dialog(self, page) -> str:
        """检测页面是否有验证弹窗 → 'none' / 'sms' / 'captcha' / 'unknown'"""
        platform = self._platform

        # 抖音验证弹窗
        if platform == "douyin":
            try:
                from douyin_ops import SELECTORS as DY_SEL
                if await page.locator(DY_SEL["verify_panel"]).count() > 0:
                    # 判断是短信验证还是滑块
                    if await page.locator(DY_SEL["verify_input"]).count() > 0:
                        return "sms"
                    return "captcha"
            except Exception:
                pass

        # 小红书验证弹窗
        if platform == "xiaohongshu":
            try:
                if await page.locator(".r-captcha-modal").count() > 0:
                    return "captcha"
                if await page.locator('input[placeholder*="验证码"]').count() > 0:
                    return "sms"
            except Exception:
                pass

        # 通用: 检查验证码输入框
        try:
            if await page.locator('input[placeholder*="验证码"]').count() > 0:
                return "sms"
        except Exception:
            pass

        return "none"
