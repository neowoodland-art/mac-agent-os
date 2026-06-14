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
    """连接浏览器（Chrome CDP / Camoufox 原生 / Camoufox 持久化）"""

    def __init__(self, port: int = 9222, browser_type: str = "auto",
                 headless: bool = True, window: tuple = (702, 783),
                 profile_dir: str = None,
                 locale: list = None,
                 identity_dir: str = None,
                 window_position: tuple = (0, 0)):
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
        
        身份工厂模式（Camoufox 持久化）:
        - identity_dir: identities/{name}/ 目录路径
          设置后将自动加载 config.yaml 中的固化指纹，
          使用 persistent_context=True + user_data_dir 启动
        - window_position: 窗口在屏幕上的位置 (left, top)，写入 xulstore
        """
        self.port = port
        self.browser_type = browser_type
        self.headless = headless
        self.window = window
        self.profile_dir = profile_dir
        self.locale = locale or ["zh-CN"]
        self.identity_dir = identity_dir
        self.window_position = window_position
        
        self._playwright = None
        self._camoufox = None          # AsyncCamoufox 实例（防止 GC 回收导致连接断开）
        self._camoufox_browser = None  # Camoufox native browser handle
        self.browser = None
        self.context = None
        self.page = None
        self.cdp_session = None
        self._is_camoufox_native = False
        self._identity_config = None  # 缓存的 config.yaml 内容

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
        
        self._camoufox = AsyncCamoufox(**kwargs)
        self._camoufox_browser = await self._camoufox.start()
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

    # ─── Camoufox 持久化启动（身份工厂模式）────────────────────────

    async def _launch_camoufox_persistent(self):
        """通过身份工厂配置启动持久化 Camoufox

        核心改进:
        - persistent_context=True → 状态保存在 user_data_dir
        - user_data_dir → 固定 Profile 目录，不丢失登录态
        - fingerprint → 固化指纹，每次启动同一副面孔
        """
        import pickle
        import yaml
        from camoufox.async_api import AsyncCamoufox

        identity_path = Path(self.identity_dir)
        config_path = identity_path / "config.yaml"
        fp_path = identity_path / "fingerprint.pkl"
        user_data_dir = str(identity_path / "user_data")

        if not config_path.exists():
            raise FileNotFoundError(
                f"身份配置文件不存在: {config_path}\n"
                f"请先运行: python create_identity.py {identity_path.name}")

        # 加载身份配置
        with open(config_path) as f:
            config = yaml.safe_load(f)
        self._identity_config = config

        # 加载固化指纹（pickle 格式，BrowserForge Fingerprint 对象）
        fingerprint = None
        if fp_path.exists():
            with open(fp_path, 'rb') as f:
                fingerprint = pickle.load(f)

        proxy = config["identity"].get("proxy")

        # 读取窗口尺寸（优先用配置中的，否则用默认值）
        cfg_window = config.get("window", self.window)
        if isinstance(cfg_window, (list, tuple)) and len(cfg_window) == 2:
            w_width, w_height = int(cfg_window[0]), int(cfg_window[1])
        else:
            w_width, w_height = self.window

        # 构建 Camoufox 参数
        # 清理残留锁文件（防止上次非正常退出导致启动失败）
        for lock_file in [".parentlock", ".startup-incomplete", "lock"]:
            try:
                lf = Path(user_data_dir) / lock_file
                if lf.exists():
                    lf.unlink()
            except:
                pass

        kwargs = {
            'persistent_context': True,
            'user_data_dir': user_data_dir,
            'headless': self.headless,
            'window': (w_width, w_height),
            'locale': self.locale or ['zh-CN'],
            'os': 'windows',
            'fonts': ['STHeiti', 'Heiti SC', 'PingFang SC', 'Noto Sans CJK SC'],
            'humanize': 1.5,
            'firefox_user_prefs': {
                'dom.disable_window_move_resize': False,
            },
            'args': [
                f'--width={w_width}',
                f'--height={w_height}',
                '--new-window',
            ],
            # Camoufox config：在启动前注入 DOM 属性覆盖
            # 让 viewport/screen 全部固定为 702×783
            'config': {
                'window.innerWidth': w_width,
                'window.innerHeight': w_height,
                'window.outerWidth': w_width,
                'window.outerHeight': w_height,
                'screen.width': w_width,
                'screen.height': w_height,
                'screen.availWidth': w_width,
                'screen.availHeight': w_height,
            },
        }

        # 注入固化指纹（关键！——确保每次启动同一副面孔）
        if fingerprint is not None:
            kwargs['fingerprint'] = fingerprint
            kwargs['i_know_what_im_doing'] = True  # 抑制 Camoufox 自定义指纹警告
            print(f"   指纹: ✅ 已固化 ({type(fingerprint).__name__})")
        else:
            print(f"   指纹: ⚠️ 未指定（将随机生成）")

        # 注入代理
        if proxy:
            proxy_cfg = {'server': proxy} if isinstance(proxy, str) else proxy
            kwargs['proxy'] = proxy_cfg
            print(f"   代理: {proxy_cfg['server']}")

        print(f"🦊 启动 Camoufox 持久化模式")
        print(f"   Profile: {user_data_dir}")

        # ── 强制设置 Firefox 窗口大小 ──
        # Firefox 在 xulstore.json 中存储窗口状态，每次启动时读取它，
        # 这会导致 --width/--height 命令行参数被覆盖。
        # 在启动前直接写入这个文件，确保窗口尺寸正确。
        try:
            import json as _j
            xul_path = Path(user_data_dir) / "xulstore.json"
            # 从 accounts.yaml 读取窗口位置，回退到 self.window_position
            cfg_path = Path(self.identity_dir).parent.parent / "config" / "accounts.yaml"
            cfg_x, cfg_y = self.window_position
            try:
                import yaml as _y
                if cfg_path.exists():
                    with open(cfg_path) as _f:
                        _cfg = _y.safe_load(_f)
                    for _a in _cfg.get("accounts", []):
                        if _a.get("identity_dir", "").rstrip('/') == self.identity_dir.rstrip('/') or \
                           _a.get("id") in self.identity_dir:
                            _wp = _a.get("window_position")
                            if _wp and len(_wp) == 2:
                                cfg_x, cfg_y = int(_wp[0]), int(_wp[1])
                            break
            except: pass

            xul_data = {
                "chrome://browser/content/browser.xhtml": {
                    "main-window": {
                        "screenX": str(cfg_x),
                        "screenY": str(cfg_y),
                        "width": str(w_width),
                        "height": str(w_height),
                        "sizemode": "normal"
                    }
                }
            }
            xul_path.parent.mkdir(parents=True, exist_ok=True)
            xul_path.write_text(_j.dumps(xul_data, indent=2))
            print(f"   xulstore: {w_width}×{w_height}")
        except Exception as e:
            print(f"   ⚠️ xulstore: {e}")

        self._camoufox = AsyncCamoufox(**kwargs)
        # persistent_context=True 返回的是 BrowserContext（包含已保存状态）
        ctx = await self._camoufox.start()
        self._camoufox_browser = ctx
        self._is_camoufox_native = True
        self.context = ctx

        # 获取或创建页面
        if ctx.pages:
            self.page = ctx.pages[0]
        else:
            self.page = await ctx.new_page()

        # 强制设置窗口大小（Firefox --width/--height 有时不生效，JS 确保实际窗口尺寸）
        try:
            await self.page.evaluate(f"""
                window.moveTo(0, 0);
                window.resizeTo({w_width}, {w_height});
            """)
        except Exception:
            pass  # resizeTo 可能被浏览器策略阻止，不影响主体功能

        print(f"✅ Camoufox 持久化就绪 | user_data: {identity_path.name}/user_data/")
        print(f"   窗口: {w_width}×{w_height}")

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
        """连接到浏览器（自动选择模式）

        优先级:
        1. identity_dir 模式 → Camoufox 持久化（persistent_context）
        2. camoufox 类型 → Camoufox 原生（临时 profile）
        3. 其他 → CDP 连接（Chrome/Firefox）
        """
        # 先杀残留 Camoufox 进程 + 清理锁文件
        import subprocess
        subprocess.run(['pkill', '-f', 'camoufox'], capture_output=True, timeout=5)
        await asyncio.sleep(2)

        if self.identity_dir:
            # 清理锁文件
            for lock in ['.parentlock', '.startup-incomplete', 'lock']:
                try:
                    lf = Path(self.identity_dir) / 'user_data' / lock
                    if lf.exists(): lf.unlink()
                except: pass
            await self._launch_camoufox_persistent()
        else:
            bt = self._resolve_browser_type()
            if bt == "camoufox":
                await self._launch_camoufox()
            else:
                await self._connect_cdp()
        return self.page

    # ─── 反检测 ────────────────────────────────────────────────

    async def init_anti_detection(self):
        """初始化反检测配置（安卓平板模式视口 + App跳转拦截）

        关键: mobile=True 可使抖音加载移动端/平板界面，
        这样才能显示点赞/收藏/评论按钮。

        2026-05-03 ghai 要求：全部改为安卓平板标识
        UA: Samsung Galaxy Tab S9 (SM-X910, Android 14)
        """
        # 安卓平板 User-Agent（通用）
        ANDROID_TABLET_UA = (
            "Mozilla/5.0 (Linux; Android 14; SM-X910) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.6367.113 Safari/537.36"
        )

        if self._is_camoufox_native:
            # Camoufox: 只设置视口尺寸（702×783 小窗口模拟平板）
            # 注意：不覆盖 UA！Camoufox 的 Windows Firefox UA 是 C++ 级原生伪装，
            # 强行改为 Android 会导致底层指纹（platform/fonts/webgl）与 UA 矛盾
            await self.page.set_viewport_size({
                "width": self.window[0],
                "height": self.window[1]
            })
            print(f"✅ Camoufox 反检测已就绪（Windows 平板 702×783）")
            return None
        
        # Chrome CDP: 使用 DevTools Protocol 设置 UA + 触摸 + 视口
        if not self.cdp_session:
            self.cdp_session = await self.context.new_cdp_session(self.page)

        # 1) 设置安卓平板 User-Agent
        try:
            await self.cdp_session.send("Network.setUserAgentOverride", {
                "userAgent": ANDROID_TABLET_UA
            })
        except Exception:
            pass

        # 2) 设置视口尺寸
        try:
            await self.page.set_viewport_size({
                "width": self.window[0],
                "height": self.window[1]
            })
        except Exception:
            pass

        # 3) 启用触摸模拟（关键！让 maxTouchPoints > 0，抖音才能识别为触摸设备）
        try:
            await self.cdp_session.send("Emulation.setTouchEmulationEnabled", {
                "enabled": True,
                "maxTouchPoints": 5,
                "configuration": "mobile",
            })
        except Exception:
            pass

        # 设置安卓平板 User-Agent
        try:
            await self.cdp_session.send("Network.setUserAgentOverride", {
                "userAgent": ANDROID_TABLET_UA
            })
        except Exception:
            pass

        print("✅ 反检测已就绪（平板模式 702x783 + iPad UA + 触摸模拟）")
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
        # 优先通过 AsyncCamoufox 实例优雅关闭（会依次关浏览器+Playwright驱动）
        if hasattr(self, '_camoufox') and self._camoufox:
            await self._camoufox.stop()
        elif self._camoufox_browser:
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
