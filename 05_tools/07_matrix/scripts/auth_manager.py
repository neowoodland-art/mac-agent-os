#!/usr/bin/env python3
"""
🔐 AuthManager — 登录状态管理原子化模块 (v1.0.0)

原子操作:
  check_login_by_cookie(context)    → bool  # Cookie 检测（主方案）
  check_login_by_dom(page)          → bool  # DOM 检测（备选，仅移动端视口）
  get_login_status(context, page)   → dict  # 多维综合检测
  export_cookies(context, path)     → int   # 导出 Cookie 到文件
  inject_cookies(context, path)     → int   # 从文件注入 Cookie
  get_session_id(cookies)           → str   # 提取 sessionid

设计原则:
  1. Cookie 检测为主方案（不依赖 UI 布局）
  2. DOM 检测为备选（仅在 mobile=True 视口下有效）
  3. 所有函数无副作用（不写 DB/文件，除非函数名明确）
  4. 统一异常处理（所有异常返回 False/空值，不抛出）

最后更新: 2026-05-01
"""

import json
import asyncio
from pathlib import Path
from typing import Optional

__version__ = "1.0.0"


# ══════════════════════════════════════════════════════════════
# Cookie 检测（核心方案）
# ══════════════════════════════════════════════════════════════

# ── 各平台登录态 Cookie 规则 ──
LOGIN_COOKIE_RULES = {
    "douyin": {
        "domain": "douyin",
        "names": ("sessionid", "sid_guard"),
    },
    "xiaohongshu": {
        "domain": "xiaohongshu",
        "names": ("a1", "web_session"),
    },
    "kuaishou": {
        "domain": "kuaishou",
        "names": ("kuaishou.login",),
    },
    "zhihu": {
        "domain": "zhihu",
        "names": ("z_c0", "d_c0"),
    },
}


async def check_login_by_cookie(context, platform: str = "douyin") -> bool:
    """通过 Cookie 检测登录状态
    
    检测平台特有的 session cookie 是否存在。
    这是主方案，不依赖页面 DOM 布局。
    
    参数:
        context: Playwright BrowserContext
        platform: 平台名称 (douyin/xiaohongshu/kuaishou/zhihu)
    
    返回:
        bool: True=已登录, False=未登录
    """
    try:
        cookies = await context.cookies()
    except Exception:
        return False
    
    rule = LOGIN_COOKIE_RULES.get(platform)
    if not rule:
        return False
    
    for c in cookies:
        domain = c.get("domain", "")
        name = c.get("name", "")
        if rule["domain"] in domain and name in rule["names"]:
            return True
    
    return False


def check_login_by_cookie_sync(cookies: list, platform: str = "douyin") -> bool:
    """同步版 Cookie 检测（从已获取的 Cookie 列表判断）
    
    参数:
        cookies: Cookie 列表（每个为 dict，含 domain/name 字段）
        platform: 平台名称 (douyin/xiaohongshu/...)
    
    返回:
        bool: True=已登录
    """
    rule = LOGIN_COOKIE_RULES.get(platform)
    if not rule:
        return False
    
    for c in cookies:
        domain = c.get("domain", "")
        name = c.get("name", "")
        if rule["domain"] in domain and name in rule["names"]:
            return True
    return False


def get_session_id(cookies: list, platform: str = "douyin") -> Optional[str]:
    """从 Cookie 列表中提取 session cookie 值
    
    参数:
        cookies: Cookie 列表
        platform: 平台名称
    
    返回:
        str/None: session cookie 值或 None
    """
    rule = LOGIN_COOKIE_RULES.get(platform)
    if not rule:
        return None
    for c in cookies:
        if c.get("name") in rule["names"]:
            return c.get("value")
    return None


def count_platform_cookies(cookies: list, platform: str = "douyin") -> int:
    """统计指定平台的 Cookie 数量"""
    rule = LOGIN_COOKIE_RULES.get(platform)
    if not rule:
        return 0
    domain_hint = rule["domain"]
    return sum(1 for c in cookies if domain_hint in c.get("domain", ""))


# ══════════════════════════════════════════════════════════════
# DOM 检测（备选方案）
# ══════════════════════════════════════════════════════════════

# 各平台登录态 DOM 指示器
LOGIN_INDICATORS = {
    "douyin": [
        "[data-e2e='user-avatar']",        # 主指示器
        "[data-e2e='user-detail']",         # 用户详情
    ],
    "xiaohongshu": [
        ".user-avatar",
        ".reds-count",
    ],
    "kuaishou": [
        ".avatar-container",
    ],
    "zhihu": [
        ".AppHeader-profile",
    ],
}


async def check_login_by_dom(page, platform: str = "douyin") -> bool:
    """通过 DOM 元素检测登录状态（备选方案）
    
    注意: 仅在移动端/平板视口 (mobile=True) 下有效。
    桌面端视口下抖音不渲染这些元素。
    
    参数:
        page: Playwright Page
        platform: 平台名称（douyin/xiaohongshu/kuaishou/zhihu）
    
    返回:
        bool: True=已登录
    """
    selectors = LOGIN_INDICATORS.get(platform, [])
    if not selectors:
        return False
    
    try:
        for sel in selectors:
            el = await page.query_selector(sel)
            if el:
                return True
    except Exception:
        pass
    
    return False


# ══════════════════════════════════════════════════════════════
# 综合检测
# ══════════════════════════════════════════════════════════════

