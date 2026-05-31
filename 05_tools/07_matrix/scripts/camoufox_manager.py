#!/usr/bin/env python3
"""
Camoufox 管理器 — 直接启动 + 终端保持

用法:
  python camoufox_manager.py --launch douyin_camo01    # 启动（终端保持）
  python camoufox_manager.py --list                    # 列出账号
  python camoufox_manager.py --export douyin_camo01    # 导出 Cookie
  python camoufox_manager.py --import douyin_camo01    # 导入 Cookie
  python camoufox_manager.py --verify douyin_camo01    # 验证登录
  python camoufox_manager.py --status douyin_camo01    # 检查状态
  python camoufox_manager.py --stop douyin_camo01      # 停止
"""
import argparse
import asyncio
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# 项目路径
from local_paths import config_path, profiles_path, data_path
CONFIG_PATH = config_path("accounts.yaml")
PROFILES_DIR = profiles_path()
COOKIE_STORAGE = data_path("cookies")
LOGIN_LOG = data_path("login_log.jsonl")
PID_DIR = data_path("camoufox_pids")


# ─── 配置加载 ────────────────────────────────────────────────────

def load_config():
    """加载 accounts.yaml"""
    try:
        import yaml
    except ImportError:
        print("❌ 需要 PyYAML: pip install pyyaml")
        sys.exit(1)
    with open(CONFIG_PATH, encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_account(account_id: str):
    """根据 ID 获取账号配置"""
    data = load_config()
    for acc in data.get('accounts', []):
        if acc.get('id') == account_id:
            # 合并全局 camoufox 配置
            camo_cfg = data.get('camoufox', {})
            if 'screen' not in acc and 'screen' in camo_cfg:
                acc['screen'] = camo_cfg['screen']
            if 'geo' not in acc and 'geo' in camo_cfg:
                acc['geo'] = camo_cfg['geo']
            return acc
    return None


# ─── 登录记录 ────────────────────────────────────────────────────

def log_login(account_id: str, platform: str, status: str, detail: str = ""):
    """记录登录状态到 login_log.jsonl"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "account_id": account_id,
        "platform": platform,
        "status": status,  # logged_in / logged_out / login_failed / cookie_restored
        "detail": detail,
    }
    with open(LOGIN_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def get_last_login(account_id: str):
    """获取账号最近一次登录记录"""
    if not LOGIN_LOG.exists():
        return None
    last = None
    for line in LOGIN_LOG.read_text(encoding='utf-8').splitlines():
        try:
            entry = json.loads(line)
            if entry.get('account_id') == account_id:
                last = entry
        except json.JSONDecodeError:
            continue
    return last


# ─── PID 管理 ────────────────────────────────────────────────────

def save_pid(account_id: str, pid: int):
    (PID_DIR / f"{account_id}.pid").write_text(str(pid))


def read_pid(account_id: str):
    pid_file = PID_DIR / f"{account_id}.pid"
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text().strip())
    except (ValueError, OSError):
        return None


def is_alive(pid: int):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ─── 核心：启动 Camoufox（直接模式，终端保持） ─────────────────────

async def launch_camoufox(account: dict):
    """启动 Camoufox 浏览器，终端保持运行，CDP 端口供外部连接"""
    from camoufox.async_api import AsyncCamoufox

    # 合并配置
    screen = account.get('screen', {'width': 702, 'height': 783})
    geo = account.get('geo', {'timezone': 'Asia/Shanghai', 'locale': 'zh-CN'})
    proxy = account.get('proxy')

    profile_dir = PROFILES_DIR / account.get('profile_dir', account['id'])
    profile_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 启动 Camoufox（{account['id']}，CDP 端口 {account['port']}）")
    print(f"   窗口: {screen['width']}x{screen['height']}")
    print(f"   地区: {geo.get('locale', 'zh-CN')} / {geo.get('timezone', 'Asia/Shanghai')}")
    print(f"   Profile: {profile_dir}")
    if proxy:
        print(f"   代理: {proxy}")

    # 不指定 executable_path，让 Camoufox 自动检测
    # （显式指定会导致 properties.json 路径查找错误）
    kwargs = {
        'headless': False,
        'window': (screen['width'], screen['height']),
        'locale': [geo.get('locale', 'zh-CN')],
        'args': [f'--remote-debugging-port={account["port"]}'],
        # 使用持久化 profile 目录，登录状态跨重启保持
        'persistent_context': True,
        'user_data_dir': str(profile_dir),
    }

    if proxy and isinstance(proxy, str) and proxy not in ('null', 'None', ''):
        kwargs['proxy'] = {'server': proxy}

    try:
        async with AsyncCamoufox(**kwargs) as browser:
            # Camoufox 启动后内部有浏览器子进程，通过 CDP 端口确认就绪
            cdp_ok = await _wait_for_cdp(account['port'], timeout=15)

            if cdp_ok:
                print(f"\n✅ Camoufox 就绪！CDP 端口 {account['port']} 可连接")
                log_login(account['id'], account.get('platform', ''), 'browser_started', f"port={account['port']}")
            else:
                print(f"\n⚠️  Camoufox 已启动，但 CDP 端口 {account['port']} 未就绪")
                print(f"   浏览器仍可用，但外部自动化可能需要直接操作")

            print(f"\n{'='*50}")
            print(f"  账号: {account['id']}")
            print(f"  CDP:  localhost:{account['port']}")
            print(f"  ⚠️  请勿关闭此终端，浏览器将保持运行")
            print(f"  Ctrl+C 可停止浏览器")
            print(f"{'='*50}\n")

            # 保持运行直到 Ctrl+C
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass

    except KeyboardInterrupt:
        print(f"\n🛑 停止 Camoufox（{account['id']}）...")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理 PID
        pid_file = PID_DIR / f"{account['id']}.pid"
        pid_file.unlink(missing_ok=True)


async def _wait_for_cdp(port: int, timeout: int = 10) -> bool:
    """等待 CDP 端口就绪"""
    import urllib.request
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for i in range(timeout * 2):
        try:
            with opener.open(f"http://localhost:{port}/json/version", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        await asyncio.sleep(0.5)
    return False


# ─── CDP 连接 ────────────────────────────────────────────────────

async def connect_cdp(port: int):
    """通过 CDP 连接已启动的 Camoufox 实例"""
    import urllib.request
    from patchright.async_api import async_playwright

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://localhost:{port}/json/version", timeout=5) as r:
            info = json.loads(r.read())
            ws_url = info.get("webSocketDebuggerUrl")
    except Exception as e:
        print(f"❌ CDP 端口 {port} 连接失败: {e}")
        return None

    if not ws_url:
        print(f"❌ 未获取到 WebSocket URL")
        return None

    pw = await async_playwright().start()
    try:
        browser = await pw.firefox.connect_over_cdp(ws_url)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        print(f"✅ 已连接 Camoufox（端口 {port}），页面: {page.url}")
        return page
    except Exception as e:
        print(f"❌ Playwright 连接失败: {e}")
        await pw.stop()
        return None


# ─── 登录验证 ────────────────────────────────────────────────────

async def verify_login(account_id: str):
    """验证登录状态并记录"""
    account = get_account(account_id)
    if not account:
        print(f"❌ 账号 {account_id} 不存在")
        return

    page = await connect_cdp(account['port'])
    if not page:
        return

    platform = account.get('platform', '')
    try:
        await page.goto('https://www.douyin.com/', wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(3)

        # 检测登录状态
        indicators = {
            'douyin': "[data-e2e='user-avatar']",
            'xiaohongshu': ".user-avatar, .reds-count",
            'zhihu': ".AppHeader-profile",
        }
        selector = indicators.get(platform)
        logged_in = False
        if selector:
            el = await page.query_selector(selector)
            logged_in = el is not None

        status = 'logged_in' if logged_in else 'logged_out'
        print(f"{'✅ 已登录' if logged_in else '❌ 未登录'}（{account_id}）")

        # 记录登录状态
        log_login(account_id, platform, status)
        return logged_in

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        log_login(account_id, platform, 'login_failed', str(e))
        return False


# ─── Cookie 管理 ─────────────────────────────────────────────────

async def export_cookies(account_id: str):
    """导出 Cookie 到文件"""
    account = get_account(account_id)
    if not account:
        print(f"❌ 账号 {account_id} 不存在")
        return

    page = await connect_cdp(account['port'])
    if not page:
        return

    cookies = await page.context.cookies()
    cookie_file = COOKIE_STORAGE / f"{account_id}_cookies.json"
    with open(cookie_file, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2, ensure_ascii=False)

    log_login(account_id, account.get('platform', ''), 'cookie_exported', f"count={len(cookies)}")
    print(f"✅ 导出 {len(cookies)} 个 Cookie → {cookie_file}")


async def import_cookies(account_id: str):
    """从文件导入 Cookie"""
    account = get_account(account_id)
    if not account:
        print(f"❌ 账号 {account_id} 不存在")
        return

    cookie_file = COOKIE_STORAGE / f"{account_id}_cookies.json"
    if not cookie_file.exists():
        print(f"❌ Cookie 文件不存在: {cookie_file}")
        return

    page = await connect_cdp(account['port'])
    if not page:
        return

    with open(cookie_file, encoding='utf-8') as f:
        cookies = json.load(f)

    await page.context.clear_cookies()
    await page.context.add_cookies(cookies)

    log_login(account_id, account.get('platform', ''), 'cookie_restored', f"count={len(cookies)}")
    print(f"✅ 导入 {len(cookies)} 个 Cookie")


# ─── 停止与状态 ──────────────────────────────────────────────────

async def stop_camoufox(account_id: str):
    """停止 Camoufox 进程"""
    pid = read_pid(account_id)
    if not pid:
        print(f"⚪ 无 PID 记录（{account_id}），可能未通过本脚本启动")
        return

    if not is_alive(pid):
        print(f"⚪ 进程已终止（PID {pid}）")
        (PID_DIR / f"{account_id}.pid").unlink(missing_ok=True)
        return

    try:
        os.kill(pid, signal.SIGINT)
        print(f"🛑 已发送停止信号（PID {pid}）")
        for _ in range(10):
            if not is_alive(pid):
                break
            time.sleep(0.5)
        else:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
        (PID_DIR / f"{account_id}.pid").unlink(missing_ok=True)
        print(f"✅ 已停止（{account_id}）")
    except OSError as e:
        print(f"❌ 停止失败: {e}")


async def check_status(account_id: str):
    """检查 Camoufox 运行状态"""
    account = get_account(account_id)
    if not account:
        print(f"❌ 账号 {account_id} 不存在")
        return

    pid = read_pid(account_id)
    running = pid and is_alive(pid)

    print(f"\n📋 账号: {account_id}")
    print(f"   平台: {account.get('platform', '?')}")
    print(f"   端口: {account.get('port', '?')}")
    print(f"   状态: {'🟢 运行中' if running else '⚪ 未运行'}")
    if running:
        print(f"   PID:  {pid}")

    # 最近登录记录
    last = get_last_login(account_id)
    if last:
        print(f"   最近: {last['status']} @ {last['timestamp'][:19]}")
        if last.get('detail'):
            print(f"   详情: {last['detail']}")


# ─── CLI ─────────────────────────────────────────────────────────

async def async_main():
    parser = argparse.ArgumentParser(
        description='Camoufox 管理器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python camoufox_manager.py --launch douyin_camo01    # 启动浏览器（终端保持）
  python camoufox_manager.py --list                    # 列出所有 Camoufox 账号
  python camoufox_manager.py --verify douyin_camo01    # 验证登录
  python camoufox_manager.py --export douyin_camo01    # 导出 Cookie
  python camoufox_manager.py --import douyin_camo01    # 导入 Cookie
  python camoufox_manager.py --status douyin_camo01    # 查看状态+登录记录
  python camoufox_manager.py --stop douyin_camo01      # 停止浏览器
""")
    parser.add_argument('--launch', type=str, help='启动指定账号（终端保持）')
    parser.add_argument('--list', action='store_true', help='列出所有 Camoufox 账号')
    parser.add_argument('--verify', type=str, help='验证登录状态')
    parser.add_argument('--export', type=str, help='导出 Cookie')
    parser.add_argument('--import', type=str, dest='import_', help='导入 Cookie')
    parser.add_argument('--status', type=str, help='查看账号状态')
    parser.add_argument('--stop', type=str, help='停止浏览器')

    args = parser.parse_args()

    if args.list:
        data = load_config()
        camo_accounts = [a for a in data.get('accounts', []) if a.get('browser_type') == 'camoufox']
        print(f"\n📋 Camoufox 账号（共 {len(camo_accounts)} 个）")
        print(f"{'ID':<20} {'平台':<8} {'端口':<6} {'状态'}")
        print("-" * 50)
        for acc in camo_accounts:
            pid = read_pid(acc['id'])
            status = "🟢 运行" if pid and is_alive(pid) else "⚪ 停止"
            print(f"{acc['id']:<20} {acc.get('platform', '?'):<8} {acc.get('port', '?'):<6} {status}")
        return

    if args.launch:
        account = get_account(args.launch)
        if not account:
            print(f"❌ 账号 {args.launch} 不存在")
            return
        await launch_camoufox(account)
        return

    if args.verify:
        await verify_login(args.verify)
        return

    if args.export:
        await export_cookies(args.export)
        return

    if args.import_:
        await import_cookies(args.import_)
        return

    if args.status:
        await check_status(args.status)
        return

    if args.stop:
        await stop_camoufox(args.stop)
        return

    parser.print_help()


def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
