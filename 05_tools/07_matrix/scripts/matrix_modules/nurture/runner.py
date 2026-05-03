"""
常驻养号引擎 — 集成行为模拟参数化

使用方式（通过 matrix CLI）:
  matrix nurture run -a douyin_01
  matrix nurture loop -a douyin_01 -r 10
  matrix nurture run -a douyin_01 -a douyin_02 -a douyin_camo01  # 多账号并发
"""
import asyncio
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

# 路径注入
SCRIPTS_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from matrix_modules.nurture.behavior import BehaviorConfig

LOCAL_ROOT = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix"
SCRIPTS = SCRIPTS_DIR
BP_DIR = SCRIPTS_DIR.parent / "blueprints"
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def load_accounts_config() -> list:
    """加载 accounts.yaml 中的所有已启用抖音账号"""
    import yaml
    config_path = LOCAL_ROOT / "config" / "accounts.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return [a for a in data.get("accounts", [])
            if a.get("enabled") and a.get("platform") == "douyin"]


def get_account_config(account_id: str) -> dict:
    """根据账号ID获取配置"""
    for a in load_accounts_config():
        if a["id"] == account_id:
            return a
    return {}


def ensure_chrome(port: int, profile_dir: str):
    """确保 Chrome 在指定端口运行，没运行就启动"""
    import urllib.request
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://localhost:{port}/json/version", timeout=2):
            return  # 已在运行
    except:
        pass

    # 启动 Chrome
    profile_path = str(LOCAL_ROOT / "profiles" / profile_dir)
    cmd = [
        CHROME_BIN,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_path}",
        "--no-first-run", "--no-default-browser-check",
        "--window-size=702,783",
        "about:blank",
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"  🚀 启动 Chrome :{port} (profile: {profile_dir})")
    time.sleep(4)


async def _force_window_size(conn, engine: str, width: int, height: int):
    """Chrome CDP 强制设置窗口（仅 Chrome，Camoufox 用 window.open）"""
    if engine == "chrome" and conn.cdp_session:
        try:
            win_info = await conn.cdp_session.send("Browser.getWindowForTarget")
            win_id = win_info.get("windowId")
            if win_id:
                await conn.cdp_session.send("Browser.setWindowBounds", {
                    "windowId": win_id,
                    "bounds": {"width": width, "height": height}
                })
                print(f"  📐 Chrome 窗口: {width}×{height} (CDP)")
        except Exception as e:
            print(f"  ⚠️ Chrome CDP 调窗失败: {e}")


async def _camoufox_open_window(conn, width: int, height: int):
    """Camoufox: 通过 window.open 创建指定尺寸的新窗口
    Firefox 的 resizeTo 被 Playwright 禁用，但 window.open 尺寸参数原生生效
    """
    import asyncio

    # 监听新窗口事件
    new_page_future = asyncio.get_event_loop().create_future()
    def on_page(page):
        if not new_page_future.done():
            new_page_future.set_result(page)

    conn.context.on("page", on_page)

    # 创建指定尺寸的新窗口
    await conn.page.evaluate(f"""
        window.open('about:blank', 'main',
            'width={width},height={height},left=0,top=0,' +
            'menubar=no,toolbar=no,location=no,status=no');
    """)

    # 等待新窗口出现（最多5秒）
    try:
        new_page = await asyncio.wait_for(new_page_future, timeout=5)
    except asyncio.TimeoutError:
        # 如果事件没触发，检查已有 pages
        pages = conn.context.pages
        if len(pages) > 1:
            new_page = pages[-1]
        else:
            print(f"  ⚠️ 未能创建新窗口，使用原窗口")
            return None

    # 关闭旧窗口
    try:
        await conn.page.close()
    except:
        pass

    return new_page


