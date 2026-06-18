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
import subprocess

# 路径注入
SCRIPTS_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from matrix_modules.nurture.behavior import BehaviorConfig

from matrix_mgmt import AGENT_LOCAL
LOCAL_ROOT = AGENT_LOCAL / "tools" / "matrix"
SCRIPTS = SCRIPTS_DIR
BP_DIR = SCRIPTS_DIR.parent / "blueprints"
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def _move_camoufox_window(identity_dir: str, target_left: int, target_top: int):
    """用 AppleScript 将对应 Camoufox 窗口移动到指定位置"""
    try:
        profile_path = identity_dir.rstrip('/') + '/user_data'
        # 通过 profile 路径匹配进程，然后移动其窗口
        script = f'''
set profilePath to "{profile_path}"
tell application "System Events"
    set procList to every process whose name contains "camoufox"
    repeat with proc in procList
        set pid to unix id of proc
        try
            set cmdLine to do shell script "ps -p " & pid & " -o command= 2>/dev/null | head -1"
            if cmdLine contains profilePath then
                set winList to every window of proc
                repeat with w in winList
                    set position of w to {{{target_left}, {target_top}}}
                end repeat
            end if
        end try
    end repeat
end tell
'''
        result = subprocess.run(['osascript', '-e', script],
                                capture_output=True, timeout=5, text=True)
        if result.returncode == 0:
            print(f"  🪟 窗口移至 ({target_left},{target_top})")
        else:
            print(f"  ⚠️ 窗口移动失败: {result.stderr[:80]}")
    except Exception as e:
        print(f"  ⚠️ 窗口移动异常: {e}")


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


async def _camoufox_open_window(conn, width: int, height: int, left: int = 0, top: int = 0):
    """Camoufox: 通过 window.open 创建指定尺寸和位置的新窗口"""
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
            'width={width},height={height},left={left},top={top},' +
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

    # 新窗口带到前端（确保后续操作有焦点）
    try:
        await new_page.bring_to_front()
    except:
        pass
    await asyncio.sleep(0.5)

    return new_page


def load_identity_config(identity_name: str, identity_dir_override: str = None) -> dict:
    """加载身份配置（含可选的行为覆盖）"""
    import yaml
    if identity_dir_override:
        config_path = Path(identity_dir_override) / "config.yaml"
    else:
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


async def _safe_goto(page, url: str, timeout: int = 15, conn=None):
    """安全导航——三级保底：goto → JS跳转 → CDP强制导航"""
    # 第一级：Playwright goto
    try:
        await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
        return True
    except Exception:
        pass

    # 第二级：JS 强制跳转
    try:
        await page.evaluate(f"window.location.href = '{url}'")
        await asyncio.sleep(3)
        return True
    except Exception:
        pass

    # 第三级：CDP 强制导航（页面完全卡死时的保底）
    try:
        if conn and hasattr(conn, 'cdp_session') and conn.cdp_session:
            await conn.cdp_session.send("Page.navigate", {"url": url})
            await asyncio.sleep(3)
            return True
    except Exception:
        pass

    return False



async def _activate_window():
    """用 AppleScript 激活 Camoufox 窗口（确保在最前端）"""
    try:
        script = 'tell application "System Events" to set frontmost of every process whose name contains "camoufox" to true'
        subprocess.run(['osascript', '-e', script], capture_output=True, timeout=3)
    except:
        pass


async def _dismiss_popups(page):
    """移除新手教学指引弹窗"""
    try:
        for text in ["我知道了", "关闭", "跳过", "下一步"]:
            btn = page.locator(f'button:has-text("{text}")').first
            if await btn.count() > 0:
                await btn.click()
                await asyncio.sleep(0.3)
    except:
        pass


SCREENSHOT_DIR = LOCAL_ROOT / "screenshots"


async def _take_screenshot(page, identity_name: str, label: str):
    """截图保存，供后续AI分析"""
    try:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%H%M%S")
        path = str(SCREENSHOT_DIR / f"{identity_name}_{label}_{ts}.png")
        await page.screenshot(path=path, full_page=False)
        return path
    except:
        return None


async def _check_anchor(page, anchor_type: str, timeout: float = 3.0) -> bool:
    """检测页面锚点，判断当前在什么状态

    anchor_type:
      - 'video_page': 是否在视频播放页（有video元素）
      - 'home_page':  是否在首页/精选页（有卡片列表）
      - 'video_playing': 视频是否正在播放
      - 'has_videos':  页面是否有视频链接
    """
    try:
        if anchor_type == 'video_page':
            vc = await asyncio.wait_for(
                page.evaluate("document.querySelectorAll('video').length"), timeout=timeout
            )
            return vc > 0
        elif anchor_type == 'home_page':
            has_cards = await asyncio.wait_for(
                page.evaluate("document.querySelectorAll('.discover-video-card-item').length > 0"),
                timeout=timeout
            )
            return has_cards
        elif anchor_type == 'video_playing':
            playing = await asyncio.wait_for(
                page.evaluate("""() => {
                    const v = document.querySelector('video');
                    return v ? !v.paused && v.readyState > 0 : false;
                }"""), timeout=timeout
            )
            return playing
        elif anchor_type == 'has_videos':
            links = await asyncio.wait_for(
                page.evaluate("document.querySelectorAll('a[href*=\"/video/\"]').length > 0"),
                timeout=timeout
            )
            return links
    except:
        pass
    return False


