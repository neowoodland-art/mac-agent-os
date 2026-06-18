#!/usr/bin/env python3
"""
⚠️ 已废弃 — 请使用 cdp_connector.py 替代。
   本文件保留以供 orchestrator.py 引用，新代码禁止导入。

BrowserManager — 浏览器生命周期管理 (v1.0.0)

功能:
  - Chrome CDP 模式（优雅启动/关闭）
  - Camoufox (Firefox) 原生模式
  - 端口冲突检测与优雅清理
  - 启动后 CDP 等待就绪

用法:
    bm = BrowserManager()
    await bm.launch("douyin_01")    # 读取配置启动
    await bm.close()                 # 优雅关闭
"""

import asyncio
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional

from local_paths import config_path, profiles_path, data_path

# 版本
__version__ = "1.0.0"


class BrowserManagerError(Exception):
    pass


class BrowserManager:
    """浏览器管理器 — 优雅启停"""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self._account = None
        self._config = None
        self._connector = None  # cdp_connector 实例
        self._camoufox_handle = None  # AsyncCamoufox 实例
        self.browser_type = None  # "chrome" | "camoufox"

    # ─── 加载账号配置 ────────────────────────────────────────────

    def _load_account(self, account_id: str) -> dict:
        """从 accounts.yaml 加载账号配置"""
        import yaml
        acct_file = config_path("accounts.yaml")
        with open(acct_file) as f:
            data = yaml.safe_load(f)
        for a in data.get("accounts", []):
            if a["id"] == account_id:
                return a
        raise BrowserManagerError(f"账号不存在: {account_id}")

    # ─── Chrome 启动 ────────────────────────────────────────────

    def _find_chrome(self) -> str:
        """查找 Chrome 可执行文件"""
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]
        for c in candidates:
            if Path(c).exists():
                return c
        # 尝试通过 Playwright 找
        try:
            from patchright import async_api
            return str(async_api.sync_playwright().chromium.executable_path)
        except Exception:
            raise BrowserManagerError("Chrome 未安装")

    def _graceful_kill(self, port: int, wait: float = 3.0):
        """优雅停止端口上的进程 (SIGTERM → 等待 → SIGKILL)"""
        try:
            r = subprocess.run(["lsof", "-ti", f":{port}"],
                               capture_output=True, text=True, timeout=5)
            pids = [int(p) for p in r.stdout.strip().split() if p.strip()]
            if not pids:
                return
            # SIGTERM 先
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            # 等待进程退出
            deadline = time.time() + wait
            while time.time() < deadline:
                alive = False
                for pid in pids[:]:
                    try:
                        os.kill(pid, 0)
                        alive = True
                    except ProcessLookupError:
                        pids.remove(pid)
                if not alive:
                    return
                time.sleep(0.3)
            # 还没退出的强制杀
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        except subprocess.TimeoutExpired:
            pass

    async def _launch_chrome(self, account: dict):
        """启动 Chrome — 使用 subprocess + CDP（不走 Playwright）
        
        关键：Playwright 内部协议会被抖音检测 → 桌面版
        改用 subprocess 启动 + CDP 连接 → 手机版正常
        """
        chrome = self._find_chrome()
        port = account.get("port", 9222)
        profile_dir = str(profiles_path() / account.get("profile_dir", account["id"]))

        # 优雅清理旧进程
        self._graceful_kill(port, wait=3.0)
        await asyncio.sleep(1)

        # 启动 Chrome（用 --remote-debugging-port 但不走 Playwright）
        cmd = [
            chrome,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run", "--no-default-browser-check",
            "--disable-extensions",
            "--window-size=702,783",
            "about:blank",
        ]
        self.process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        self.browser_type = "chrome"

        # 等待 CDP 就绪
        import urllib.request
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(15):
            try:
                with opener.open(f"http://localhost:{port}/json/version", timeout=3) as r:
                    if r.status == 200:
                        # 用 cdp_connector 建立连接
                        from cdp_connector import CDPConnector
                        self._connector = CDPConnector(port=port)
                        await self._connector.connect()
                        self._page = self._connector.page
                        return port
            except Exception:
                pass
            await asyncio.sleep(1)
        raise BrowserManagerError(f"Chrome CDP 启动超时 (端口 {port})")
        return port

    # ─── Camoufox 启动 ──────────────────────────────────────────

    async def _launch_camoufox(self, account: dict):
        """启动 Camoufox (Firefox) 原生模式"""
        from camoufox.async_api import AsyncCamoufox

        self._camoufox_handle = AsyncCamoufox(
            headless=False,
            window=(702, 783),
            locale=["zh-CN"],
        )
        browser = await self._camoufox_handle.start()
        self.browser_type = "camoufox"
        return browser  # 返回 AsyncBrowser 对象

    # ─── 统一入口 ───────────────────────────────────────────────

    async def launch(self, account_id: str) -> dict:
        """
        启动浏览器
        返回: {"type": "chrome"|"camoufox", "port": int|None, "browser": object|None}
        """
        self._account = self._load_account(account_id)
        bt = self._account.get("browser_type", "chrome")

        if bt == "camoufox" or bt == "firefox":
            browser = await self._launch_camoufox(self._account)
            return {"type": "camoufox", "port": self._account.get("port", 9301), "browser": browser}
        else:
            await self._launch_chrome(self._account)
            return {"type": "chrome", "port": self._account.get("port", 9222), "page": self._page}

    # ─── 获取已连接的 page ────────────────────────────────────

    @property
    def page(self):
        """获取 Playwright page 对象"""
        if hasattr(self, '_page') and self._page:
            return self._page
        return None

    # ─── 关闭 ──────────────────────────────────────────────────

    # ─── 登录态管理 ──────────────────────────────────────────

    async def detect_login_state(self, page) -> dict:
        """检测登录状态，返回:
        {"status": "logged_in"|"cookie_available"|"lost",
         "method": "profile"|"cookie"|"",
         "detail": str}
        """
        # 1. 从已启动的浏览器检查 Cookie
        try:
            cookies = await page.context.cookies()
            dy = [c for c in cookies if "douyin" in c.get("domain", "")]
            has_session = any(c["name"] == "sessionid" for c in dy)
            if has_session:
                return {"status": "logged_in", "method": "profile", "detail": "浏览器已有 sessionid"}
        except Exception:
            pass

        # 2. 检查是否有保存的 Cookie 文件
        cookie_file = data_path("cookies") / f"{self._account['id']}_cookies.json"
        if cookie_file.exists():
            try:
                saved_cookies = json.loads(cookie_file.read_text())
                has_session = any(c.get("name") == "sessionid" and c.get("domain", "").find("douyin") >= 0 for c in saved_cookies)
                if has_session:
                    return {"status": "cookie_available", "method": "cookie",
                            "detail": f"Cookie文件存在 ({cookie_file.name})", "file": str(cookie_file)}
            except Exception:
                pass

        # 3. 登录态丢失
        return {"status": "lost", "method": "", "detail": "无可用登录态"}

    async def inject_cookies(self, page) -> bool:
        """注入保存的 Cookie 到浏览器"""
        acct_id = self._account["id"]
        cookie_file = data_path("cookies") / f"{acct_id}_cookies.json"
        if not cookie_file.exists():
            return False
        try:
            cookies = json.loads(cookie_file.read_text())
            count = 0
            for c in cookies:
                try:
                    await page.context.add_cookies([{
                        "name": c["name"], "value": c["value"],
                        "domain": c["domain"], "path": c.get("path", "/"),
                        "httpOnly": c.get("httpOnly", False),
                        "secure": c.get("secure", False),
                        "sameSite": c.get("sameSite", "Lax"),
                    }])
                    count += 1
                except Exception:
                    pass
            return count > 0
        except Exception:
            return False

    # ─── 激活手机模式 ────────────────────────────────────────

    async def activate_mobile_mode(self, page):
        """激活手机模式：通过CDP设置UA+视口，然后刷新"""
        if self.browser_type == "chrome" and hasattr(self, '_connector') and self._connector:
            try:
                cdp = self._connector.cdp_session
                if not cdp:
                    cdp = await self._connector.context.new_cdp_session(page)
                await cdp.send("Network.setUserAgentOverride", {
                    "userAgent": "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
                })
                await cdp.send("Emulation.setDeviceMetricsOverride", {
                    "width": 702, "height": 783, "deviceScaleFactor": 2,
                    "mobile": True, "screenWidth": 702, "screenHeight": 783,
                })
            except Exception:
                pass
        # 刷新激活
        try:
            await page.reload(wait_until="domcontentloaded")
        except Exception:
            await page.goto("https://www.douyin.com/", timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(5)

    async def apply_fingerprint_protection(self, page):
        """应用浏览器指纹保护"""
        from anti_detection import FINGERPRINT_SCRIPT
        try:
            result = await page.evaluate(FINGERPRINT_SCRIPT)
            print(f"  🔒 指纹保护: {result}")
        except Exception as e:
            print(f"  ⚠️ 指纹保护: {type(e).__name__}")

    async def remove_overlays(self, page):
        """清理页面弹窗"""
        from anti_detection import OVERLAY_REMOVE_SCRIPT
        try:
            count = await page.evaluate(OVERLAY_REMOVE_SCRIPT)
            if count > 0:
                print(f"  🧹 清理 {count} 个弹窗")
            return count
        except Exception:
            return 0

    async def close(self):
        """优雅关闭浏览器"""
        # 关闭 CDP connector (Chrome)
        if hasattr(self, '_connector') and self._connector:
            try:
                await self._connector.close()
            except Exception:
                pass
            self._connector = None

        # 关闭 Camoufox
        if hasattr(self, '_camoufox_handle') and self._camoufox_handle:
            try:
                await self._camoufox_handle.stop()
            except Exception:
                pass
            self._camoufox_handle = None

        # 关闭 Chrome 进程 (SIGTERM)
        if hasattr(self, 'process') and self.process:
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
            except Exception:
                pass
            self.process = None
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
            except Exception:
                pass
            self.process = None

        await asyncio.sleep(1)

    # ─── 获取账号信息 ──────────────────────────────────────────

    @property
    def account_name(self) -> str:
        return self._account.get("display_name", self._account.get("id", "?"))

    @property
    def account_id(self) -> str:
        return self._account.get("id", "?")