def load_identity_config(identity_name: str) -> dict:
    """加载身份配置（含可选的行为覆盖）"""
    import yaml
    config_path = LOCAL_ROOT / "identities" / identity_name / "config.yaml"
    with open(config_path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_blueprint(name: str = "douyin_browse_v2") -> dict:
    """加载蓝图"""
    bp_file = BP_DIR / f"{name}.json"
    return json.loads(bp_file.read_text())


def get_user_data_dir(identity_name: str) -> str:
    """获取身份持久化目录"""
    return str(LOCAL_ROOT / "identities" / identity_name / "user_data")


# ── 日志工具 ─────────────────────────────────────

def _log(msg: str, log_file: str = None):
    """输出到 stdout 和日志文件"""
    print(msg)
    if log_file:
        try:
            with open(log_file, "a") as f:
                f.write(msg + "\n")
        except:
            pass


async def run_one_round(conn, page, behavior: BehaviorConfig, log_file: str = None):
    """单轮养号 —— 真人化流程

    流程：
    1. 进入推荐页
    2. 看5个视频（滑动切换），每个随机观看 4-15秒
    3. 5个中随机选1个点赞、1个收藏（可能相同）
    4. 在搜索框输入关键词 → 搜索 → 看结果视频
    """
    _log(f"  🔄 开始新一轮", log_file)

    # 回到首页
    await page.goto("https://www.douyin.com/", timeout=15000, wait_until="domcontentloaded")
    await asyncio.sleep(random.uniform(1, 2))
    try:
        await conn.remove_overlays()
    except:
        pass

    TOTAL_VIDEOS = 5

    # ── 先确定点赞/收藏位置（浏览前定好）──
    like_idx = random.randint(0, TOTAL_VIDEOS - 1)
    collect_idx = random.randint(0, TOTAL_VIDEOS - 1)

    # ── Phase 1: 浏览 5 个视频 ──
    # 抖音精选页使用瀑布流卡片（无 <a> 链接），需点击卡片进入视频
    for vi in range(TOTAL_VIDEOS):
        _log(f"    📹 视频 {vi+1}/{TOTAL_VIDEOS}", log_file)

        # 每次先回到 feed 首页（视频播放完回首页找下一个卡片）
        if vi > 0:
            await page.goto("https://www.douyin.com/", timeout=15000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(1.5, 3))

        # 找视频卡片并点击
        clicked = False
        try:
            # 先滚动加载更多卡片
            if vi > 0:
                await page.evaluate("window.scrollBy(0, 400)")
                await asyncio.sleep(1)

            clicked = await page.evaluate("""() => {
                // 尝试多种选择器找视频卡片
                const cards = document.querySelectorAll(
                    '.discover-video-card-item, ' +
                    '[class*=\"video-card\"], ' +
                    '[class*=\"VideoCard\"], ' +
                    '.waterfall-videoCardCon'
                );
                if (cards.length > 0) {
                    // 点击第1个
                    cards[0].click();
                    return true;
                }
                // 备选：找图片点击
                const imgs = document.querySelectorAll('[class*=\"video-card-img\"]');
                if (imgs.length > 0) {
                    imgs[0].click();
                    return true;
                }
                return false;
            }""")
        except:
            pass

        if not clicked:
            _log(f"      无法找到视频卡片，跳过", log_file)
            continue

        # 等待页面跳转到视频页
        await asyncio.sleep(random.uniform(2, 4))

        # 观看（随机 4-15 秒）
        watch_sec = random.uniform(4, 15)
        _log(f"      观看 {watch_sec:.0f}s...", log_file)
        await asyncio.sleep(watch_sec)

        # 点赞（如果这个视频被选中）
        if vi == like_idx:
            try:
                r = await page.evaluate("""() => {
                    const b = document.querySelector('[data-e2e="feed-active-video-double-like"]')
                        || document.querySelector('[data-e2e="like-count"]');
                    if (b) { b.click(); return 'ok'; }
                    return '-';
                }""")
                if r == 'ok':
                    _log(f"      👍 点赞 (第{vi+1}个)", log_file)
            except:
                pass
            await asyncio.sleep(random.uniform(0.5, 1.5))

        # 收藏（如果这个视频被选中）
        if vi == collect_idx:
            try:
                r = await page.evaluate("""() => {
                    const b = document.querySelector('[data-e2e="video-collect"]');
                    return b ? (b.click(), 'ok') : '-';
                }""")
                if r == 'ok':
                    _log(f"      ⭐ 收藏 (第{vi+1}个)", log_file)
            except:
                pass
            await asyncio.sleep(random.uniform(0.5, 1.5))

    # ── Phase 2: 搜索框搜索 ──
    search_keywords = ["搞笑", "美食", "旅行", "萌宠", "科技", "音乐", "舞蹈", "健身"]
    keyword = random.choice(search_keywords)
    _log(f"    🔍 搜索: {keyword}", log_file)

    try:
        # 在搜索框输入关键词
        await page.evaluate(f"""() => {{
            const input = document.querySelector('input[placeholder*="搜索"]');
            if (!input) return;
            // 设置值并触发事件
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            nativeInputValueSetter.call(input, '{keyword}');
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}""")
        await asyncio.sleep(random.uniform(0.5, 1))

        # 点击搜索按钮
        await page.evaluate("""() => {
            const btn = [...document.querySelectorAll('button')]
                .find(b => b.textContent.includes('搜索'));
            if (btn) btn.click();
        }""")
        await asyncio.sleep(random.uniform(2, 4))

        # 在搜索结果中点一个视频
        try:
            result_link = await page.evaluate("""() => {
                const links = [...document.querySelectorAll('a[href*="/video/"]')];
                return links.length > 0
                    ? links[Math.floor(Math.random() * Math.min(links.length, 3))].href
                    : null;
            }""")
            if result_link:
                await page.goto(result_link, timeout=15000, wait_until="domcontentloaded")
                search_watch = random.uniform(5, 12)
                _log(f"      搜索视频观看 {search_watch:.0f}s", log_file)
                await asyncio.sleep(search_watch)
        except:
            pass
    except Exception as e:
        _log(f"    ⚠️ 搜索异常: {type(e).__name__}", log_file)

    # 回到首页
    try:
        await conn.remove_overlays()
    except:
        pass

    return TOTAL_VIDEOS


async def _execute_op(page, conn, op: str, args: dict, behavior: BehaviorConfig):
    """(已弃用，保留为兼容) 由 run_one_round 替代"""
    return "deprecated"

    if op == "goto_home":
        await page.goto("https://www.douyin.com/", timeout=15000)
        return "home"

    elif op == "wait_watch":
        sec = behavior.watch_duration()
        await asyncio.sleep(sec)
        return f"watch({sec:.1f}s)"

    elif op in ("like",):
        r = await page.evaluate("""() => {
            const b = document.querySelector('[data-e2e="feed-active-video-double-like"]');
            if (b) { b.click(); return '👍'; }
            const b2 = document.querySelector('[data-e2e="like-count"]');
            if (b2) { b2.click(); return '👍'; }
            return '-';
        }""")
        # 点击后微停顿
        await asyncio.sleep(behavior.click_delay())
        return r

    elif op in ("collect",):
        r = await page.evaluate("""() => {
            const b = document.querySelector('[data-e2e="video-collect"]');
            return b ? (b.click(), '⭐') : '-';
        }""")
        await asyncio.sleep(behavior.click_delay())
        return r

    elif op in ("next_video", "swipe_next"):
        await page.evaluate("window.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown'}))")
        await asyncio.sleep(behavior.action_delay())
        return "↓next"

    elif op == "scroll_feed":
        dist = behavior.scroll_distance()
        await page.evaluate(f"window.scrollBy(0, {dist})")
        # 可能暂停
        if behavior.should_pause_scroll():
            await asyncio.sleep(behavior.scroll_pause())
        return f"scroll({dist})"

    elif op == "random_scroll":
        dist = random.randint(150, 500)
        await page.evaluate(f"window.scrollBy(0, {dist})")
        await asyncio.sleep(behavior.action_delay())
        return f"rscroll({dist})"

    elif op == "wait":
        await asyncio.sleep(behavior.sequence_gap())
        return "⏸"

    else:
        return f"skip({op})"


async def nurture_loop(identity_name: str,
                       blueprint_name: str = "douyin_browse_v2",
                       rounds: int = 10,
                       behavior_config: Optional[dict] = None,
                       headless: bool = False,
                       engine: str = "auto",
                       daemon: bool = False):
    """常驻养号主循环（支持 Chrome CDP + Camoufox 双引擎）

    Args:
        identity_name: 账号/身份名称
        blueprint_name: 蓝图名称
        rounds: 循环轮数
        behavior_config: 行为参数覆盖
        headless: 是否无头模式
        engine: 引擎 (auto/chrome/camoufox)
        daemon: 完成后是否保持浏览器连接不退出
    """
    from cdp_connector import CDPConnector

    # 获取账号配置
    acct = get_account_config(identity_name)
    if not acct:
        print(f"❌ 账号 '{identity_name}' 未在 accounts.yaml 中找到")
        return

    identity_dir = str(LOCAL_ROOT / "identities" / identity_name)
    config = load_identity_config(identity_name)

    # 确定引擎
    if engine == "auto":
        bt = acct.get("browser_type", "chrome")
        engine = "camoufox" if bt == "camoufox" else "chrome"

    # 加载行为配置
    identity_behavior = config.get("behavior", {})
    if behavior_config:
        identity_behavior.update(behavior_config)
    bhv = BehaviorConfig(identity_behavior)

    eng_name = "Chrome CDP" if engine == "chrome" else "Camoufox"
    # 获取窗口尺寸（从身份配置读取，默认702x783）
    cfg_win = config.get("window", [702, 783])
    if isinstance(cfg_win, (list, tuple)) and len(cfg_win) == 2:
        w_width, w_height = int(cfg_win[0]), int(cfg_win[1])
    else:
        w_width, w_height = 702, 783

    print(f"\n{'='*55}")
    print(f" 🦀 {identity_name} — {blueprint_name} ({rounds}轮) [{eng_name}]")
    if daemon:
        print(f"    模式: daemon (完成后保持连接)")
    print(f"    行为模式: behavior v1.0")
    print(f"{'='*55}")

    # ── 连接浏览器 ──
    if engine == "chrome":
        port = acct.get("port", 9222)
        profile_dir = acct.get("profile_dir", identity_name)
        ensure_chrome(port, profile_dir)
        conn = CDPConnector(port=port, headless=headless, window=(702, 783))
    else:
        conn = CDPConnector(
            identity_dir=identity_dir,
            headless=headless,
            window=(702, 783),
        )

    await conn.connect()
    await conn.init_anti_detection()

    # 强制设置窗口大小
    if engine == "camoufox":
        # Camoufox: 用 window.open 创建正确尺寸的物理窗口
        new_page = await _camoufox_open_window(conn, w_width, w_height)
        if new_page:
            conn.page = new_page
            # 新窗口的 viewport 由 Camoufox config 注入自动处理
            print(f"  📐 Camoufox 窗口: {w_width}×{w_height}")
    else:
        await _force_window_size(conn, engine, w_width, w_height)

    # 进入抖音首页
    await conn.page.goto("https://www.douyin.com/",
                         timeout=20000, wait_until="domcontentloaded")
    # 导航后重设反检测（确保 UA/触摸/视口全部生效）
    await conn.init_anti_detection()
    await asyncio.sleep(2)
    # 导航到目标页面后重新设置反检测（CDP 覆盖可能在跨域导航后失效）
    await conn.init_anti_detection()
    await asyncio.sleep(2)

    # 找视频进入播放页
    video_links = await conn.page.evaluate("""() => {
        const links = [...document.querySelectorAll('a[href*="/video/"]')];
        return [...new Set(links.map(a => a.href))].slice(0, 5);
    }""")
    if video_links:
        await conn.page.goto(random.choice(video_links),
                             timeout=15000, wait_until="domcontentloaded")
        # 视频页也重新设置
        await conn.init_anti_detection()
        await asyncio.sleep(bhv.click_delay())

    # ── 循环执行 —— 新流程（不依赖旧蓝图）──
    LOG_FILE = f"/tmp/matrix_nurture_{identity_name}.log"
    _log(f"  日志: {LOG_FILE}", LOG_FILE)

    passed_rounds = 0
    for r in range(1, rounds + 1):
        _log(f"\n{'='*40}", LOG_FILE)
        _log(f" 🔁 {identity_name} 第 {r}/{rounds} 轮", LOG_FILE)
        _log(f"{'='*40}", LOG_FILE)

        try:
            p = await run_one_round(conn, conn.page, bhv, LOG_FILE)
            passed_rounds += 1

            await conn.remove_overlays()

            if r < rounds:
                rest = bhv.round_break()
                _log(f"  ⏳ 休息 {rest:.0f}s...", LOG_FILE)
                await asyncio.sleep(rest)

        except Exception as e:
            _log(f"  ❌ 第 {r} 轮异常: {type(e).__name__}: {str(e)[:60]}", LOG_FILE)
            try:
                await conn.page.goto("https://www.douyin.com/",
                                     timeout=10000, wait_until="domcontentloaded")
            except:
                pass
            await asyncio.sleep(3)

    # ── 总结 ──
    elapsed = time.time() - getattr(nurture_multi, '_t_start', time.time())
    _log(f"\n{'='*40}", LOG_FILE)
    _log(f" 🏁 {identity_name} 养号完成 ({eng_name})", LOG_FILE)
    _log(f"    轮数: {passed_rounds}/{rounds}", LOG_FILE)
    _log(f"    浏览视频: ~{passed_rounds * 3} 个", LOG_FILE)
    _log(f"    耗时: {elapsed:.0f}s ({elapsed/60:.1f}min)", LOG_FILE)

    # ── Daemon 保持模式 ──
    if daemon:
        _log(f"    🔄 进入 daemon 保持模式", LOG_FILE)
        _log(f"      进程保持运行，浏览器保持连接", LOG_FILE)
        _log(f"      停止命令: matrix nurture stop {identity_name}", LOG_FILE)
        try:
            while True:
                await asyncio.sleep(30)
        except (asyncio.CancelledError, KeyboardInterrupt):
            _log(f"    ⏹ daemon 结束", LOG_FILE)
    else:
        _log(f"    (浏览器保持运行，Python退出)", LOG_FILE)
    _log(f"{'='*40}", LOG_FILE)


async def nurture_multi(identities: List[str],
                        blueprint_name: str = "douyin_browse_v2",
                        rounds: int = 10,
                        headless: bool = False,
                        engines: Optional[dict] = None,
                        daemon: bool = False):
    """多账号并发养号（支持每个账号指定引擎）

    Args:
        identities: 账号ID列表
        blueprint_name: 蓝图名称
        rounds: 循环轮数
        headless: 是否无头模式
        engines: {账号ID: 引擎名} 的字典
        daemon: 完成后是否保持浏览器连接不退出
    """
    nurture_multi._t_start = time.time()

    if engines is None:
        engines = {}

    tasks = []
    for name in identities:
        eng = engines.get(name, "auto")
        tasks.append(nurture_loop(
            identity_name=name,
            blueprint_name=blueprint_name,
            rounds=rounds,
            headless=headless,
            engine=eng,
            daemon=daemon,
        ))

    await asyncio.gather(*tasks)