async def _retry_enter_video(conn, page, identity_name: str, log_file: str,
                              max_retries: int = 3) -> bool:
    """进入视频播放页（含锚点检测 + 重试 + 截图）

    流程：
    1. 导航到首页 → 检测首页锚点（卡片列表）
    2. 点击卡片 → 检测播放页锚点（video元素）
    3. 失败则刷新重试，3次仍失败则截图
    """
    for attempt in range(1, max_retries + 1):
        # 导航到首页
        _log(f"    📍 尝试进入播放页 ({attempt}/{max_retries})", log_file)
        ok = await _safe_goto(page, "https://www.douyin.com/", conn=conn)
        if not ok:
            _log(f"    ⚠️ 首页导航失败", log_file)
            continue
        await asyncio.sleep(random.uniform(2, 4))
        await _dismiss_popups(page)

        # 检测首页锚点
        if not await _check_anchor(page, 'home_page', timeout=5):
            _log(f"    ⚠️ 未检测到首页锚点（卡片列表）", log_file)
            continue

        # 窗口激活 + 双击卡片（确保播放）
        try:
            await _activate_window()
            card = page.locator('.discover-video-card-item').first
            if await card.count() == 0:
                continue
            await card.click()      # 第1次点击：打开播放
            await asyncio.sleep(1)
            await card.click()      # 第2次点击：确保播放（暂停→恢复）
            await asyncio.sleep(3)
        except:
            continue

        # 检测播放页锚点：video > 0
        if await _check_anchor(page, 'video_page', timeout=3):
            _log(f"    ✅ 进入播放页（video锚点确认）", log_file)
            # 点击视频区域确保焦点（让键盘事件正确路由到播放器）
            try:
                vid = page.locator('video').first
                if await vid.count() > 0:
                    box = await vid.bounding_box()
                    if box:
                        await page.mouse.click(box['x'] + box['width']//2,
                                               box['y'] + box['height']//3)
                        await asyncio.sleep(0.5)
            except:
                pass
            # 检查是否覆盖播放模式
            try:
                ac = await page.evaluate(
                    "document.querySelectorAll('.discover-video-card-item').length")
                if ac > 20:
                    _log(f"    📌 覆盖播放(cards={ac})", log_file)
            except:
                pass
            return True

        # 备选：直接导航到视频URL
        try:
            link = await page.evaluate(
                "document.querySelector('a[href*=\"/video/\"]')?.href"
            )
            if link:
                await _safe_goto(page, link, conn=conn)
                await asyncio.sleep(2)
                if await _check_anchor(page, 'video_page', timeout=3):
                    _log(f"    ✅ 视频URL导航进入播放页", log_file)
                    return True
        except:
            pass

        _log(f"    ⚠️ 第{attempt}次未进入播放页", log_file)

    # 3次全失败，截图让AI分析
    ss = await _take_screenshot(page, identity_name, "enter_fail")
    if ss:
        _log(f"    📸 截图已保存: {ss}", log_file)
    _log(f"    ❌ 连续{max_retries}次无法进入播放页，请检查截图", log_file)
    return False


async def _swipe_down(page, log_file: str) -> bool:
    """下滑切换视频（Playwright真实键盘）→ 检测video是否真正切换"""
    try:
        # 下滑前记录video状态
        before = await asyncio.wait_for(
            page.evaluate("""() => {
                const v = document.querySelector('video');
                return v ? {src: v.src, paused: v.paused, ready: v.readyState} : null;
            }"""), timeout=3
        )
        # 下滑切换视频：鼠标滚轮 + 键盘 ArrowDown 双重尝试
        try:
            await page.bring_to_front()
        except:
            pass

        # 方式A：鼠标滚轮（在覆盖播放模式下有效）
        await page.mouse.wheel(0, 800)
        await asyncio.sleep(2)
        after = await asyncio.wait_for(
            page.evaluate("""() => {
                const v = document.querySelector('video');
                return v ? {src: v.src, paused: v.paused, ready: v.readyState} : null;
            }"""), timeout=3
        )
        switched = False
        if before and after and after['src'] != before['src'] and after['src']:
            switched = True

        if not switched:
            # 方式B：键盘 ArrowDown
            await page.keyboard.press('ArrowDown')
            await asyncio.sleep(2)
            after = await asyncio.wait_for(
                page.evaluate("""() => {
                    const v = document.querySelector('video');
                    return v ? {src: v.src, paused: v.paused, ready: v.readyState} : null;
                }"""), timeout=3
            )
            if before and after and after['src'] != before['src'] and after['src']:
                switched = True

        if not switched:
            _log(f"    📊 src相同={before['src'][:30] if before else 'N/A'}...", log_file)
        return switched
    except Exception as e:
        _log(f"    ⚠️ 下滑异常: {str(e)[:30]}", log_file)
        return False


async def run_one_round(conn, page, behavior: BehaviorConfig, log_file: str = None,
                         identity_name: str = "unknown"):
    """单轮养号 —— 锚点驱动的视频浏览循环

    流程（原子化操作 + 锚点验证 + 重试）：
    1. 进入播放页（含3次重试 + 截图）
    2. 下滑看视频（含video切换锚点检测）
       - 间隔 8~20 秒（随机）
       - 每3~6个视频随机点赞
    3. 搜索
    """
    _log(f"  🔄 开始新一轮", log_file)

    # ── Step 1: 进入播放页（带锚点检测 + 重试）──
    entered = await _retry_enter_video(conn, page, identity_name, log_file)
    if not entered:
        return 0

    # ── Step 2: 下滑看视频（锚点驱动）──
    DURATION = 0.1  # 分钟（测试模式）
    start_ts = time.time()
    video_count = 0
    last_video_ts = time.time()
    _log(f"    📹 开始滑视频（{DURATION}min，间隔8~20s随机）", log_file)

    while time.time() - start_ts < DURATION * 60:
        # 看视频：8~20秒随机，足够看完一个短视频
        watch_sec = random.uniform(8, 20)
        await asyncio.sleep(watch_sec)
        video_count += 1
        _log(f"    📹 #{video_count} 看了{watch_sec:.0f}s", log_file)

        # 随机点赞（每3~6个视频）
        if video_count % random.randint(3, 6) == 0:
            try:
                btn = page.locator(
                    '[data-e2e="feed-active-video-double-like"], '
                    '[data-e2e="like-count"]'
                ).first
                if await btn.count() > 0:
                    await btn.click()
                    _log(f"      👍 #{video_count}", log_file)
                    await asyncio.sleep(random.uniform(1, 2))
            except:
                pass

        # 下滑切换（含video锚点检测）
        switched = await _swipe_down(page, log_file)
        if not switched:
            _log(f"    ⚠️ video未切换，尝试备用下滑", log_file)
            try:
                await page.keyboard.press('ArrowDown')
                await asyncio.sleep(2)
            except:
                # 下滑失败：回退到首页重试
                _log(f"    🔄 下滑连续失败，回退首页重试", log_file)
                recovered = await _retry_enter_video(
                    conn, page, identity_name, log_file, max_retries=1
                )
                if not recovered:
                    _log(f"    ❌ 无法恢复，退出本轮", log_file)
                    break

        # 进度报告
        if video_count % 8 == 0:
            elapsed = time.time() - start_ts
            _log(f"    📹 #{video_count} | 已过{elapsed/60:.0f}min", log_file)

    # ── Step 2.5: 播放页交互（随机点赞/评论/关注等）──
    await _player_interactions(page, identity_name, log_file, count=1)

    _log(f"    \u23f1\ufe0f 评论测试完成，停留5秒让你检查", log_file)
    await asyncio.sleep(5)
    return video_count

    # ── Step 3: 搜索 ──
    await _safe_goto(page, "https://www.douyin.com/", conn=conn)
    await asyncio.sleep(2)
    await _activate_window()
    keyword = random.choice(["搞笑", "美食", "旅行", "萌宠", "科技", "音乐"])
    _log(f"    🔍 搜索: {keyword}", log_file)
    try:
        # 输入关键词
        await page.evaluate(f"""() => {{
            const i = document.querySelector('input[placeholder*="搜索"]');
            if (!i) return;
            i.value = '{keyword}';
            i.dispatchEvent(new Event('input', {{bubbles: true}}));
        }}""")
        await asyncio.sleep(0.5)
        # 点击搜索按钮
        await page.evaluate("""() => {
            const b = [...document.querySelectorAll('button')]
                .find(b => b.textContent.includes('搜索'));
            if (b) b.click();
        }""")
        await asyncio.sleep(3)
        _log(f"    ✅ 搜索结果已加载", log_file)

        # 点击第一个搜索结果视频（窗口激活 + 双击）
        await _activate_window()
        clicked = False
        # 方式1: a[href*="/video/"] 点击
        link = page.locator('a[href*="/video/"]').first
        if await link.count() > 0:
            await link.click()
            await asyncio.sleep(1)
            await link.click()
            _log(f"    ▶️ 点击搜索结果视频(a标签)", log_file)
            clicked = True
        else:
            # 方式2: 找搜索容器中的第一个可点击卡片
            try:
                card = page.locator(
                    '[class*="search"] [class*="card"], '
                    '[class*="result"] a, '
                    '[class*="search"] a'
                ).first
                if await card.count() > 0:
                    await card.click()
                    await asyncio.sleep(1)
                    await card.click()
                    _log(f"    ▶️ 点击搜索卡片", log_file)
                    clicked = True
            except:
                pass

        if not clicked:
            # 方式3: JS 收集链接，导航到第一个
            link = await page.evaluate("""() => {
                const links = [...document.querySelectorAll('a[href*="/video/"]')];
                return links.length > 0 ? links[0].href : null;
            }""")
            if link:
                await _safe_goto(page, link, conn=conn)
                _log(f"    ▶️ 导航到搜索结果视频", log_file)
                clicked = True

        if not clicked:
            # 方式4: Tab+Enter 键盘导航到第一个结果
            for _ in range(5):
                await page.keyboard.press('Tab')
                await asyncio.sleep(0.3)
            await page.keyboard.press('Enter')
            await asyncio.sleep(3)
            v = await page.evaluate("document.querySelectorAll('video').length")
            if v >= 2:
                _log(f"    ▶️ Tab+Enter 进入搜索结果(video={v})", log_file)
                clicked = True

        if clicked:
            await asyncio.sleep(random.uniform(5, 10))
        else:
            _log(f"    ⚠️ 未找到搜索结果视频", log_file)
    except:
        _log(f"    ⚠️ 搜索异常", log_file)

    return video_count


# ── 评论状态机 ────────────────────────────────────────────

COMMENT_STATES = {
    "closed":       "评论区未打开",
    "panel_open":   "评论面板已打开",
    "input_focused": "输入框已聚焦",
    "text_entered": "文本已输入",
    "sent":         "评论已发送",
    "verify_code":  "验证码弹窗",
    "failed":       "操作失败",
}

COMMENT_TRANSITIONS = {
    "closed":       ["panel_open"],
    "panel_open":   ["input_focused"],
    "input_focused": ["text_entered"],
    "text_entered":  ["sent", "verify_code"],
    "sent":         [],   # 终态
    "verify_code":  [],   # 需要人工介入
}


class CommentStateMachine:
    """评论区状态机"""

    def __init__(self, page, log_file: str):
        self.page = page
        self.log_file = log_file
        self.state = "closed"
        self._history = []

    def _transition(self, to_state: str):
        """记录状态迁移"""
        self._history.append((self.state, to_state))
        _log(f"      🔄 状态: {self.state} → {to_state} ({COMMENT_STATES.get(to_state, '?')})",
             self.log_file)
        self.state = to_state

    async def detect(self) -> str:
        """检测当前评论区状态"""
        try:
            state_js = """() => {
                // 检测评论区面板
                const panel = document.querySelector('[class*="comment-header"]')
                    || document.querySelector('[class*="comment-input"]')
                    || document.querySelector('[class*="Comment"]')
                    || document.querySelector('[class*="chat"]')
                    || document.querySelector('[class*="commentContainer"]');

                // 检测编辑器
                const editor = document.querySelector('.public-DraftEditor-content')
                    || document.querySelector('[contenteditable="true"]')
                    || document.querySelector('[class*="DraftEditor"] [contenteditable]')
                    || document.querySelector('textarea')
                    || document.querySelector('input[type="text"]');

                // 检测 activeElement 是否可编辑
                const ae = document.activeElement;
                const editorActive = ae && (ae.isContentEditable
                    || ae.getAttribute('contenteditable') === 'true'
                    || ae.closest('[contenteditable]'));

                // 检测输入框是否有内容
                let hasText = false;
                if (editor) {
                    const txt = editor.textContent || '';
                    hasText = txt.trim().length > 0;
                }

                // 检测验证码弹窗
                const verifyInput = document.querySelector('input[placeholder*="验证码"]');

                // 检测评论是否已发送（页面文本中是否有刚发的评论—需要调用方传参）
                return {
                    has_panel: !!panel,
                    has_editor: !!editor,
                    editor_active: editorActive,
                    has_text: hasText,
                    has_verify: !!verifyInput,
                };
            }"""
            result = await asyncio.wait_for(
                self.page.evaluate(state_js), timeout=3
            )
        except Exception:
            result = {}

        # 状态推断
        if result.get("has_verify"):
            return "verify_code"
        if result.get("has_text") and result.get("editor_active"):
            return "text_entered"
        if result.get("editor_active"):
            return "input_focused"
        if result.get("has_panel") or result.get("has_editor"):
            return "panel_open"
        return "closed"

    async def ensure_open(self) -> bool:
        """确保评论区打开 → 返回是否成功"""
        detected = await self.detect()
        if detected == "verify_code":
            _log(f"      ⚠️ 检测到验证码弹窗，无法继续", self.log_file)
            self._transition("verify_code")
            return False
        if detected in ("panel_open", "input_focused", "text_entered"):
            _log(f"      ✅ 评论区已打开 (state={detected})", self.log_file)
            self._transition("panel_open")
            return True

        # 策略A: 键盘 'x' 键（先确保视频焦点）
        _log(f"      🖱️ 点击视频区域获取焦点", self.log_file)
        try:
            vid = self.page.locator('video').first
            if await vid.count() > 0:
                box = await vid.bounding_box()
                if box:
                    await self.page.mouse.click(
                        box['x'] + box['width'] // 2,
                        box['y'] + box['height'] // 3
                    )
                    await asyncio.sleep(0.5)
        except:
            pass

        _log(f"      ⌨️ 'x' 键打开评论区", self.log_file)
        try:
            await _activate_window()
            await asyncio.sleep(0.3)
            await self.page.keyboard.press('x')
            await asyncio.sleep(2)
        except Exception as e:
            _log(f"      ⚠️ 键盘异常: {str(e)[:30]}", self.log_file)

        # 验证
        detected = await self.detect()
        if detected in ("panel_open", "input_focused", "text_entered"):
            _log(f"      ✅ 键盘 'x' 打开评论区成功", self.log_file)
            self._transition("panel_open")
            return True

        # 策略B: DOM 找评论图标点击（兜底，与原 interact.comment 一致）
        _log(f"      🎯 DOM 找评论图标点击", self.log_file)
        try:
            clicked = await asyncio.wait_for(self.page.evaluate("""() => {
                const btn = document.querySelector('[data-e2e="video-comment-count"]');
                if (btn) { btn.click(); return true; }
                const btn2 = document.querySelector('[data-e2e="feed-comment-icon"]');
                if (btn2) { btn2.click(); return true; }
                // 也找 [class*="comment"] 的按钮
                const allBtns = [...document.querySelectorAll('button, a, [class*="comment"]')];
                const commentBtn = allBtns.find(el => {
                    const t = (el.textContent || '').toLowerCase();
                    return t.includes('评论') || el.className.includes('comment');
                });
                if (commentBtn) { commentBtn.click(); return true; }
                return false;
            }"""), timeout=5)
            if clicked:
                await asyncio.sleep(2)
                detected = await self.detect()
                if detected in ("panel_open", "input_focused", "text_entered"):
                    _log(f"      ✅ DOM 评论图标点击成功", self.log_file)
                    self._transition("panel_open")
                    return True
        except Exception as e:
            _log(f"      ⚠️ DOM 评论图标异常: {str(e)[:30]}", self.log_file)

        _log(f"      ❌ 评论区打开失败 (state={detected})", self.log_file)
        return False

    async def focus_input(self) -> bool:
        """聚焦输入框 → 双击模式

        双击之间不做任何操作（page.evaluate 会干扰焦点）。
        """
        detected = await self.detect()
        if detected == "input_focused":
            _log(f"      ✅ 输入框已聚焦（无需操作）", self.log_file)
            self._transition("input_focused")
            return True

        # 校验：必须在 panel_open 状态
        if detected != "panel_open":
            _log(f"      ⚠️ 不在 panel_open 状态 (state={detected})，跳过聚焦", self.log_file)
            return False

        # ── 策略1: Playwright locator 点编辑器（最接近真人操作）──
        _log(f"      🎯 Playwright locator 点编辑器", self.log_file)
        try:
            editor = self.page.locator('.public-DraftEditor-content').first
            if await editor.count() > 0:
                await editor.click(timeout=5000)
                await asyncio.sleep(0.5)
                await editor.click(timeout=5000)  # 双击
                await asyncio.sleep(0.5)
                detected = await self.detect()
                if detected == "input_focused":
                    _log(f"      ✅ Playwright 双击聚焦成功", self.log_file)
                    self._transition("input_focused")
                    return True
        except Exception as e:
            _log(f"      ⚠️ Playwright locator 异常: {str(e)[:30]}", self.log_file)

        # ── 策略2: DOM focus + click ──
        _log(f"      🎯 DOM 方式聚焦", self.log_file)
        dom_ok = await self._dom_focus_editor()
        if dom_ok:
            await asyncio.sleep(0.5)
            await self._dom_focus_editor()  # 第2次
            await asyncio.sleep(0.5)
            detected = await self.detect()
            if detected == "input_focused":
                _log(f"      ✅ DOM 聚焦成功", self.log_file)
                self._transition("input_focused")
                return True

        # ── 策略3: 坐标双击 ──
        _log(f"      🖱️ 坐标双击聚焦", self.log_file)
        await _activate_window()
        win_size = await self._get_window_size()
        from matrix_modules.nurture.ui_layout import calc_input_position
        tx, ty = calc_input_position(win_size["width"], win_size["height"])
        _log(f"      🖱️ 坐标 ({tx}, {ty})", self.log_file)

        await self.page.mouse.move(tx, ty, steps=8)
        await asyncio.sleep(0.3)
        await self.page.mouse.click(tx, ty)
        await asyncio.sleep(1)
        await self.page.mouse.click(tx, ty)
        await asyncio.sleep(0.5)

        detected = await self.detect()
        if detected == "input_focused":
            _log(f"      ✅ 坐标双击聚焦成功", self.log_file)
            self._transition("input_focused")
            return True

        _log(f"      ⚠️ 所有聚焦方式均失败 (state={detected})", self.log_file)
        return False

    async def _dom_focus_editor(self) -> bool:
        """通过 DOM focus() + click() 聚焦编辑器——排除不可见/隐藏元素"""
        js = """() => {
            // 只找可见的、有合理尺寸的编辑器
            const candidates = [
                document.querySelector('.public-DraftEditor-content'),
                document.querySelector('[contenteditable="true"][role="combobox"]'),
                document.querySelector('[data-e2e="comment-editor"] [contenteditable]'),
                document.querySelector('[class*="DraftEditor"] [contenteditable]'),
                document.querySelector('[contenteditable="true"]'),
            ].filter(el => {
                if (!el) return false;
                const r = el.getBoundingClientRect();
                return r.width > 20 && r.height > 10;  // 排除隐藏元素
            });
            if (candidates.length === 0) return JSON.stringify({ok: false, reason: 'no visible editor'});
            const ed = candidates[0];
            ed.focus();
            ed.click();
            ed.dispatchEvent(new Event('focus', {bubbles: true}));
            ed.dispatchEvent(new Event('click', {bubbles: true}));
            const rect = ed.getBoundingClientRect();
            return JSON.stringify({
                ok: true, tag: ed.tagName, cls: (ed.className||'').slice(0,30),
                ph: (ed.placeholder||''),
                x: Math.round(rect.left + rect.width/2),
                y: Math.round(rect.top + rect.height/2)
            });
        }"""
        try:
            result = await asyncio.wait_for(self.page.evaluate(js), timeout=3)
            parsed = json.loads(result)
            if parsed.get("ok"):
                _log(f"      DOM编辑器位置: ({parsed.get('x','?')}, {parsed.get('y','?')}) tag={parsed.get('tag','?')}",
                     self.log_file)
                return True
        except Exception as e:
            _log(f"      DOM focus 异常: {str(e)[:30]}", self.log_file)
        return False

    async def _get_window_size(self) -> dict:
        """获取浏览器 viewport 尺寸"""
        try:
            return await asyncio.wait_for(self.page.evaluate(
                "() => ({width: window.innerWidth, height: window.innerHeight})"
            ), timeout=3)
        except Exception:
            return {"width": 702, "height": 783}

    def get_history(self) -> list:
        return list(self._history)


async def _send_comment(page, log_file: str, window_size: tuple = None):
    """发送评论 —— 状态机版：三步走，每一步都验证

    流程:
      1. 状态检测 + 确保评论区打开
      2. DOM聚焦/坐标点击 + 输入文本
      3. 发送 + 验证

    每一步失败都有 fallback 策略：
      - Step 1 失败 → 重试 KeyX
      - Step 2 DOM 失败 → 坐标兜底
      - Step 3 DOM 发送失败 → Enter
    
    不依赖硬编码坐标。所有坐标从窗口右边缘动态计算。
    """
    from matrix_modules.nurture.comment_corpus import get_comment
    comment = get_comment(keyword="推荐")
    _log(f"    \U0001f4ac 评论状态机开始", log_file)
    _log(f"    \U0001f4ac 评论内容: \"{comment}\"", log_file)

    # 初始化状态机
    sm = CommentStateMachine(page, log_file)

    # ── Step 1: 打开评论区 ──
    _log(f"    ─── Step 1: 打开评论区 ───", log_file)
    opened = await sm.ensure_open()
    if not opened:
        # 重试一次
        _log(f"    🔄 重试: 再次 KeyX", log_file)
        await asyncio.sleep(1)
        opened = await sm.ensure_open()
        if not opened:
            _log(f"    ❌ 评论区打开失败，跳过评论", log_file)
            return False

    # ── Step 2: 聚焦输入框 + 输入文本 ──
    _log(f"    ─── Step 2: 聚焦 + 输入 ───", log_file)
    focused = await sm.focus_input()
    if not focused:
        _log(f"    ❌ 输入框聚焦失败，跳过评论", log_file)
        return False

    # 输入文本 — pbcopy + Meta+V（Draft.js 唯一可靠方式，keyboard.type 和 execCommand 均不触发 React 状态更新）
    _log(f"    ⌨️ 输入: \"{comment[:20]}\"...", log_file)
    try:
        import subprocess
        subprocess.run(['osascript', '-e', f'set the clipboard to "{comment}"'], timeout=5)
        await page.keyboard.press('Meta+v')
        await asyncio.sleep(1.5)
    except Exception as e:
        _log(f"      ⚠️ 粘贴异常: {str(e)[:30]}", log_file)

    # 验证编辑器内容
    try:
        has_text = await asyncio.wait_for(page.evaluate(
            "() => document.querySelector('.public-DraftEditor-content')?.textContent?.length > 0"
        ), timeout=3)
        _log(f"      🔍 输入确认: {'✅' if has_text else '❌'}", log_file)
    except:
        has_text = False

    if not has_text:
        _log(f"    ❌ 粘贴失败，跳过评论", log_file)
        return False

    # 等 React 处理
    await asyncio.sleep(1.5)

    sm._transition("text_entered")

    # ── Step 3: 发送 + 验证 ──
    _log(f"    ─── Step 3: 发送 ───", log_file)
    send_result = await _send_comment_execute(page, log_file)
    _log(f"      ��� 发送结果: {send_result}", log_file)

    if send_result == "verify_code":
        sm._transition("verify_code")
        _log(f"    ⚠️ 验证码弹窗，自动获取验证码", log_file)
        ok = await _check_verify_code(page, log_file)
        if ok:
            _log(f"    ✅ 验证码已提交", log_file)
            sm._transition("sent")
            return True
        else:
            _log(f"    ⚠️ 验证码处理失败", log_file)
            return "verify_code"

    # 等待页面更新
    await asyncio.sleep(3)

    # 验证：检查评论列表区域是否有刚发的评论（避免输入框内容误判）
    try:
        found = await asyncio.wait_for(page.evaluate(
            f"() => {{ const list = document.querySelector('[data-e2e=\"comment-list\"]') || document.querySelector('[class*=\"comment-list\"]') || document.body; return list.innerText.includes('{comment}'); }}"
        ), timeout=3)
        _log(f"      🔍 页面出现评论: {'✅' if found else '❌'}", log_file)
    except:
        found = False

    if found:
        sm._transition("sent")
        _log(f"    ✅ 评论发送并确认！", log_file)
        return True
    else:
        _log(f"    ⚠️ 评论发送后未在页面找到", log_file)
        return True  # 乐观返回：可能未被刷新渲染


async def _send_comment_execute(page, log_file: str) -> str:
    """执行发送操作：找发送按钮 → Ctrl+Enter → Alt+Enter

    Returns:
        'ok' | 'verify_code' | 'failed'
    """
    # 尝试3次找发送按钮（React 可能需要时间更新 UI）
    for attempt in range(3):
        try:
            send_btn = await asyncio.wait_for(page.evaluate("""() => {
                // 找发送/确认按钮（可能在上箭头图标上）
                const btns = [...document.querySelectorAll('button, [class*="send"], [class*="submit"], [class*="confirm"]')];
                const send = btns.find(b =>
                    (b.textContent || '').includes('发送')
                    || (b.textContent || '').includes('发布')
                    || b.className.includes('send')
                    || b.className.includes('submit')
                    || b.className.includes('confirm')
                    || (b.querySelector('svg') && b.className.includes('arrow'))  // 上箭头图标
                );
                if (send) {
                    send.click();
                    return 'clicked';
                }
                return 'not_found';
            }"""), timeout=3)
            if send_btn == 'clicked':
                _log(f"      第{attempt+1}次尝试: 找到发送按钮 ✅", log_file)
                break
        except:
            pass
        await asyncio.sleep(0.5)
    else:
        _log(f"      发送按钮未找到，键盘兜底", log_file)
        # 键盘兜底：Enter（2026-05-15 从 Alt+Enter 改为 Enter，适配新版发送）
        try:
            await page.keyboard.press('Enter')
            _log(f"      ⌨️ Enter 触发", log_file)
        except:
            pass

    await asyncio.sleep(2)

    # 验证码检测
    try:
        has_code = await asyncio.wait_for(page.evaluate(
            "() => !!document.querySelector('input[placeholder*=\"\\u9a8c\\u8bc1\\u7801\"]')"
        ), timeout=3)
        if has_code:
            return "verify_code"
    except:
        pass

    return "ok"
async def _check_verify_code(page, log_file: str):
    """检测验证码弹窗，自动获取并回填验证码"""
    try:
        has_popup = await page.evaluate("""() => {
            return !!(document.querySelector('input[placeholder*="验证码"]')
                   || document.querySelector('[class*="verify"]')
                   || document.body.innerText.includes('验证码已发送'));
        }""")
        if not has_popup:
            return False

        _log(f"    ⚠️ 检测到验证码弹窗！", log_file)

        # 自动获取验证码（API 轮询）
        from matrix_modules.account.sms import ApiSMSHandler
        handler = ApiSMSHandler()
        code = await handler.wait("抖音", timeout=120)

        if not code or len(code) not in (4, 5, 6):
            _log(f"    ⏰ 未获取到有效验证码({code})，跳过", log_file)
            # fallback: 手动输入
            import sys
            print("\n⚠️  API 未获取到验证码，请手动输入")
            sys.stdout.write("验证码: "); sys.stdout.flush()
            code = sys.stdin.readline().strip()
            if len(code) not in (4, 5, 6):
                return False

        # 回填验证码
        _log(f"    📝 回填验证码: {code}", log_file)
        await page.evaluate(f"""() => {{
            const inp = document.querySelector('input[placeholder*="验证码"]');
            if (inp) {{
                inp.value = '{code}';
                inp.dispatchEvent(new Event('input', {{bubbles: true}}));
            }}
        }}""")
        await asyncio.sleep(0.5)

        # 点击确认/提交
        confirm = page.locator(
            'button:has-text("确认"), '
            'button:has-text("提交"), '
            'button:has-text("验证")'
        ).first
        if await confirm.count() > 0:
            await confirm.click()
            _log(f"    ✅ 验证码已提交", log_file)

        await asyncio.sleep(2)
        return True

    except Exception as e:
        _log(f"    ⚠️ 验证码处理异常: {str(e)[:30]}", log_file)
        return False


# ── 页面级状态检测 ───────────────────────────────────────

PAGE_STATES = {
    "unknown":      "未知页面",
    "grid":         "首页/精选页（卡片列表）",
    "player":       "视频播放页（有 video 元素）",
    "search":       "搜索结果页",
    "search_player": "搜索结果中的播放页",
    "profile":      "个人主页",
}


async def _detect_page_state(page) -> str:
    """检测当前页面状态（与原 _check_anchor 风格一致）

    播放页判定：有 video 元素即视为播放页（与 _check_anchor('video_page') 一致）
    """
    try:
        js = """() => {
            const url = location.href;
            const vc = document.querySelectorAll('video').length;
            const cards = document.querySelectorAll('.discover-video-card-item, [data-e2e="alink-item"]').length;
            const title = document.title || '';

            // 有 video → 播放页（jingxuan 页点击卡片后也会打开视频）
            if (vc > 0) return 'player';

            // 搜索页
            if (url.includes('/search/') || document.querySelector('[data-e2e="searchbar-input"]')) {
                if (vc > 0) return 'search_player';
                return 'search';
            }
            // 首页：有卡片列表
            if (cards > 0 || title.includes('精选') || title.includes('推荐')) return 'grid';
            // 个人主页
            if (url.includes('/user/')) return 'profile';
            return 'unknown';
        }"""
        return await asyncio.wait_for(page.evaluate(js), timeout=3)
    except Exception:
        return "unknown"


async def _ensure_player_state(page, identity_name: str, log_file: str) -> bool:
    """确保在视频播放页（与原 _retry_enter_video 风格一致）

    流程：
      1. 检测是否有 video → 有则已播放页
      2. 没有 → 导航 douyin.com → 点卡片（与原流程一致）
      3. 验证：video > 0
    """
    # 快速检测：有 video 就认为是播放页
    vc = await _check_anchor(page, 'video_page', timeout=3)
    if vc:
        _log(f"    ✅ 已有视频播放页 (video={vc})", log_file)
        return True

    # 没有 video → 需要进入播放页
    _log(f"    🔄 没有视频，进入播放页...", log_file)
    try:
        for attempt in range(3):
            await _safe_goto(page, "https://www.douyin.com/?recommend=1", timeout=15)
            await asyncio.sleep(random.uniform(2, 4))
            await _dismiss_popups(page)

            # 找卡片（与原 _retry_enter_video 相同）
            card = page.locator('.discover-video-card-item').first
            cc = await card.count()
            if cc == 0:
                _log(f"    ⚠️ 未找到卡片 (attempt={attempt})", log_file)
                continue

            await _activate_window()
            await card.click()
            await asyncio.sleep(1)
            await card.click()
            await asyncio.sleep(3)

            vc = await _check_anchor(page, 'video_page', timeout=3)
            if vc:
                # 点视频区域获取焦点（与原流程相同）
                try:
                    vid = page.locator('video').first
                    if await vid.count() > 0:
                        box = await vid.bounding_box()
                        if box:
                            await page.mouse.click(box['x'] + box['width']//2,
                                                   box['y'] + box['height']//3)
                except:
                    pass
                _log(f"    ✅ 进入播放页成功", log_file)
                return True

            _log(f"    ⚠️ 第{attempt+1}次未进入播放页", log_file)

    except Exception as e:
        _log(f"    ⚠️ 进入播放页异常: {str(e)[:40]}", log_file)

    _log(f"    ❌ 无法进入播放页", log_file)
    return False


async def _player_interactions(page, identity_name: str, log_file: str,
                                 count: int = 4):
    """播放页交互阶段：状态感知 + 行为链执行

    流程:
      0. 检测并确保在播放页（不在则恢复）
      1. 随机选择行为链或单步操作
      2. 每步验证是否成功

    行为链 = 一组顺序相关的操作
    使用抖音快捷键（比DOM选择器更可靠）
    """
    # ── Step 0: 确保在播放页 ──
    _log(f"    🎮 播放页交互 ×{count}", log_file)
    ok = await _ensure_player_state(page, identity_name, log_file)
    if not ok:
        _log(f"    ❌ 不在播放页，跳过交互", log_file)
        return

    # ── 原子操作库 ──
    SINGLE_OPS = [
        ('like',           'KeyZ', 5),           # 点赞（高频）
        ('follow',         'KeyG', 2),            # 关注
        ('seek_fwd',       'ArrowRight', 2),      # 快进
        ('seek_bwd',       'ArrowLeft', 2),       # 快退
        ('toggle_loop',    'KeyP', 1),             # 连播
        ('toggle_mute',    'KeyM', 1),             # 静音
        ('toggle_display', 'KeyJ', 1),             # 清屏
    ]

    # ── 行为链 ──
    CHAINS = [
        # 评论链（发一条评论 + 看评论 + 关闭）
        [
            ('open_comment', 'KeyX'),
            ('type_comment', 'input'),
            ('wait_10s', 'wait'),
            ('scroll_comment', 'scroll'),
        ],
    ]

    for i in range(count):
        await asyncio.sleep(random.uniform(1.5, 4))

        # 先检测当前页面状态，每轮保证在播放页
        state = await _detect_page_state(page)
        if state not in ("player", "search_player"):
            _log(f"    ⚠️ 第{i+1}轮不在播放页(state={state})，尝试恢复", log_file)
            recovered = await _ensure_player_state(page, identity_name, log_file)
            if not recovered:
                _log(f"    ❌ 无法恢复播放页，跳过剩余交互", log_file)
                break

        # 执行行为链
        if CHAINS:
            chain = random.choice(CHAINS)
            _log(f"      🔗 行为链 #{CHAINS.index(chain)+1}", log_file)
            for op_name, method in chain:
                await asyncio.sleep(random.uniform(0.5, 1.5))
                try:
                    if method == 'scroll':
                        await page.mouse.wheel(0, random.randint(200, 600))
                        await asyncio.sleep(random.uniform(0.5, 1))
                        await page.mouse.wheel(0, random.randint(100, 400))
                        _log(f"        📜 {op_name}", log_file)
                    elif method == 'dom':
                        btn = page.locator(
                            'button:has-text("收藏"), '
                            '[class*="collect"], '
                            '[title*="收藏"]'
                        ).first
                        if await btn.count() > 0:
                            await btn.click()
                            _log(f"        🎯 {op_name} (dom)", log_file)
                        else:
                            _log(f"        ⚠️ {op_name} 未找到dom", log_file)
                    elif method == 'wait':
                        _log(f"        ⏳ 等待10秒让你检查...", log_file)
                        await asyncio.sleep(10)
                    elif method == 'input':
                        if op_name == 'type_comment':
                            await _send_comment(page, log_file)
                        else:
                            _log(f"        ⚠️ 未知input操作: {op_name}", log_file)
                    else:
                        await page.keyboard.press(method)
                        _log(f"        🎯 {op_name} ({method})", log_file)
                except Exception as e:
                    _log(f"        ⚠️ {op_name}: {str(e)[:20]}", log_file)
        else:
            # 单个随机操作
            op_name, method, _ = random.choices(
                SINGLE_OPS, weights=[w for _,_,w in SINGLE_OPS], k=1
            )[0]
            try:
                await page.keyboard.press(method)
                _log(f"      🎯 {op_name} ({method})", log_file)
            except Exception as e:
                _log(f"      ⚠️ {op_name}: {str(e)[:20]}", log_file)


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

    # 确定真实身份目录：优先使用 accounts.yaml 中的 identity_dir
    custom_identity = acct.get("identity_dir")
    if custom_identity:
        custom_path = LOCAL_ROOT / custom_identity
        if custom_path.exists():
            identity_dir = str(custom_path)
        else:
            identity_dir = str(LOCAL_ROOT / "identities" / identity_name)
    else:
        identity_dir = str(LOCAL_ROOT / "identities" / identity_name)

    config = load_identity_config(identity_name, identity_dir_override=identity_dir)

    # 确定引擎：有 identity_dir 就用 Camoufox，否则按 browser_type 判断
    if engine == "auto":
        if acct.get("identity_dir"):
            engine = "camoufox"
        else:
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
    # 获取窗口位置（从 accounts.yaml 读取，保存窗口位置记忆）
    win_pos = acct.get("window_position", [0, 0])
    if isinstance(win_pos, (list, tuple)) and len(win_pos) == 2:
        w_left, w_top = int(win_pos[0]), int(win_pos[1])
    else:
        w_left, w_top = 0, 0

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
            window_position=(w_left, w_top),
        )

    await conn.connect()
    await conn.init_anti_detection()

    # Camoufox: 窗口位置由用户手动调整，脚本启动时不自动移动
    # （AppleScript 定位不准确，用户已反馈）
    if engine == "camoufox":
        print(f"  📐 Camoufox 窗口: {w_width}×{w_height}")
    else:
        await _force_window_size(conn, engine, w_width, w_height)

    # 进入抖音首页
    await _safe_goto(conn.page, "https://www.douyin.com/", conn=conn)
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
        await _safe_goto(conn.page, random.choice(video_links), conn=conn)
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
            p = await run_one_round(conn, conn.page, bhv, LOG_FILE, identity_name=identity_name)
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

    # 保存窗口位置
    # 窗口位置固定使用 accounts.yaml 中的配置值，不保存回写
    # （Camoufox 启动偏移会导致保存的坐标偏离预期，每次启动都应从配置读取）

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


# ════════════════════════════════════════════════════════════
#  小红书养号 Runner
# ════════════════════════════════════════════════════════════

async def nurture_xhs_loop(
    identity_name: str,
    rounds: int = 10,
    headless: bool = False,
    behavior_config: dict = None,
    daemon: bool = False,
    use_ai_comments: bool = False,
):
    """小红书单账号养号循环

    设计原则（抖音踩坑防护）:
    1. 每步操作独立 try/except，失败不崩流程
    2. 操作前后锚点验证
    3. 3 次连续失败 → 截图 → 暂停
    4. 运行完关闭浏览器（不 daemon，节省资源）
    5. 强制使用 agent-os venv Python

    Args:
        use_ai_comments: 使用 AI 生成评论（需 oMLX 模型运行中）
    """
    import sys
    exe = sys.executable
    if "agent-os" not in exe:
        print(f"❌ 必须使用 agent-os venv Python: {exe}")
        sys.exit(1)

    # 加载账号配置
    import yaml
    config_path = LOCAL_ROOT / "config" / "accounts.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    acct = None
    for a in data.get("accounts", []):
        if a["id"] == identity_name:
            acct = a
            break

    if not acct:
        print(f"❌ 账号 {identity_name} 未找到")
        return

    if acct.get("platform") != "xiaohongshu":
        print(f"❌ 账号 {identity_name} 平台不是 xiaohongshu")
        return

    # 获取身份目录
    identity_dir = acct.get("identity_dir", identity_name)
    if not identity_dir.startswith("/"):
        identity_dir = str(LOCAL_ROOT / identity_dir)

    # 窗口配置
    win_pos = acct.get("window_position", [0, 0])
    w_left, w_top = int(win_pos[0]), int(win_pos[1]) if isinstance(win_pos, (list, tuple)) else (0, 0)

    # 加载行为配置
    from matrix_modules.nurture.behavior import BehaviorConfig
    bhv = BehaviorConfig(behavior_config)

    # 日志文件
    LOG_FILE = f"/tmp/matrix_nurture_xhs_{identity_name}.log"
    def _xhs_log(msg):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        try:
            with open(LOG_FILE, "a") as f:
                f.write(line + "\n")
        except:
            pass

    _xhs_log(f"{'='*55}")
    _xhs_log(f" 🦀 {identity_name} — 小红书养号 ({rounds}轮) [Camoufox]")
    _xhs_log(f"{'='*55}")

    # 导入小红书操作模块
    from matrix_modules.ops.xhs import browse, interact
    from matrix_modules.comment.xhs.corpus import random_comment, reset_session
    from matrix_modules.ops.xhs.selectors import ANCHORS

    # 重置评论去重（新账号新会话）
    reset_session()

    # 连接浏览器
    from cdp_connector import CDPConnector
    conn = CDPConnector(
        identity_dir=identity_dir,
        headless=headless,
        window=(702, 783),
        window_position=(w_left, w_top),
    )

    # 清理锁文件（直接路径，不递归扫 22k+ 文件）
    for lock in ['.parentlock', '.startup-incomplete', 'lock']:
        try:
            lf = Path(identity_dir) / 'user_data' / lock
            if lf.exists():
                lf.unlink()
                print(f"  🧹 清理锁文件: {lock}")
        except:
            pass

    try:
        await conn.connect()
    except Exception as e:
        _xhs_log(f"❌ 浏览器连接失败: {e}")
        return

    # 反检测
    try:
        await conn.init_anti_detection()
    except Exception as e:
        _xhs_log(f"⚠️ 反检测初始化失败: {e}")

    # 进入小红书首页（带重试，P1 #9）
    for attempt in range(1, 4):
        try:
            await browse.goto_home(conn.page)
            await asyncio.sleep(3)
            # 关闭登录弹窗
            await browse.dismiss_login_modal(conn.page)
            await asyncio.sleep(1)
            # 重初始化反检测
            try:
                await conn.init_anti_detection()
            except Exception:
                pass
            break
        except Exception as e:
            _xhs_log(f"❌ 首页导航失败 (第{attempt}次): {e}")
            if attempt < 3:
                await asyncio.sleep(3)
            else:
                await conn.close()
                return

    # 验证首页锚点
    is_home = await browse.check_anchor(conn.page, "home_page")
    if not is_home:
        _xhs_log(f"⚠️ 首页锚点验证失败，尝试点击刷新按钮...")
        refreshed = await browse.click_refresh_button(conn.page)
        if not refreshed:
            _xhs_log(f"  ⚠️ 未找到刷新按钮，fallback 到 reload()")
            await conn.page.reload()
        else:
            _xhs_log(f"  ✅ 已点击刷新按钮")
        await asyncio.sleep(3)
        try:
            await conn.init_anti_detection()
        except Exception:
            pass

    # ── 登录态检查（P0 #14）──
    _xhs_log(f"  🔐 检测登录状态...")
    try:
        from auth_manager import check_login_by_cookie_sync, get_session_id, count_platform_cookies
        cookies = await conn.context.cookies()
        logged_in = check_login_by_cookie_sync(cookies, "xiaohongshu")
        session_val = get_session_id(cookies, "xiaohongshu")
        cookie_cnt = count_platform_cookies(cookies, "xiaohongshu")
        if logged_in:
            _xhs_log(f"  ✅ 登录检测: 已登录 (cookies={cookie_cnt})")
            if session_val:
                _xhs_log(f"     session: {session_val[:20]}...")
        else:
            _xhs_log(f"  ⚠️ 登录检测: 未登录 (cookie_count={cookie_cnt})")
            _xhs_log(f"     允许未登录浏览，但评论/互动可能受限")
            # 截图供参考
            try:
                ss_path = f"/tmp/xhs_login_check_{identity_name}.png"
                await conn.page.screenshot(path=ss_path)
                _xhs_log(f"     📸 截图: {ss_path}")
            except:
                pass
    except Exception as e:
        _xhs_log(f"  ⚠️ 登录态检测异常: {e}")

    # 记录开始时间（P0 #4）
    _t_start = time.time()
    passed_rounds = 0
    consecutive_failures = 0

    for r in range(1, rounds + 1):
        _xhs_log(f"\n{'='*40}")
        _xhs_log(f" 🔁 {identity_name} 第 {r}/{rounds} 轮")
        _xhs_log(f"{'='*40}")

        round_ok = True
        try:
            # ── Step 0: 强制刷新瀑布流页面（每轮必执行）──
            _xhs_log("  🔄 刷新瀑布流页面...")
            refreshed = await browse.click_refresh_button(conn.page)
            if refreshed:
                _xhs_log("  ✅ 已点击刷新按钮")
                await asyncio.sleep(2)
            else:
                _xhs_log("  ⚠️ 未找到刷新按钮，跳过（页面可能已正常）")
            await asyncio.sleep(bhv.click_delay())

            # ── Step 1: 瀑布流浏览 ──
            _xhs_log("  📜 瀑布流浏览...")
            await browse.scroll_feed_human(conn.page, screens=random.randint(1, 3))
            await asyncio.sleep(bhv.click_delay())

            # ── Step 2: 点击笔记卡片 ──
            _xhs_log("  🎯 点击笔记卡片...")
            note_url = await browse.click_note_card(conn.page)
            if not note_url:
                _xhs_log("  ⚠️ 未找到可点击的笔记")
                round_ok = False
            else:
                _xhs_log(f"  ✅ 进入笔记: {note_url[:60]}...")
                await asyncio.sleep(bhv.click_delay())

                # 验证详情页锚点
                is_detail = await browse.check_anchor(conn.page, "note_detail")
                if not is_detail:
                    _xhs_log("  ⚠️ 详情页锚点验证失败")

                # ── Step 3: 浏览内容 ──
                watch_time = await browse.browse_note_detail(conn.page)
                _xhs_log(f"  👀 浏览 {watch_time:.0f}s")

                # ── Step 4: 随机互动 ──
                interact_result = await interact.random_interact(conn.page)
                actions = []
                if interact_result.get("like"):
                    actions.append("点赞")
                if interact_result.get("collect"):
                    actions.append("收藏")
                if interact_result.get("follow"):
                    actions.append("关注")
                if actions:
                    _xhs_log(f"  ❤️ 互动: {' '.join(actions)}")

                # ── Step 5: 评论（每 3 轮 1 次）──
                if r % 3 == 0:
                    _xhs_log("  💬 尝试评论...")
                    if use_ai_comments:
                        # AI 生成评论（P2 #17）
                        try:
                            from matrix_modules.comment.ai_generator import AICommentGenerator
                            ig = AICommentGenerator()
                            note_info = await conn.page.evaluate("""
                            () => {
                                const t = document.querySelector('.title, h1, [class*=note-title]');
                                const c = document.querySelector('.content, .desc, [class*=content]');
                                return {
                                    title: t ? t.textContent.trim().substring(0, 80) : '',
                                    content: c ? c.textContent.trim().substring(0, 150) : '',
                                };
                            }
                            """)
                            comment_text = ig.generate_with_context(
                                note_title=note_info.get("title", ""),
                                note_content=note_info.get("content", ""),
                            )
                        except Exception:
                            comment_text = random_comment()
                    else:
                        comment_text = random_comment()
                    comment_result = await interact.comment(conn.page, comment_text)
                    if comment_result.get("success"):
                        _xhs_log(f"  ✅ 评论发送: {comment_text}")
                    else:
                        _xhs_log(f"  ⚠️ 评论失败: {comment_result.get('error', 'unknown')}")

                # ── Step 6: 检测 QR 墙 → 返回首页 ──
                _xhs_log("  🔙 返回首页...")
                # 先检测是否有 QR 检测墙弹窗
                qr_back = await browse.click_qr_wall_back_button(conn.page)
                if qr_back:
                    _xhs_log("  ✅ 检测到 QR 墙，已点击返回首页按钮")
                    await asyncio.sleep(2)
                else:
                    await browse.go_back_to_home(conn.page)
                await asyncio.sleep(bhv.click_delay())

                # P1 #11: 返回首页后重新关闭弹窗
                await browse.dismiss_login_modal(conn.page)

            # ── Step 7: 搜索发现（每 2 轮 1 次）──
            if r % 2 == 0 and round_ok:
                _xhs_log("  🔍 搜索发现...")
                kw = await browse.search(conn.page)
                if kw:
                    _xhs_log(f"  ✅ 搜索: {kw}")
                    await asyncio.sleep(2)
                    # 点击一个搜索结果
                    result_url = await browse.click_search_result(conn.page)
                    if result_url:
                        _xhs_log(f"  ✅ 点击结果")
                        await asyncio.sleep(random.uniform(3, 6))
                        await browse.go_back_to_home(conn.page)
                        # 返回后刷新页面
                        _xhs_log("  🔄 搜索返回后刷新页面...")
                        await browse.click_refresh_button(conn.page)
                        await asyncio.sleep(1)
                        # 返回后重新关闭弹窗
                        await browse.dismiss_login_modal(conn.page)
                    else:
                        _xhs_log("  ⚠️ 无搜索结果可点击")
                else:
                    _xhs_log("  ⚠️ 搜索失败")

        except Exception as e:
            _xhs_log(f"  ❌ 本轮异常: {e}")
            round_ok = False

        # 失败计数与防护
        if round_ok:
            passed_rounds += 1
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            _xhs_log(f"  ⚠️ 连续失败 {consecutive_failures}/3")

        if consecutive_failures >= 3:
            _xhs_log(f"  🛑 连续失败 3 次，暂停该账号")
            try:
                screenshot_path = f"/tmp/xhs_error_{identity_name}_{int(time.time())}.png"
                await conn.page.screenshot(path=screenshot_path)
                _xhs_log(f"  📸 截图保存: {screenshot_path}")
            except:
                pass
            break

        # 轮间休息
        if r < rounds:
            rest = bhv.round_break()
            _xhs_log(f"  ⏳ 休息 {rest:.0f}s...")
            await asyncio.sleep(rest)

    # ── 完成汇总 ──
    elapsed = time.time() - _t_start
    _xhs_log(f"\n{'='*40}")
    _xhs_log(f" 🏁 {identity_name} 养号完成")
    _xhs_log(f"    轮数: {passed_rounds}/{rounds}")
    _xhs_log(f"    耗时: {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # 关闭浏览器（不 daemon，节省资源）
    _xhs_log("  🔒 关闭浏览器...")
    try:
        await conn.close()
        _xhs_log("  ✅ 浏览器已关闭")
    except Exception as e:
        _xhs_log(f"  ⚠️ 关闭异常: {e}")

    _xhs_log(f"{'='*40}")
