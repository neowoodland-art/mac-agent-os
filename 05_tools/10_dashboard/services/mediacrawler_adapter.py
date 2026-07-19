"""
mediacrawler_adapter.py — MediaCrawler 风格适配器 (v2)

核心改动：
  1. 连接 Chrome CDP 一次，复用整个 session
  2. 每个视频打开其视频页，而非首页（获取正确的 cookie 上下文）
  3. 采集完关闭 tab，不关浏览器
  4. 全局单例 Session 管理
"""
import asyncio, json, logging, os, re, time
from pathlib import Path

logger = logging.getLogger("dashboard.mediacrawler_adapter")

CDP_PORT = 9222
_SESSION = None  # 全局单例
_CDP_SEMAPHORE = asyncio.Semaphore(3)  # 限制最多 3 个并发 CDP 操作

class ChromeCDPSession:
    """管理 Chrome CDP 连接的全局单例"""
    
    def __init__(self):
        self._pw = None
        self.browser = None
        self._lock = asyncio.Lock()
        self._tabs = []

    async def ensure_connected(self):
        if self.browser and self.browser.is_connected():
            return True
        try:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self.browser = await self._pw.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
            ctx = self.browser.contexts[0] if self.browser.contexts else await self.browser.new_context()
            # 访问抖音首页建立 cookie（后续所有 tab 共享上下文）
            page = await ctx.new_page()
            await page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
            await page.close()
            logger.info("CDP Session 已建立")
            return True
        except Exception as e:
            self.browser = None
            logger.warning(f"CDP 连接失败: {e}")
            return False

    async def close(self):
        if self.browser:
            try:
                await self.browser.close()
            except:
                pass
            self.browser = None
        if self._pw:
            try:
                await self._pw.stop()
            except:
                pass
            self._pw = None


async def _get_session() -> ChromeCDPSession:
    global _SESSION
    if _SESSION is None:
        _SESSION = ChromeCDPSession()
    return _SESSION


async def _fetch_video_data_cdp(aweme_id: str, page) -> dict:
    """
    在指定 page 上下文中获取单个视频的数据
    page 需已导航到抖音首页（cookie 已建立）
    """
    try:
        # 导航到视频页（获取正确的 referer 和 cookie 上下文）
        await page.goto(
            f"https://www.douyin.com/video/{aweme_id}",
            wait_until="domcontentloaded", timeout=20000
        )
        await page.wait_for_timeout(3000)

        # 调抖音内部 API 获取视频详情
        detail_json = await page.evaluate(f"""async () => {{
            try {{
                const r = await fetch(
                    'https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={aweme_id}&version_code=170400&app_name=aweme&device_platform=web',
                    {{ headers: {{ 'Accept': 'application/json, text/plain, */*', 'Referer': 'https://www.douyin.com/' }} }}
                );
                const data = await r.json();
                return JSON.stringify(data);
            }} catch(e) {{
                return JSON.stringify({{error: e.message}});
            }}
        }}""")

        detail = json.loads(detail_json)
        if "error" in detail:
            return {"success": False, "error": detail["error"]}

        aweme = detail.get("aweme_detail", {})
        if not aweme:
            return {"success": False, "error": f"API 未返回数据: {str(detail)[:200]}"}

        statistics = aweme.get("statistics", {})
        author_info = aweme.get("author", {})

        data = {
            "title": aweme.get("desc", ""),
            "author": author_info.get("nickname", ""),
            "likes": int(statistics.get("digg_count", 0)),
            "comments": int(statistics.get("comment_count", 0)),
            "collects": int(statistics.get("collect_count", 0)),
            "shares": int(statistics.get("share_count", 0)),
            "comment_texts": [],
        }

        # 获取热评
        try:
            cmt_json = await page.evaluate(f"""async () => {{
                try {{
                    const r = await fetch(
                        'https://www.douyin.com/aweme/v1/web/comment/list/?aweme_id={aweme_id}&count=20&cursor=0',
                        {{ headers: {{ 'Accept': 'application/json, text/plain, */*', 'Referer': 'https://www.douyin.com/' }} }}
                    );
                    const data = await r.json();
                    return JSON.stringify(data);
                }} catch(e) {{
                    return JSON.stringify({{comments_error: e.message}});
                }}
            }}""")
            cmt_result = json.loads(cmt_json)
            cmts = cmt_result.get("comments", [])
            for c in cmts[:20]:
                user = c.get("user", {})
                data["comment_texts"].append({
                    "nickname": user.get("nickname", ""),
                    "text": c.get("text", ""),
                    "likes": c.get("digg_count", 0),
                })
        except Exception as e:
            logger.debug(f"评论获取失败: {e}")

        return {"success": True, "data": data}

    except Exception as e:
        return {"success": False, "error": f"页面操作失败: {e}"}


