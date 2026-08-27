"""
mediacrawler_adapter.py — 抖音视频数据采集器 v3

全新架构：不再依赖 CDP/Playwright/浏览器页面。
直接从 Chrome profile 读取 cookie，通过 HTTP 请求调用抖音 API。
全程无窗口、无标签页、无闪烁。
"""
import asyncio, json, logging, os, re, time, sqlite3, urllib.request, urllib.error
from pathlib import Path

logger = logging.getLogger("dashboard.mediacrawler_adapter")

# HTTP 请求头（模拟浏览器）
DOUYIN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.douyin.com/",
    "Origin": "https://www.douyin.com",
}


# ── Playwright CDP 连接管理（复用，避免反复建连） ──
# Chrome 新版把 cookie 值加密存在 SQLite 里，必须通过 CDP 读解密后的值。

_PW = None
_BROWSER = None

async def _ensure_cdp():
    """确保 Playwright CDP 连接可用（全局复用）"""
    global _PW, _BROWSER
    if _BROWSER and _PW:
        try:
            if _BROWSER.is_connected():
                return _BROWSER.contexts[0] if _BROWSER.contexts else None
        except:
            pass
        # 断连了，重建
        try:
            await _BROWSER.close()
        except:
            pass
        try:
            await _PW.stop()
        except:
            pass
        _BROWSER = None
        _PW = None
    
    try:
        from playwright.async_api import async_playwright
        _PW = await async_playwright().start()
        _BROWSER = await _PW.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = _BROWSER.contexts[0] if _BROWSER.contexts else None
        return ctx
    except Exception as e:
        _BROWSER = None
        _PW = None
        logger.warning(f"CDP 连接失败: {e}")
        return None


async def _get_cookies() -> dict:
    """从 CDP 连接读取 Chrome cookie（解密后的值）"""
    ctx = await _ensure_cdp()
    if not ctx:
        return {}
    try:
        all_cookies = await ctx.cookies()
        result = {}
        for c in all_cookies:
            domain = c.get("domain", "")
            if "douyin" in domain or "amemv" in domain:
                result[c["name"]] = c["value"]
        return result
    except Exception as e:
        logger.warning(f"读 cookie 失败: {e}")
        return {}


def _cookie_str(cookies: dict) -> str:
    """将 cookie 字典转为 HTTP Header 字符串"""
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


# ── HTTP API 请求（不打开任何浏览器页面） ──

