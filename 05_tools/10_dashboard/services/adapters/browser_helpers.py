"""
browser_helpers.py — 抓取系统的浏览器辅助函数 v2

用途：
  当 OpenCLI 抓取失败时，通过真实 Chrome 浏览器降级提取数据。

设计原则：
  ⛔ 绝不使用 Camoufox（养号专用，Firefox 内核 + 特殊指纹）
  ✅ 使用 Playwright 启动真实 Chrome（Chromium 内核，正常指纹）
  ✅ 支持 headless 和 headed 两种模式
  ✅ 浏览器实例复用，避免反复启动

调用方式：
  from services.adapters.browser_helpers import page_evaluate, page_extract

  # 执行 JS 提取数据
  data = await page_evaluate("https://www.douyin.com/video/xxx", js_code)

  # 按 CSS 选择器提取
  texts = await page_extract("https://www.douyin.com/video/xxx", ["h1.title", ".desc"])
"""
import asyncio, json, logging, os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dashboard.scrape.browser")

# ── 浏览器单例（复用实例，避免反复启动）──

_browser = None
_lock = asyncio.Lock()
_USER_DATA_DIR = os.environ.get(
    "SCRAPE_CHROME_USER_DATA",
    str(Path.home() / "workbuddy-agent-os" / "agent-local" / "runtime" / "scrape_chrome_profile"),
)

# Chrome 可执行路径
_CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS 标准路径
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
_CHROME_PATH = None
for p in _CHROME_PATHS:
    if Path(p).exists():
        _CHROME_PATH = p
        break


async def _get_browser(headless: bool = True):
    """
    获取/创建浏览器实例（单例）。
    使用 Playwright 启动真实 Chrome，而非 Camoufox。
    """
    global _browser
    async with _lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("Playwright 未安装，无法使用浏览器降级")
            # 尝试安装
            try:
                proc = await asyncio.create_subprocess_exec(
                    *["playwright", "install", "chromium"],
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await proc.communicate()
                from playwright.async_api import async_playwright
            except Exception:
                raise RuntimeError("Playwright 不可用，无法启动浏览器降级")

        p = await async_playwright().start()
        launch_kwargs = {
            "headless": headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1280,720",
            ],
        }
        if _CHROME_PATH:
            launch_kwargs["executable_path"] = _CHROME_PATH
            logger.info(f"使用系统 Chrome: {_CHROME_PATH}")
        else:
            logger.info("使用 Playwright 内置 Chromium")

        try:
            _browser = await p.chromium.launch(**launch_kwargs)
            logger.info("✅ 浏览器降级: Chrome 启动成功")
        except Exception as e:
            logger.error(f"❌ 浏览器启动失败: {e}")
            await p.stop()
            raise
        return _browser


async def page_evaluate(url: str, js_code: str,
                        timeout: int = 30000, headless: bool = True) -> dict:
    """
    打开 URL，执行 JavaScript 提取数据。

    参数:
      url:       目标页面地址
      js_code:   要执行的 JS 代码（字符串形式的箭头函数或普通函数）
      timeout:   页面加载超时（毫秒）
      headless:  是否无头模式

    返回:
      字典。JS 返回值的 JSON 表示。失败时返回 {}。
    """
    browser = await _get_browser(headless=headless)
    context = None
    page = None
    try:
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
            locale="zh-CN",
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        # 等待页面稳定
        await page.wait_for_load_state("networkidle", timeout=timeout)
        # 额外等待，让动态渲染完成
        await asyncio.sleep(1)

        # 执行 JS
        result = await page.evaluate(js_code)
        if result is None:
            logger.warning(f"  ⚠️ page_evaluate JS 返回 null: {url[:60]}")
            return {}

        # 序列化确保可 JSON 返回
        if isinstance(result, (dict, list)):
            return result
        return {"_value": str(result)}

    except Exception as e:
        logger.warning(f"  ⚠️ page_evaluate 失败 [{url[:60]}]: {e}")
        return {}
    finally:
        if page:
            await page.close()
        if context:
            await context.close()


async def page_extract(url: str, selectors: list,
                       timeout: int = 30000, headless: bool = True) -> dict:
    """
    打开 URL，按 CSS 选择器提取 DOM 文本。

    参数:
      url:       目标页面
      selectors: CSS 选择器列表，如 ["h1", ".video-title", "[data-e2e=comment-count]"]
      timeout:   超时（毫秒）
      headless:  是否无头

    返回:
      {selector: [text1, text2, ...], ...}
    """
    js = f"""() => {{
        const results = {{}};
        const sel = {json.dumps(selectors)};
        for (const s of sel) {{
            const els = document.querySelectorAll(s);
            results[s] = Array.from(els).map(el => el.textContent.trim()).filter(t => t);
        }}
        return results;
    }}"""
    return await page_evaluate(url, js, timeout=timeout, headless=headless)


async def close_browser():
    """关闭浏览器实例（清理时调用）"""
    global _browser
    async with _lock:
        if _browser:
            try:
                await _browser.close()
                logger.info("浏览器降级: Chrome 已关闭")
            except Exception as e:
                logger.warning(f"关闭浏览器时出错: {e}")
            _browser = None
