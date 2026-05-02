#!/usr/bin/env python3
"""
CDP 连接器 — 连接本机浏览器（Chrome / Camoufox）
用法: python cdp_connector.py [port]

支持模式:
  Chrome:   通过 CDP 端口连接 Google Chrome
  Camoufox: 通过原生 API 启动 Firefox 内核浏览器

工作流示例:
  # Chrome CDP 模式
  conn = CDPConnector(port=9222)
  await conn.connect()

  # Camoufox 原生模式
  conn = CDPConnector(browser_type="camoufox", headless=True)
  await conn.connect()
"""
import asyncio
import json
import random
import time
from pathlib import Path
from typing import Optional


class CDPConnector:
    """连接浏览器（Chrome CDP / Camoufox 原生）"""

    def __init__(self, port: int = 9222, browser_type: str = "auto",
                 headless: bool = True, window: tuple = (702, 783),
                 profile_dir: str = None,
                 locale: list = None):
        """
        browser_type: auto / chromium / firefox / camoufox
        - auto: 根据端口自动判断（9301+ 为 Firefox/Camoufox）
        - chromium: 强制 Chrome CDP
        - firefox: 通过 CDP 连接 Firefox
        - camoufox: 使用 Camoufox 原生 API 启动（不依赖外部CDP端口）
        
        Camoufox 专用参数:
        - headless: 是否无头模式（默认 True）
        - window: 窗口大小 (width, height)
        - profile_dir: Profile 目录路径
        - locale: 语言设置（默认 ["zh-CN"]）
        """
        self.port = port
        self.browser_type = browser_type
        self.headless = headless
        self.window = window
        self.profile_dir = profile_dir
        self.locale = locale or ["zh-CN"]
        
        self._playwright = None
        self._camoufox_browser = None  # Camoufox native browser handle
        self.browser = None
        self.context = None
        self.page = None
        self.cdp_session = None
        self._is_camoufox_native = False

    def _resolve_browser_type(self) -> str:
        if self.browser_type != "auto":
            return self.browser_type
        return "firefox" if self.port >= 9301 else "chromium"

    # ─── Camoufox 原生启动 ──────────────────────────────────────

    async def _launch_camoufox(self):
        """通过 Camoufox 原生 API 启动浏览器"""
        from camoufox.async_api import AsyncCamoufox
        
        kwargs = {
            'headless': self.headless,
            'window': self.window,
            'locale': self.locale,
            # 固定 Windows 指纹（UA/WebGL/Canvas 全部伪装为 Windows）
            # 默认是随机选择，这会导致手机端提示"macOS/Windows"不确定
            'os': 'windows',
            # 加载系统中文字体（STHeiti/华文黑体），防止中文乱码
            # Camoufox 默认不加载系统字体，需要显式指定
            'fonts': ['STHeiti', 'Heiti SC', 'PingFang SC', 'Noto Sans CJK SC'],
            # 鼠标行为拟人化，使操作更接近真人
            'humanize': 1.5,
        }
        
        print(f"🦊 启动 Camoufox (Firefox 135, OS=Windows, headless={self.headless})")
        
        cf = AsyncCamoufox(**kwargs)
        self._camoufox_browser = await cf.start()
        self._is_camoufox_native = True
        
        # Get browser context and page
        if self._camoufox_browser.contexts:
            self.context = self._camoufox_browser.contexts[0]
        else:
            self.context = await self._camoufox_browser.new_context()
        
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()
        
        print(f"✅ Camoufox 就绪，当前页面: {self.page.url}")

    # ─── Chrome / Firefox CDP 连接 ──────────────────────────────

    async def _connect_cdp(self):
        """通过 CDP 协议连接 Chrome/Firefox"""
        bt = self._resolve_browser_type()
        
        import urllib.request
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        
        # 获取 WebSocket Debugger URL
        with opener.open(f"http://localhost:{self.port}/json/version", timeout=5) as r:
            info = json.loads(r.read())
        ws_url = info.get("webSocketDebuggerUrl")
        if not ws_url:
            raise RuntimeError(f"无法获取 WebSocket URL（端口 {self.port}）")

        from patchright.async_api import async_playwright
        self._playwright = await async_playwright().start()
        
        if bt == "firefox":
            self.browser = await self._playwright.firefox.connect_over_cdp(ws_url)
        else:
            self.browser = await self._playwright.chromium.connect_over_cdp(ws_url)

        self.context = self.browser.contexts[0]
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()
        print(f"✅ 已连接 {bt}（端口 {self.port}），当前页面数：{len(self.context.pages)}")
        return self.page

    # ─── 统一入口 ───────────────────────────────────────────────

    async def connect(self):
        """连接到浏览器（自动选择 Camoufox 原生 或 CDP）"""
        bt = self._resolve_browser_type()
        
        if bt == "camoufox":
            await self._launch_camoufox()
        else:
            await self._connect_cdp()
        return self.page

    # ─── 反检测 ────────────────────────────────────────────────

    async def init_anti_detection(self):
        """初始化反检测配置（平板模式视口 + App跳转拦截）
        
        关键: mobile=True 可使抖音加载移动端/平板界面，
        这样才能显示点赞/收藏/评论按钮。
        """
        if self._is_camoufox_native:
            # Camoufox: 设置平板视口 + iPad UA
            await self.page.set_viewport_size({
                "width": self.window[0],
                "height": self.window[1]
            })
            await self.page.evaluate("""() => {
                Object.defineProperty(navigator, 'userAgent', {
                    get: () => 'Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
                });
            }""")
            print("✅ Camoufox 反检测已就绪（平板模式 702x783 + iPad UA）")
            return None
        
        # Chrome CDP: 使用 DevTools Protocol
        if not self.cdp_session:
            self.cdp_session = await self.context.new_cdp_session(self.page)

        # 关键: mobile=true → 抖音识别为平板/手机，显示播放器UI
        await self.cdp_session.send("Emulation.setDeviceMetricsOverride", {
            "width": 702, "height": 783,
            "deviceScaleFactor": 2,
            "mobile": True,
            "screenWidth": 702,
            "screenHeight": 783,
        })

        # 设置 iPad User-Agent
        try:
            await self.cdp_session.send("Network.setUserAgentOverride", {
                "userAgent": "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
            })
        except Exception:
            pass

        # App 跳转拦截
        blocked_schemes = [
            "xhdsdiscover://*", "snssdk1128://*", "snssdk1233://*",
            "kuaishou://*", "zhihu://*", "weixin://*",
            "alipays://*", "taobao://*", "openapp.jdmobile://*", "intent://*",
        ]
        await self.cdp_session.send("Fetch.enable", {
            "patterns": [
                {"urlPattern": s, "requestStage": "Request"}
                for s in blocked_schemes
            ]
        })

        async def handle_paused(event):
            try:
                await self.cdp_session.send("Fetch.failRequest", {
                    "requestId": event["requestId"],
                    "errorReason": "Aborted"
                })
            except Exception:
                pass

        self.cdp_session.on("Fetch.requestPaused", handle_paused)
        print("✅ 反检测已就绪（平板模式 702x783 + iPad UA + App跳转拦截）")
        return self.cdp_session

    # ─── 导航 ───────────────────────────────────────────────────

    async def goto(self, url: str, wait: str = "domcontentloaded"):
        await self.page.goto(url, wait_until=wait, timeout=30000)
        await asyncio.sleep(1.5)
        await self.remove_overlays()
        return self.page

    async def remove_overlays(self):
        """清理 App 跳转弹窗和遮罩"""
        script = """
        () => {
            const selectors = [
                '[class*="download"]','[class*="open-app"]','[class*="app-guide"]',
                '[class*="launch-app"]','[class*="open-in-app"]','[class*="app-launcher"]',
                '.open-in-app','.app-launch-mask','.download-tip','.bottom-bar',
                '.download-banner','.open-app-btn','.app-download-tip',
                '.open-app-layer','.download-guide-mask',
                '.open-in-app-bar','.app-open-button',
                '#app-launch-dialog','#open-app-modal','#download-modal',
            ];
            let count = 0;
            selectors.forEach(s => {
                document.querySelectorAll(s).forEach(el => { el.remove(); count++; });
            });
            document.body.style.overflow = '';
            document.body.style.overflowY = 'auto';
            document.body.style.position = '';
            return count;
        }
        """
        removed = await self.page.evaluate(script)
        if removed > 0:
            print(f"  🧹 已清理 {removed} 个弹窗/遮罩")
        return removed

    # ─── 交互 ───────────────────────────────────────────────────

    async def touch_tap(self, x: int, y: int):
        """模拟触摸点击"""
        if self._is_camoufox_native:
            await self.page.tap("#root", position={"x": x, "y": y})
            return
        ts = int(time.time() * 1000)
        await self.cdp_session.send("Input.dispatchTouchEvent", {
            "type": "touchStart",
            "touchPoints": [{"x": x, "y": y, "id": 0}],
            "timestamp": ts
        })
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await self.cdp_session.send("Input.dispatchTouchEvent", {
            "type": "touchEnd",
            "touchPoints": [{"x": x, "y": y, "id": 0}],
            "timestamp": int(time.time() * 1000)
        })

    async def swipe_up(self, distance: int = 600, duration_ms: int = 400):
        """向上滑动（浏览下一条内容）"""
        if self._is_camoufox_native:
            await self.page.evaluate(f"window.scrollBy(0, {distance})")
            return

        cx = 195
        start_y = 700
        end_y = start_y - distance
        steps = 20
        step_duration = duration_ms / steps / 1000

        for i in range(steps):
            progress = i / steps
            current_y = start_y + (end_y - start_y) * progress
            event_type = "touchStart" if i == 0 else ("touchEnd" if i == steps - 1 else "touchMove")
            await self.cdp_session.send("Input.dispatchTouchEvent", {
                "type": event_type,
                "touchPoints": [{"x": cx, "y": current_y, "id": 0}],
                "timestamp": int(time.time() * 1000)
            })
            await asyncio.sleep(step_duration + random.uniform(-0.005, 0.005))

    async def check_login(self, platform: str = "douyin") -> dict:
        """检测登录状态（委托 auth_manager 多维检测）
        
        返回字典包含: logged_in, cookie_ok, dom_ok, cookie_count, session_id, method
        不再只依赖 DOM 检测（桌面端视口不显示头像元素）。
        """
        from auth_manager import get_login_status
        return await get_login_status(self.context, self.page, platform)

    # ─── 清理 ───────────────────────────────────────────────────

    async def close(self):
        if self._camoufox_browser:
            await self._camoufox_browser.close()
        if self._playwright:
            await self._playwright.stop()


# ─── 快速测试 ────────────────────────────────────────────────────
async def _test(port: int = 9222, browser_type: str = "auto"):
    print(f"测试连接（端口 {port}, 类型 {browser_type}）...")
    conn = CDPConnector(port=port, browser_type=browser_type)
    try:
        page = await conn.connect()
        await conn.init_anti_detection()

        print("\n测试导航到抖音...")
        await conn.goto("https://www.douyin.com")
        print(f"  URL:   {page.url}")
        print(f"  Title: {await page.title()}")

        status = await conn.check_login("douyin")
        print(f"  抖音登录状态: {'✅ 已登录 (via ' + status['method'] + ')' if status['logged_in'] else '❌ 未登录'}")
        print(f"     Cookie: {status['cookie_count']}个, sessionid: {'✅' if status['session_id'] else '❌'}")

    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("提示：")
        print("  Chrome:  bash ~/matrix/scripts/launch_chrome.sh account_01 9222")
        print("  Camoufox: 指定 browser_type='camoufox'")
    finally:
        await conn.close()


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    port = 9222
    btype = "auto"
    if args:
        port = int(args[0])
    if len(args) > 1:
        btype = args[1]
    asyncio.run(_test(port, btype))
