#!/usr/bin/env python3
"""
账号切换器 — 自动化 Chrome Profile 切换 + 指纹初始化

两套逻辑：
  方案A（默认）: Chrome Profile 切换 — 关闭旧 Chrome → 启动新 Profile → 初始化指纹
  方案B（实验）: Cookie 注入 — 单浏览器实例 → CDP 注入/清除 Cookie → 验证登录

用法:
  # 方案A: 切换到 account_02
  python switch_account.py --method profile --target account_02 --port 9222

  # 方案B: Cookie 注入切换（实验性）
  python switch_account.py --method cookie --target account_02 --port 9222

  # 查看当前活跃账号
  python switch_account.py --status

  # 列出所有账号
  python switch_account.py --list
"""
import argparse
import asyncio
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# ── 项目路径 ────────────────────────────────────────────────
from local_paths import config_path, profiles_path, data_path, logs_path, code_dir
CONFIG_PATH = config_path("accounts.yaml")
PROFILES_DIR = profiles_path()
DB_PATH = data_path("matrix.db")
LOG_DIR = logs_path()
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 全局视口配置（从 accounts.yaml 读取，默认 702x783 桌面端）
VIEWPORT_CONFIG = {"width": 702, "height": 783, "mobile": False}

# 指纹模板库（每个 Profile 用不同的指纹组合）
FINGERPRINT_TEMPLATES = [
    # template_id: (viewport, deviceScaleFactor, userAgent_hint, timezone, locale)
    {"id": "fp_iphone14pro",  "viewport": (393, 852),  "dsf": 3, "tz": "Asia/Shanghai", "locale": "zh-CN"},
    {"id": "fp_iphone15pro",  "viewport": (393, 852),  "dsf": 3, "tz": "Asia/Shanghai", "locale": "zh-CN"},
    {"id": "fp_pixel8",       "viewport": (412, 915),  "dsf": 2.625, "tz": "Asia/Shanghai", "locale": "zh-CN"},
    {"id": "fp_samsung24",    "viewport": (412, 915),  "dsf": 2.625, "tz": "Asia/Shanghai", "locale": "zh-CN"},
    {"id": "fp_iphone13",     "viewport": (390, 844),  "dsf": 3, "tz": "Asia/Shanghai", "locale": "zh-CN"},
    {"id": "fp_huawei_p60",   "viewport": (393, 873),  "dsf": 3, "tz": "Asia/Shanghai", "locale": "zh-CN"},
    {"id": "fp_xiaomi14",     "viewport": (393, 873),  "dsf": 3, "tz": "Asia/Shanghai", "locale": "zh-CN"},
    {"id": "fp_oppo_find",    "viewport": (412, 915),  "dsf": 2.625, "tz": "Asia/Shanghai", "locale": "zh-CN"},
]