async def get_video_data(url: str) -> dict:
    """
    统一入口：传入抖音视频 URL，返回完整数据
    复用 Chrome CDP Session，不重复打开浏览器
    """
    import time as _time

    aweme_id = _extract_aweme_id(url)
    if not aweme_id:
        aweme_id = _resolve_shortlink(url)
    if not aweme_id:
        return {"error": f"无法解析视频 ID: {url}"}

    t0 = _time.time()
    result = {
        "aweme_id": aweme_id,
        "title": "",
        "author": "",
        "likes": 0,
        "comments": 0,
        "collects": 0,
        "shares": 0,
        "comment_texts": [],
        "collected_at": _time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    session = await _get_session()
    connected = await session.ensure_connected()
    if not connected:
        logger.warning("CDP 不可用，降级 Playwright")
        pw_data = await _fetch_via_playwright(aweme_id)
        if pw_data.get("success"):
            result.update(pw_data["data"])
        else:
            result["error"] = pw_data.get("error", "所有采集方法均失败")
        return result

    # 每个请求开一个独立 tab，不复用旧的（避免互扰）
    # 用信号量限制并发，最多 3 个同时采集
    async with _CDP_SEMAPHORE:
        try:
            ctx = session.browser.contexts[0] if session.browser.contexts else await session.browser.new_context()
            page = await ctx.new_page()
            await page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)
            cdp_data = await _fetch_video_data_cdp(aweme_id, page)
            await page.close()
        except Exception as e:
            cdp_data = {"success": False, "error": str(e)}

    if cdp_data.get("success"):
        result.update(cdp_data["data"])
        result["_method"] = "cdp"
        result["_duration"] = round(_time.time() - t0, 2)
    else:
        logger.warning(f"CDP 采集失败: {cdp_data.get('error')}，降级")
        pw_data = await _fetch_via_playwright(aweme_id)
        if pw_data.get("success"):
            result.update(pw_data["data"])
            result["_method"] = "playwright"
        else:
            result["error"] = pw_data.get("error", "所有采集方法均失败")

    return result


# ── 降级方案 (Playwright 标准模式，不依赖 CDP) ──

async def _fetch_via_playwright(aweme_id: str) -> dict:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"success": False, "error": "Playwright 未安装"}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(f"https://www.douyin.com/video/{aweme_id}", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)
            text = await page.inner_text("body")
            title, author = "", ""
            ld = await page.evaluate('''() => { const el = document.querySelector('script[type="application/ld+json"]'); if (!el) return null; try { return JSON.parse(el.textContent); } catch(e) { return null; } }''')
            if ld and ld.get("itemListElement"):
                for item in ld["itemListElement"]:
                    if item.get("position") == 2:
                        author = item.get("name", "")
            m = re.search(r'获赞([\d.]+[万wW]?)', text)
            likes = _parse_num(m.group(1)) if m else 0
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for l in lines:
                if "#" in l and len(l) > 10:
                    title = l.split("#")[0].strip()
                    break
            await browser.close()
            return {"success": True, "data": {"title": title, "author": author, "likes": likes, "comments": 0, "collects": 0, "shares": 0, "comment_texts": [], "_notice": "Playwright 降级"}}
    except Exception as e:
        return {"success": False, "error": f"Playwright: {e}"}


# ── 工具函数 ──

def _extract_aweme_id(url: str):
    m = re.search(r'douyin\.com/video/(\d+)', url)
    if m: return m.group(1)
    m = re.search(r'iesdouyin\.com/share/video/(\d+)', url)
    if m: return m.group(1)
    return None

def _resolve_shortlink(url: str):
    import subprocess
    try:
        result = subprocess.run(["curl", "-sI", url], capture_output=True, text=True, timeout=10)
        for line in result.stdout.split("\n"):
            if line.lower().startswith("location:"):
                loc = line.split(":", 1)[1].strip()
                m = re.search(r'/video/(\d+)', loc)
                if m: return m.group(1)
    except: pass
    return None

def _parse_num(s: str) -> int:
    s = s.strip().replace(" ", "")
    if "万" in s or "w" in s.lower():
        try: return int(float(s.replace("万", "").replace("w", "").replace("W", "")) * 10000)
        except: return 0
    try: return int(float(s))
    except: return 0