def _http_get(url: str, cookies: dict, timeout: int = 15) -> dict:
    """发起 HTTP GET 请求并返回 JSON（cookies 必传，由调用方从 CDP 获取）"""
    req = urllib.request.Request(
        url,
        headers={
            **DOUYIN_HEADERS,
            "Cookie": _cookie_str(cookies),
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# ── 工具函数 ──

def _extract_aweme_id(url: str):
    m = re.search(r'douyin\.com/video/(\d+)', url)
    if m:
        return m.group(1)
    m = re.search(r'iesdouyin\.com/share/video/(\d+)', url)
    if m:
        return m.group(1)
    # 抖音精选页 / 发现页：modal_id 就是视频 aweme_id（jingxuan?modal_id=xxx）
    m = re.search(r'(?:jingxuan|discover|modal_id)[=?/](\d+)', url)
    if m:
        return m.group(1)
    return None


def _resolve_shortlink(url: str):
    import subprocess
    try:
        result = subprocess.run(
            ["curl", "-sI", url], capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.split("\n"):
            if line.lower().startswith("location:"):
                loc = line.split(":", 1)[1].strip()
                m = re.search(r'/video/(\d+)', loc)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return None


# ── 核心：获取视频数据（纯 HTTP，无浏览器） ──

async def get_video_data(url: str) -> dict:
    """
    统一入口：传入抖音视频 URL，返回完整数据
    通过 HTTP API 获取，不打开任何浏览器页面
    """
    aweme_id = _extract_aweme_id(url)
    if not aweme_id:
        aweme_id = _resolve_shortlink(url)
    if not aweme_id:
        return {"error": f"无法解析视频 ID: {url}"}

    t0 = time.time()
    result = {
        "aweme_id": aweme_id,
        "title": "",
        "author": "",
        "likes": 0,
        "comments": 0,
        "collects": 0,
        "shares": 0,
        "comment_texts": [],
        "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 读取登录态 cookie（通过 CDP，解密后的值）
    cookies = await _get_cookies()
    has_session = bool(cookies.get("sessionid"))
    if not has_session:
        result["error"] = "抖音登录已过期，请点击顶部「📱 打开抖音登录」按钮重新登录"
        result["login_expired"] = True
        return result

    # 调抖音 API 获取视频详情
    try:
        api_url = (
            f"https://www.douyin.com/aweme/v1/web/aweme/detail/"
            f"?aweme_id={aweme_id}&version_code=170400&app_name=aweme&device_platform=web"
        )
        detail = await asyncio.to_thread(_http_get, api_url, cookies)
    except urllib.error.HTTPError as e:
        result["error"] = f"HTTP {e.code}: {e.reason}"
        return result
    except Exception as e:
        result["error"] = f"请求失败: {e}"
        return result

    aweme = detail.get("aweme_detail", {})
    if not aweme:
        if detail.get("status_code") == 2:
            result["error"] = "抖音登录已过期，请重新登录"
            result["login_expired"] = True
            return result
        if detail.get("filter_detail"):
            # filter_detail = 视频被平台过滤（已删除/违规/推广限制），详情不可查
            result["error"] = "⚠️ 视频被平台过滤，无法采集（可能已删除/违规/推广限制）"
            result["filtered"] = True
            return result
        result["error"] = f"API 未返回数据: {str(detail)[:200]}"
        return result

    statistics = aweme.get("statistics", {})
    author_info = aweme.get("author", {})

    result.update({
        "title": aweme.get("desc", ""),
        "author": author_info.get("nickname", ""),
        "author_uid": author_info.get("uid", ""),          # 数字ID（博主精确身份）
        "author_sec_uid": author_info.get("sec_uid", ""),  # 加密ID
        "author_unique_id": author_info.get("unique_id", ""),  # 抖音号
        "likes": int(statistics.get("digg_count", 0)),
        "comments": int(statistics.get("comment_count", 0)),
        "collects": int(statistics.get("collect_count", 0)),
        "shares": int(statistics.get("share_count", 0)),
    })

    # 获取热评（复用已有 Chrome 页面，不创建新标签页）
    # Chrome 已有 douyin.com 页面，直接用它的 JS 上下文执行 fetch
    # ⚠️ 不要 new_page() — 那会在 Chrome 中闪出新标签页
    try:
        _ctx2 = await _ensure_cdp()
        if _ctx2:
            _pages = _ctx2.pages
            if _pages:
                _page = _pages[0]  # 复用已有页面（about:blank 或 douyin.com）
                _cmt_json = await _page.evaluate(f"""async () => {{
                    try {{
                        const r = await fetch(
                            'https://www.douyin.com/aweme/v1/web/comment/list/?aweme_id={aweme_id}&count=20&cursor=0',
                            {{ headers: {{ 'Accept': 'application/json, text/plain, */*', 'Referer': 'https://www.douyin.com/' }} }}
                        );
                        return JSON.stringify(await r.json());
                    }} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
                }}""")
                _cmt_data = json.loads(_cmt_json)
                if "error" not in _cmt_data:
                    for c in _cmt_data.get("comments", [])[:20]:
                        user = c.get("user", {})
                        result["comment_texts"].append({
                            "nickname": user.get("nickname", ""),
                            "text": c.get("text", ""),
                            "likes": c.get("digg_count", 0),
                        })
    except Exception as e:
        logger.debug(f"评论获取失败: {e}")

    result["_method"] = "http_api"
    result["_duration"] = round(time.time() - t0, 2)
    return result


# ── 博主采集（抖音博主监控） ──
# ⚠️ 注意：profile/other 和 aweme/post 接口要用「数字 uid」，
#    不能用 sec_user_id（会报 UserId不合法）。
#    数字 uid 从视频详情 API 的 author.uid 字段获取。

async def get_author_profile(uid: str) -> dict:
    """获取博主主页信息（粉丝数/获赞数/作品数/昵称/签名）
    
    Args:
        uid: 博主数字 ID（从视频详情的 author.uid 获取）
    
    Returns:
        {"uid", "nickname", "unique_id", "fans", "total_favorited",
         "works", "following", "signature", "avatar", "sec_uid", ...}
        失败时含 "error" 字段
    """
    result = {"uid": str(uid)}
    cookies = await _get_cookies()
    has_session = bool(cookies.get("sessionid"))
    if not has_session:
        result["error"] = "抖音登录已过期"
        result["login_expired"] = True
        return result

    try:
        api_url = (
            f"https://www.douyin.com/aweme/v1/web/user/profile/other/"
            f"?user_id={uid}&device_platform=webapp&aid=6383"
        )
        data = await asyncio.to_thread(_http_get, api_url, cookies)
    except urllib.error.HTTPError as e:
        result["error"] = f"HTTP {e.code}: {e.reason}"
        return result
    except Exception as e:
        result["error"] = f"请求失败: {e}"
        return result

    user = data.get("user", {})
    if not user:
        result["error"] = f"未返回用户数据: {data.get('status_msg', '')} (code={data.get('status_code')})"
        return result

    result.update({
        "nickname": user.get("nickname", ""),
        "unique_id": user.get("unique_id", ""),
        "sec_uid": user.get("sec_uid", ""),
        "fans": user.get("follower_count", 0),
        "total_favorited": user.get("total_favorited", 0),
        "works": user.get("aweme_count", 0),
        "following": user.get("following_count", 0),
        "signature": user.get("signature", ""),
        "avatar": (user.get("avatar_thumb") or {}).get("url_list", [""])[0] if user.get("avatar_thumb") else "",
        "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    return result


async def get_author_videos(uid: str, count: int = 20) -> dict:
    """获取博主最新发布的视频列表（按发布时间倒序）
    
    Args:
        uid: 博主数字 ID
        count: 拉取条数（默认20）
    
    Returns:
        {"uid", "videos": [{aweme_id, title, likes, comments, collects,
                            shares, create_time, url}], "has_more"}
    """
    result = {"uid": str(uid), "videos": [], "has_more": False}
    cookies = await _get_cookies()
    has_session = bool(cookies.get("sessionid"))
    if not has_session:
        result["error"] = "抖音登录已过期"
        result["login_expired"] = True
        return result

    try:
        api_url = (
            f"https://www.douyin.com/aweme/v1/web/aweme/post/"
            f"?user_id={uid}&count={count}&max_cursor=0&device_platform=webapp&aid=6383"
        )
        data = await asyncio.to_thread(_http_get, api_url, cookies)
    except urllib.error.HTTPError as e:
        result["error"] = f"HTTP {e.code}: {e.reason}"
        return result
    except Exception as e:
        result["error"] = f"请求失败: {e}"
        return result

    result["has_more"] = bool(data.get("has_more"))
    for a in data.get("aweme_list", [])[:count]:
        st = a.get("statistics", {})
        result["videos"].append({
            "aweme_id": str(a.get("aweme_id", "")),
            "title": a.get("desc", ""),
            "likes": int(st.get("digg_count", 0)),
            "comments": int(st.get("comment_count", 0)),
            "collects": int(st.get("collect_count", 0)),
            "shares": int(st.get("share_count", 0)),
            "create_time": a.get("create_time", 0),
            "url": f"https://www.douyin.com/video/{a.get('aweme_id', '')}",
        })
    return result


# ── 登录状态检测（从 cookie 文件直接读取，无窗口操作） ──

async def check_login_status() -> dict:
    """检测抖音登录状态（通过 CDP，无页面操作）"""
    cookies = await _get_cookies()
    has_session = bool(cookies.get("sessionid"))
    return {
        "logged_in": has_session,
        "cookie_sessionid": has_session,
        "cookies_count": len(cookies),
    }


# ── 打开登录页（用 AppleScript 控制 Chrome，不需要 CDP） ──

async def open_login_page():
    """在 Chrome 中打开抖音首页，让用户登录
    
    使用 macOS 的 open 命令（比 AppleScript 更可靠，不依赖辅助功能权限）。
    登录后 cookie 自动保存到 Chrome profile，两个 Chrome 都会检测。
    """
    import subprocess as _sp
    
    try:
        # 先用 open 命令让 Chrome 激活并打开抖音首页
        # open -a 会激活已有的 Chrome 窗口（无论是日常还是采集）
        _sp.run(
            ["open", "-a", "Google Chrome", "https://www.douyin.com/"],
            capture_output=True, timeout=10
        )
        logger.info("已请求 Chrome 打开抖音首页")
        return {
            "success": True,
            "message": "已打开抖音首页，请在 Chrome 中点击右上角「登录」扫码",
        }
    except Exception as e:
        logger.error(f"打开抖音首页失败: {e}")
        return {"success": False, "error": f"打开失败: {e}"}