def load_accounts_config() -> list:
    """加载 accounts.yaml（含全局视口配置）"""
    try:
        import yaml
    except ImportError:
        return _parse_yaml_simple(CONFIG_PATH)
    with open(CONFIG_PATH, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    # 保存全局视口配置
    global VIEWPORT_CONFIG
    VIEWPORT_CONFIG = data.get('viewport', VIEWPORT_CONFIG)
    return data.get('accounts', [])


def _parse_yaml_simple(path: Path) -> list:
    """简易 YAML 解析（无 PyYAML 时 fallback）— 支持 viewport 和 accounts"""
    accounts = []
    current = {}
    in_viewport = False
    vp = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        # 检测 viewport 块
        if stripped.startswith('viewport:'):
            in_viewport = True
            continue
        # 如果到了 accounts 块，退出 viewport
        if stripped.startswith('accounts:'):
            in_viewport = False
            continue
        # 解析 viewport 键值
        if in_viewport and ':' in stripped:
            k, v = stripped.split(':', 1)
            k, v = k.strip(), v.strip().strip('"').split('#')[0].strip()
            if v.lower() in ('true', 'false'):
                v = v.lower() == 'true'
            elif v.isdigit():
                v = int(v)
            vp[k] = v
            continue
        # 解析 account 条目
        if stripped.startswith('- id:'):
            if current:
                accounts.append(current)
            current = {'id': stripped.split(':', 1)[1].strip().strip('"')}
        elif ':' in stripped and current:
            k, v = stripped.split(':', 1)
            k, v = k.strip(), v.strip().strip('"')
            if v.lower() in ('true', 'false'):
                v = v.lower() == 'true'
            elif v.isdigit():
                v = int(v)
            current[k] = v
    if current:
        accounts.append(current)
    # 写入全局视口配置
    if vp:
        global VIEWPORT_CONFIG
        VIEWPORT_CONFIG = vp
    return accounts


def get_account(account_id: str) -> Optional[dict]:
    """根据 ID 获取账号配置"""
    for acc in load_accounts_config():
        if acc.get('id') == account_id:
            return acc
    return None


def get_fingerprint_for_account(account_id: str) -> dict:
    """根据账号 ID 稳定映射到指纹模板（同一账号永远同一指纹）"""
    # 用确定性哈希（不依赖 Python hash()，它不跨进程稳定）
    idx = sum(ord(c) for c in account_id) % len(FINGERPRINT_TEMPLATES)
    fp = FINGERPRINT_TEMPLATES[idx].copy()
    fp['account_id'] = account_id
    return fp


# ══════════════════════════════════════════════════════════════
# 方案A: Chrome Profile 切换
# ══════════════════════════════════════════════════════════════

def find_chrome_pids() -> list[int]:
    """查找当前运行的 Chrome 进程 PID"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'Google Chrome.*remote-debugging-port'],
            capture_output=True, text=True, timeout=5
        )
        return [int(p) for p in result.stdout.strip().splitlines() if p.strip()]
    except Exception:
        return []


def find_chrome_pid_on_port(port: int) -> Optional[int]:
    """查找监听指定端口的 Chrome PID"""
    try:
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True, text=True, timeout=5
        )
        pids = [int(p) for p in result.stdout.strip().splitlines() if p.strip()]
        return pids[0] if pids else None
    except Exception:
        return None


def kill_chrome_on_port(port: int, timeout: int = 15) -> bool:
    """优雅关闭指定端口的 Chrome（SIGTERM → 等待 → SIGKILL）"""
    pid = find_chrome_pid_on_port(port)
    if not pid:
        print(f"  端口 {port} 无 Chrome 进程")
        return True

    print(f"  🛑 关闭 Chrome PID={pid}（端口 {port}）...")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True

    # 等待进程退出
    for _ in range(timeout):
        try:
            os.kill(pid, 0)  # 检查进程是否还在
        except ProcessLookupError:
            print(f"  ✅ Chrome 已退出")
            return True
        time.sleep(1)

    # 强制终止
    print(f"  ⚠️ 超时，强制终止...")
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    time.sleep(2)
    return True


def launch_chrome(account: dict, port: int) -> bool:
    """启动 Chrome（指定 Profile + CDP 端口 + 指纹参数）"""
    profile_dir = PROFILES_DIR / account.get('profile_dir', account['id'])
    profile_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        CHROME,
        f'--remote-debugging-port={port}',
        f'--user-data-dir={profile_dir}',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-extensions',
        '--disable-background-networking',
        '--disable-sync',
        '--disable-component-update',
        '--disable-features=TranslateUI',
        '--disable-ipc-flooding-protection',
        '--disable-renderer-backgrounding',
        '--disable-backgrounding-occluded-windows',
        '--disable-client-side-phishing-detection',
        '--disable-default-apps',
        '--disable-hang-monitor',
        '--disable-popup-blocking',
        '--disable-prompt-on-repost',
        '--disable-breakpad',
        '--metrics-recording-only',
        f'--window-size={VIEWPORT_CONFIG.get("width",702)},{VIEWPORT_CONFIG.get("height",783)}',
        '--window-position=100,100',
    ]

    print(f"  🚀 启动 Chrome（账号: {account['id']}，端口: {port}）")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 等待 CDP 就绪
    import urllib.request
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for i in range(15):
        time.sleep(1)
        try:
            with opener.open(f"http://localhost:{port}/json/version", timeout=3) as r:
                info = json.loads(r.read())
                print(f"  ✅ Chrome CDP 已就绪")
                return True
        except Exception:
            print(f"  等待中... ({i+1}/15)")

    print(f"  ❌ Chrome 启动超时")
    return False


async def init_fingerprint(port: int, account_id: str) -> bool:
    """通过 CDP 注入浏览器指纹（视口 + 时区 + 语言 + WebGL 注入）"""
    from patchright.async_api import async_playwright
    import json, urllib.request

    fp = get_fingerprint_for_account(account_id)
    vw, vh = fp['viewport']

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"http://localhost:{port}/json/version", timeout=5) as r:
        ws_url = json.loads(r.read())["webSocketDebuggerUrl"]

    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.connect_over_cdp(ws_url)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        cdp = await context.new_cdp_session(page)

        # 1. 视口设置 — 从配置文件读取（默认 702x783 桌面端）
        #    mobile=false + 不覆盖 UA → Cookie 登录态正常
        vp = VIEWPORT_CONFIG
        await cdp.send("Emulation.setDeviceMetricsOverride", {
            "width": vp.get("width", 702),
            "height": vp.get("height", 783),
            "deviceScaleFactor": 1,
            "mobile": vp.get("mobile", False),
        })

        # 2. 时区覆盖
        await cdp.send("Emulation.setTimezoneOverride", {"timezoneId": fp['tz']})

        # 3. 语言覆盖
        await cdp.send("Emulation.setLocaleOverride", {"locale": fp['locale']})

        # 4. ⚠️ 不覆盖 User-Agent — 移动端 UA 会破坏 Cookie 登录态
        #    真实 Chrome 的 UA 由浏览器自行管理，覆盖会导致 Cookie 验证失败
        #    仅做视口+JS层指纹伪装

        # 5. App 跳转拦截
        blocked_schemes = [
            "xhdsdiscover://*", "snssdk1128://*", "snssdk1233://*",
            "kuaishou://*", "zhihu://*", "weixin://*",
            "alipays://*", "taobao://*", "openapp.jdmobile://*", "intent://*",
        ]
        await cdp.send("Fetch.enable", {
            "patterns": [{"urlPattern": s, "requestStage": "Request"} for s in blocked_schemes]
        })
        async def handle_paused(event):
            try:
                await cdp.send("Fetch.failRequest", {"requestId": event["requestId"], "errorReason": "Aborted"})
            except Exception:
                pass
        cdp.on("Fetch.requestPaused", handle_paused)

        # 6. WebGL Vendor/Renderer 注入（覆盖 GPU 指纹）
        await page.add_init_script("""
            // WebGL 指纹覆盖
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {
                if (param === 37445) return 'Google Inc. (NVIDIA)';
                if (param === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER, OpenGL 4.6)';
                return getParameter.call(this, param);
            };
            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(param) {
                if (param === 37445) return 'Google Inc. (NVIDIA)';
                if (param === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER, OpenGL 4.6)';
                return getParameter2.call(this, param);
            };
            // 隐藏 automation 标记
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            // 屏蔽 HeadlessChrome 标记
            const originalUA = navigator.userAgent;
            Object.defineProperty(navigator, 'userAgent', { get: () => originalUA.replace('Headless', '') });
            // 隐藏 plugins 为空的特征
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            // 隐藏 languages 为空
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
        """)

        print(f"  🔐 指纹注入完成:")
        print(f"     视口: {vw}x{vh} @ {fp['dsf']}x")
        print(f"     时区: {fp['tz']}")
        print(f"     语言: {fp['locale']}")
        print(f"     模板: {fp['id']}")

        return True
    except Exception as e:
        print(f"  ❌ 指纹注入失败: {e}")
        return False
    finally:
        await pw.stop()


async def switch_profile(target_id: str, port: int = 9222) -> bool:
    """方案A: 完整的 Profile 切换流程"""
    # 先加载配置（含视口设置）
    load_accounts_config()

    print(f"\n{'='*60}")
    print(f"🔄 方案A: Chrome Profile 切换 → {target_id}")
    print(f"{'='*60}")

    # 1. 查找目标账号
    account = get_account(target_id)
    if not account:
        print(f"❌ 账号 {target_id} 不存在")
        print(f"   可用账号: {[a['id'] for a in load_accounts_config()]}")
        return False

    if not account.get('enabled', True):
        print(f"⚠️ 账号 {target_id} 已禁用")

    # 2. 关闭当前 Chrome
    print(f"\n[1/4] 关闭当前 Chrome...")
    kill_chrome_on_port(port)
    time.sleep(2)

    # 3. 启动新 Chrome
    print(f"\n[2/4] 启动新 Chrome...")
    ok = launch_chrome(account, port)
    if not ok:
        return False

    # 4. 注入指纹
    print(f"\n[3/4] 注入浏览器指纹...")
    ok = await init_fingerprint(port, target_id)

    # 5. 验证登录（使用 auth_manager 多维检测，不再只依赖 DOM）
    print(f"\n[4/4] 验证登录状态...")
    from patchright.async_api import async_playwright
    import json, urllib.request
    from auth_manager import get_login_status, export_cookies

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"http://localhost:{port}/json/version", timeout=5) as r:
        ws_url = json.loads(r.read())["webSocketDebuggerUrl"]

    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.connect_over_cdp(ws_url)
        page = browser.contexts[0].pages[0]
        context = browser.contexts[0]

        # 导航到抖音
        await page.goto('https://www.douyin.com/', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(3)

        # 使用 auth_manager 多维检测（Cookie 主方案 + DOM 备选）
        status = await get_login_status(context, page)
        logged_in = status["logged_in"]
        method = status["method"]

        if logged_in:
            print(f"  ✅ 已登录（via {method}）")
            print(f"     douyin Cookie: {status['cookie_count']} 个")
            if status['session_id']:
                print(f"     sessionid: {status['session_id'][:20]}...")
            # 自动导出 Cookie
            cookie_dir = data_path("cookies")
            cookie_file = cookie_dir / f"{target_id}_cookies.json"
            n = await export_cookies(context, cookie_file)
            if n > 0:
                print(f"     Cookie 已自动导出 → {cookie_file.name} ({n} 个)")
        else:
            print(f"  ⚠️ 未登录")
            print(f"     Cookie 检测: {'✅' if status['cookie_ok'] else '❌'}")
            print(f"     DOM 检测:   {'✅' if status['dom_ok'] else '❌'}")
            print(f"     可用操作: 手动登录后重试，或 Cookie 注入")

        # 更新数据库
        _update_account_status(target_id, 'active' if logged_in else 'needs_login')

        print(f"\n{'='*60}")
        print(f"{'✅ 切换完成' if ok else '⚠️ 切换完成（指纹有问题）'}: {target_id}")
        print(f"   CDP: http://localhost:{port}")
        print(f"   登录: {'✅' if logged_in else '❌'}")
        print(f"{'='*60}")
        return ok
    except Exception as e:
        print(f"  ❌ 验证失败: {e}")
        return False
    finally:
        await pw.stop()


# ══════════════════════════════════════════════════════════════
# 方案B: Cookie 注入切换（实验性）
# ══════════════════════════════════════════════════════════════

COOKIE_STORAGE = data_path("cookies")


async def switch_cookie(target_id: str, port: int = 9222) -> bool:
    """方案B: Cookie 注入切换（单浏览器实例，秒级切换）"""
    print(f"\n{'='*60}")
    print(f"🔄 方案B: Cookie 注入切换 → {target_id}")
    print(f"{'='*60}")

    from patchright.async_api import async_playwright
    import json, urllib.request

    account = get_account(target_id)
    if not account:
        print(f"❌ 账号 {target_id} 不存在")
        return False

    # Cookie 文件路径
    cookie_file = COOKIE_STORAGE / f"{target_id}_cookies.json"
    if not cookie_file.exists():
        print(f"⚠️ Cookie 文件不存在: {cookie_file}")
        print(f"   需要先手动登录一次并导出 Cookie")
        return False

    # 连接浏览器
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"http://localhost:{port}/json/version", timeout=5) as r:
        ws_url = json.loads(r.read())["webSocketDebuggerUrl"]

    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.connect_over_cdp(ws_url)
        context = browser.contexts[0]
        page = context.pages[0]

        # 1. 先保存当前账号的 Cookie
        print(f"\n[1/4] 保存当前 Cookie...")
        current_url = page.url
        if 'douyin.com' in current_url:
            current_cookies = await context.cookies()
            # 猜测当前账号（通过 cookie 中的 uid）
            current_uid = None
            for c in current_cookies:
                if c.get('name') == 'uid':
                    current_uid = c.get('value')
                    break
            if current_uid:
                save_path = COOKIE_STORAGE / f"uid_{current_uid}_cookies.json"
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, 'w') as f:
                    json.dump(current_cookies, f)
                print(f"  ✅ 当前 Cookie 已保存到 {save_path.name}")

        # 2. 清除当前 Cookie
        print(f"\n[2/4] 清除当前抖音 Cookie...")
        await context.clear_cookies()
        print(f"  ✅ Cookie 已清除")

        # 3. 注入新账号 Cookie
        print(f"\n[3/4] 注入 {target_id} 的 Cookie...")
        with open(cookie_file) as f:
            cookies = json.load(f)

        # Playwright 需要 cookie 格式转换
        pw_cookies = []
        for c in cookies:
            pw_cookie = {
                "name": c.get("name"),
                "value": c.get("value"),
                "domain": c.get("domain", ".douyin.com"),
                "path": c.get("path", "/"),
            }
            if c.get("expires"):
                pw_cookie["expires"] = c["expires"]
            if c.get("httpOnly"):
                pw_cookie["httpOnly"] = True
            if c.get("secure"):
                pw_cookie["secure"] = True
            if c.get("sameSite"):
                pw_cookie["sameSite"] = c["sameSite"].capitalize()
            pw_cookies.append(pw_cookie)

        await context.add_cookies(pw_cookies)
        print(f"  ✅ 注入了 {len(pw_cookies)} 个 Cookie")

        # 4. 刷新验证
        print(f"\n[4/4] 刷新验证...")
        await page.goto('https://www.douyin.com/', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(3)

        avatar = page.locator("[data-e2e='user-avatar']")
        logged_in = await avatar.count() > 0

        if logged_in:
            print(f"  ✅ Cookie 有效，已登录")
        else:
            print(f"  ❌ Cookie 失效，需要重新登录")
            # 恢复原 Cookie
            await context.clear_cookies()
            if current_uid:
                restore_path = COOKIE_STORAGE / f"uid_{current_uid}_cookies.json"
                if restore_path.exists():
                    with open(restore_path) as f:
                        old_cookies = json.load(f)
                    await context.add_cookies(old_cookies)
                    print(f"  🔄 已恢复原账号 Cookie")

        _update_account_status(target_id, 'active' if logged_in else 'cookie_expired')

        print(f"\n{'='*60}")
        print(f"{'✅' if logged_in else '❌'} Cookie 切换: {target_id}")
        print(f"{'='*60}")
        return logged_in
    except Exception as e:
        print(f"❌ Cookie 切换失败: {e}")
        return False
    finally:
        await pw.stop()


async def export_cookies(account_id: str, port: int = 9222) -> bool:
    """导出当前浏览器的 Cookie 到文件"""
    from patchright.async_api import async_playwright
    import json, urllib.request

    cookie_file = COOKIE_STORAGE / f"{account_id}_cookies.json"

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"http://localhost:{port}/json/version", timeout=5) as r:
        ws_url = json.loads(r.read())["webSocketDebuggerUrl"]

    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.connect_over_cdp(ws_url)
        context = browser.contexts[0]
        cookies = await context.cookies()

        with open(cookie_file, 'w') as f:
            json.dump(cookies, f, indent=2)

        print(f"✅ 导出 {len(cookies)} 个 Cookie → {cookie_file}")
        return True
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        return False
    finally:
        await pw.stop()


# ── 辅助函数 ────────────────────────────────────────────────

def _update_account_status(account_id: str, status: str):
    """更新数据库中的账号状态"""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            INSERT OR REPLACE INTO accounts (id, platform, status, last_active)
            VALUES (?, 
                COALESCE((SELECT platform FROM accounts WHERE id=?), 'douyin'),
                ?, datetime('now'))
        """, (account_id, account_id, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  ⚠️ 数据库更新失败: {e}")


def show_status():
    """显示当前活跃账号状态"""
    print(f"\n{'='*60}")
    print(f"📊 账号状态")
    print(f"{'='*60}")

    accounts = load_accounts_config()
    for acc in accounts:
        aid = acc['id']
        fp = get_fingerprint_for_account(aid)
        port = acc.get('port', 9222)

        # 检查 Chrome 是否运行
        pid = find_chrome_pid_on_port(port)
        running = pid is not None

        print(f"\n  📱 {aid}")
        print(f"     平台: {acc.get('platform', '?')}")
        print(f"     端口: {port}  {'✅ 运行中' if running else '⏹ 未运行'}")
        print(f"     指纹: {fp['id']} ({fp['viewport'][0]}x{fp['viewport'][1]})")
        print(f"     状态: {acc.get('enabled', True) and '启用' or '禁用'}")

        # 从数据库获取更多信息
        try:
            conn = sqlite3.connect(str(DB_PATH))
            row = conn.execute("SELECT status, last_active FROM accounts WHERE id=?", (aid,)).fetchone()
            conn.close()
            if row:
                print(f"     DB状态: {row[0]}  上次活跃: {row[1]}")
        except Exception:
            pass


def list_accounts():
    """列出所有已配置账号"""
    print(f"\n{'='*60}")
    print(f"📋 已配置账号")
    print(f"{'='*60}")

    accounts = load_accounts_config()
    for i, acc in enumerate(accounts):
        fp = get_fingerprint_for_account(acc['id'])
        print(f"\n  [{i+1}] {acc['id']}")
        print(f"      平台:    {acc.get('platform', '?')}")
        print(f"      手机:    {acc.get('phone', '?')}")
        print(f"      端口:    {acc.get('port', '?')}")
        print(f"      Profile: {acc.get('profile_dir', '?')}")
        print(f"      指纹:    {fp['id']}")
        print(f"      启用:    {'✅' if acc.get('enabled', True) else '❌'}")
        print(f"      备注:    {acc.get('notes', '')}")


# ══════════════════════════════════════════════════════════════
# CLI 入口
# ══════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description='Matrix 账号切换器')
    parser.add_argument('--method', choices=['profile', 'cookie'], default='profile',
                        help='切换方式: profile(重启Chrome) / cookie(注入Cookie)')
    parser.add_argument('--target', type=str, help='目标账号 ID')
    parser.add_argument('--port', type=int, default=9222, help='CDP 端口')
    parser.add_argument('--list', action='store_true', help='列出所有账号')
    parser.add_argument('--status', action='store_true', help='查看当前状态')
    parser.add_argument('--export-cookies', action='store_true', help='导出当前 Cookie')

    args = parser.parse_args()

    if args.list:
        list_accounts()
        return

    if args.status:
        show_status()
        return

    if not args.target:
        parser.print_help()
        print(f"\n⚠️ 请指定 --target 账号ID")
        print(f"   可用: {[a['id'] for a in load_accounts_config()]}")
        return

    if args.export_cookies:
        await export_cookies(args.target, args.port)
        return

    if args.method == 'profile':
        await switch_profile(args.target, args.port)
    elif args.method == 'cookie':
        await switch_cookie(args.target, args.port)


if __name__ == '__main__':
    asyncio.run(main())