async def get_login_status(context, page=None, platform: str = "douyin") -> dict:
    """多维综合登录检测
    
    同时使用 Cookie 检测 + DOM 检测，返回详细诊断信息。
    
    参数:
        context: Playwright BrowserContext
        page: Playwright Page（可选，不传则跳过 DOM 检测）
        platform: 平台名称
    
    返回:
        dict:
          logged_in: bool     # 最终判断（任意一个方法确认即可）
          cookie_ok: bool     # Cookie 检测结果
          dom_ok: bool/None   # DOM 检测结果（未传 page 为 None）
          cookie_count: int   # douyin.com Cookie 数量
          session_id: str/None # sessionid 值
          method: str         # 确认方法（cookie/dom/both）
    """
    result = {
        "logged_in": False,
        "cookie_ok": False,
        "dom_ok": None,
        "cookie_count": 0,
        "session_id": None,
        "method": "",
    }
    
    # Cookie 检测
    try:
        cookies = await context.cookies()
        result["cookie_ok"] = check_login_by_cookie_sync(cookies, platform)
        result["cookie_count"] = count_platform_cookies(cookies, platform)
        result["session_id"] = get_session_id(cookies, platform)
    except Exception:
        result["cookie_ok"] = False
    
    # DOM 检测
    if page:
        try:
            result["dom_ok"] = await check_login_by_dom(page, platform)
        except Exception:
            result["dom_ok"] = False
    
    # 综合判断
    if result["cookie_ok"] and result["dom_ok"]:
        result["logged_in"] = True
        result["method"] = "both"
    elif result["cookie_ok"]:
        result["logged_in"] = True
        result["method"] = "cookie"
    elif result["dom_ok"]:
        result["logged_in"] = True
        result["method"] = "dom"
    
    return result


# ══════════════════════════════════════════════════════════════
# Cookie 导出 / 注入
# ══════════════════════════════════════════════════════════════

async def export_cookies(context, file_path: Path) -> int:
    """导出当前浏览器的所有 Cookie 到 JSON 文件
    
    参数:
        context: Playwright BrowserContext
        file_path: 导出文件路径
    
    返回:
        int: 导出的 Cookie 数量（0 表示失败）
    """
    try:
        cookies = await context.cookies()
        if not cookies:
            return 0
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)
        
        return len(cookies)
    except Exception:
        return 0


async def inject_cookies(context, file_path: Path) -> int:
    """从 JSON 文件注入 Cookie 到浏览器
    
    参数:
        context: Playwright BrowserContext
        file_path: Cookie JSON 文件路径
    
    返回:
        int: 成功注入的 Cookie 数量（0 表示失败）
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return 0
        
        cookies = json.loads(file_path.read_text(encoding="utf-8"))
        if not cookies:
            return 0
        
        success = 0
        for c in cookies:
            try:
                await context.add_cookies([{
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ""),
                    "path": c.get("path", "/"),
                    "httpOnly": c.get("httpOnly", False),
                    "secure": c.get("secure", False),
                    "sameSite": c.get("sameSite", "Lax"),
                }])
                success += 1
            except Exception:
                pass
        
        return success
    except Exception:
        return 0


async def wait_for_login(context, page, platform: str = "douyin",
                         timeout: int = 300, interval: int = 5) -> dict:
    """等待用户手动登录（轮询 Cookie + DOM）
    
    用于自动化流程中等待用户扫码登录的场景。
    不阻塞终端，自动检测到登录后返回。
    
    参数:
        context: Playwright BrowserContext
        page: Playwright Page
        platform: 平台名称
        timeout: 超时秒数（默认 300s = 5分钟）
        interval: 轮询间隔秒数（默认 5s）
    
    返回:
        dict: get_login_status() 的返回结果
    
    如果超时，返回 logged_in=False
    """
    for i in range(timeout // interval):
        await asyncio.sleep(interval)
        status = await get_login_status(context, page, platform)
        if status["logged_in"]:
            return status
        print(f"   ⏳ 等待登录... ({i * interval + interval}s/{timeout}s)")
    # 超时
    print(f"   ⏰ 等待超时 ({timeout}s)")
    return {"logged_in": False, "cookie_ok": False, "dom_ok": False,
            "cookie_count": 0, "session_id": None, "method": ""}


# ══════════════════════════════════════════════════════════════
# 独立 CLI 测试入口
# ══════════════════════════════════════════════════════════════

async def _test_check(port: int = 9222):
    """测试连接指定端口的浏览器并检测登录状态"""
    import urllib.request
    from patchright.async_api import async_playwright
    
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://localhost:{port}/json/version", timeout=5) as r:
            ws_url = json.loads(r.read())["webSocketDebuggerUrl"]
    except Exception as e:
        print(f"❌ 无法连接端口 {port}: {e}")
        return
    
    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.connect_over_cdp(ws_url)
        page = browser.contexts[0].pages[0]
        context = browser.contexts[0]
        
        await page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(3)
        
        status = await get_login_status(context, page, platform="douyin")
        domain = "douyin"
        print(f"\n📊 登录状态检测 (端口 {port})")
        print(f"  Cookie OK:     {'✅' if status['cookie_ok'] else '❌'}")
        print(f"  DOM OK:        {'✅' if status['dom_ok'] else '❌'}")
        print(f"  {domain} Cookie: {status['cookie_count']} 个")
        print(f"  session:       {status['session_id'][:20] + '...' if status['session_id'] else '❌'}")
        print(f"  最终判断:       {'✅ 已登录 (via ' + status['method'] + ')' if status['logged_in'] else '❌ 未登录'}")
        
        await pw.stop()
    except Exception as e:
        print(f"❌ 检测失败: {e}")


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9222
    asyncio.run(_test_check(port))
