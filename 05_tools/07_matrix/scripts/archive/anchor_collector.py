#!/usr/bin/env python3
"""
anchor_collector.py — 全局热键驱动的锚点采集器

使用方式：
  1. 运行本脚本 → 自动启动 Camoufox
  2. 在浏览器中操作
  3. 操作完按 ⌥+数字(1-8) → 自动采集锚点数据
  4. 按 ⌥+0 退出采集

交互模式：
  - ⌥+1~8: 采集当前页面锚点
  - ⌥+0: 退出
  - 直接输入步骤号+回车: 备选（终端模式）
"""
import asyncio
import json
import os
import sys
import time
import platform
from pathlib import Path
from datetime import datetime

# ── 路径 ──
SCRIPTS_DIR = Path.home() / "workbuddy-agent-os" / "agent-sync" / "05_tools" / "07_matrix" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
LOCAL_ROOT = Path.home() / "workbuddy-agent-os" / "agent-local" / "tools" / "matrix"
DATA_DIR = LOCAL_ROOT / "data"
SCREENSHOT_DIR = LOCAL_ROOT / "screenshots"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

from cdp_connector import CDPConnector

# ── 全局状态 ──
collected = []
loop = None  # asyncio 事件循环引用
page_obj = None
identity_name = "douyin_01"


async def init_browser():
    """启动Camoufox，打开抖音首页，关闭弹窗"""
    global page_obj
    print("\n🦀 启动 Camoufox...")
    conn = CDPConnector(
        identity_dir=str(LOCAL_ROOT / "identities" / f"{identity_name}_camo"),
        headless=False,
        window=(702, 783),
    )
    await conn.connect()
    await conn.init_anti_detection()
    page_obj = conn.page

    # 导航到抖音
    print("📍 导航到抖音首页...")
    await page_obj.goto("https://www.douyin.com/", timeout=30000, wait_until="domcontentloaded")
    await asyncio.sleep(3)

    # 关弹窗
    try:
        for text in ["我知道了", "关闭", "跳过", "下一步"]:
            btn = page_obj.locator(f'button:has-text("{text}")').first
            if await btn.count() > 0:
                await btn.click()
                await asyncio.sleep(0.5)
        print("✅ 弹窗已关闭")
    except:
        pass

    print(f"\n{'='*55}")
    print(f" 🎯 就绪！请在 Camoufox 窗口中操作")
    print(f" 按 ⌥+1~8 采集锚点，⌥+0 退出")
    print(f" 当前页面: {page_obj.url[:50]}")
    print(f"{'='*55}\n")
    return conn


async def collect_anchors(step_id):
    """采集当前页面的全部锚点数据
    step_id: int(1-9) 或 str('comment', 'like' 等)
    """
    global page_obj
    ts = datetime.now()
    step_label = str(step_id)
    data = {
        "step": step_label,
        "time": ts.strftime("%H:%M:%S"),
        "url": page_obj.url if page_obj else "N/A",
        "anchors": {},
    }

    # ── 采集 DOM 锚点 ──
    try:
        anchors = await page_obj.evaluate("""() => {
            const v = document.querySelector('video');
            const cards = document.querySelectorAll('.discover-video-card-item');
            const links = document.querySelectorAll('a[href*="/video/"]');
            const searchInput = document.querySelector('input[placeholder*="搜索"]');
            const likeBtn = document.querySelector('[data-e2e="like-count"]');
            const dblLike = document.querySelector('[data-e2e="feed-active-video-double-like"]');
            const collectBtn = document.querySelector('[data-e2e="video-collect"]');
            const commentArea = document.querySelector('[class*="comment"]');
            // 弹窗检测：用 textContent 遍历（避免 :has-text 不支持）
            let hasPopupClose = false;
            for (const btn of document.querySelectorAll('button')) {
                const t = btn.textContent || '';
                if (t.includes('我知道了') || t.includes('关闭') || t.includes('跳过')) {
                    hasPopupClose = true;
                    break;
                }
            }

            return {
                video_count: document.querySelectorAll('video').length,
                video_paused: v ? v.paused : null,
                video_playing: v ? (!v.paused && v.readyState > 0) : false,
                video_src_prefix: v ? (v.src || '').substring(0, 60) : '',
                video_currentTime: v ? Math.floor(v.currentTime) : -1,
                card_count: cards.length,
                video_links: links.length,
                has_search_input: !!searchInput,
                search_input_placeholder: searchInput ? searchInput.placeholder : '',
                has_like_btn: !!likeBtn,
                has_double_like: !!dblLike,
                has_collect_btn: !!collectBtn,
                has_comment_area: !!commentArea,
                has_popup_close: hasPopupClose,
                title: document.title,
                body_text: (document.body?.innerText || '').substring(0, 150),
            };
        }""")
        data["anchors"] = anchors

        # 单独采集评论区DOM详情（简洁，不干扰主流程）
        if step_label == 'comment':
            more = await page_obj.evaluate("""() => {
                const all = document.querySelectorAll('textarea,input,[contenteditable]');
                const vis = [...all].filter(e => {
                    const r = e.getBoundingClientRect();
                    return r.width>0 && r.height>0 && r.top>0;
                });
                return vis.map(e => ({
                    tag: e.tagName, type: e.type || '',
                    ph: e.placeholder || '', cls: (e.className||'').slice(0,40),
                    edit: !!e.isContentEditable,
                    w: Math.round(e.getBoundingClientRect().width),
                    h: Math.round(e.getBoundingClientRect().height)
                }));
            }""")
            data["comment_inputs"] = more
            btns = await page_obj.evaluate("""() => {
                const btns = [...document.querySelectorAll('button')]
                    .filter(e => { const r=e.getBoundingClientRect(); return r.width>0 && r.height>0 && r.top>0; });
                return btns.map(e => ({
                    text: (e.textContent||'').slice(0,30), cls: (e.className||'').slice(0,40)
                }));
            }""")
            data["comment_buttons"] = btns
    except Exception as e:
        data["anchors"]["error"] = str(e)

    # ── 截图 ──
    try:
        ss_file = SCREENSHOT_DIR / f"step{step_label}_{ts.strftime('%H%M%S')}.png"
        await page_obj.screenshot(path=str(ss_file))
        data["screenshot"] = str(ss_file)
    except:
        data["screenshot"] = None

    collected.append(data)
    return data


async def on_step(step_id):
    """热键触发：采集并输出"""
    step_label = str(step_id)
    print(f"\n🔥 采集 {step_label} ...", end=" ", flush=True)
    data = await collect_anchors(step_id)
    a = data["anchors"]
    print(f"✅")
    print(f"   URL:    {data['url'][:55]}")
    print(f"   video:  {a.get('video_count')} | paused={a.get('video_paused')} | playing={a.get('video_playing')}")
    print(f"   cards:  {a.get('card_count')} | links={a.get('video_links')}")
    print(f"   搜索框: {'✅' if a.get('has_search_input') else '❌'} | 点赞: {'✅' if a.get('has_like_btn') else '❌'}")
    print(f"   评论区: {'✅' if a.get('has_comment_area') else '❌'}")
    inputs = data.get('comment_inputs', [])
    if inputs:
        print(f"   📝 评论输入框 ({len(inputs)}个):")
        for i, inp in enumerate(inputs):
            print(f"      [{i}] {inp['tag']} ph=\"{inp['ph']}\" cls=\"{inp['cls']}\" edit={inp['edit']} {inp['w']}x{inp['h']}")
    btns = data.get('comment_buttons', [])
    if btns:
        print(f"   🔘 评论按钮 ({len(btns)}个):")
        for i, b in enumerate(btns):
            print(f"      [{i}] text=\"{b['text']}\" cls=\"{b['cls']}\"")
    if data["screenshot"]:
        print(f"   📸 {data['screenshot']}")
    # 蜂鸣
    print("\a", end="", flush=True)

    # 保存到文件
    save_path = DATA_DIR / f"anchor_{data['step']}.json"
    with open(save_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"   💾 {save_path}\n")


async def show_summary():
    """输出所有采集数据的汇总"""
    print(f"\n{'='*55}")
    print(f" 📊 锚点采集汇总 ({len(collected)} 步)")
    print(f"{'='*55}")
    for d in collected:
        a = d["anchors"]
        step = d["step"]
        status = "HOME" if a.get("card_count", 0) > 5 else "PLAYER" if a.get("video_count", 0) > 0 else "OTHER"
        print(f"  步{step}: [{status}] video={a.get('video_count')} cards={a.get('card_count')} "
              f"playing={a.get('video_playing')} search={'✅' if a.get('has_search_input') else '❌'} "
              f"like={'✅' if a.get('has_like_btn') else '❌'}")

    # 保存汇总
    summary_path = DATA_DIR / "anchor_summary.json"
    with open(summary_path, "w") as f:
        json.dump(collected, f, ensure_ascii=False, indent=2)
    print(f"\n💾 全部数据已保存: {summary_path}")
    print(f"   截图目录: {SCREENSHOT_DIR}")


# ── 热键监听（pynput，独立线程）──
def _start_hotkey_listener():
    """启动全局热键监听（独立线程）
    
    触发方式：直接按数字键 1~8（不需要 Option 组合）
    因为 ⌥+数字 在 macOS 上会被映射为特殊字符（如 ⌥+2=™）
    """
    from pynput import keyboard

    # 数字键对应的 pynput KeyCode（不同键盘可能不同，用 vk 更可靠）
    # macOS 数字键 vk: 1=18, 2=19, 3=20, 4=21, 5=23, 6=22, 7=26, 8=28, 9=25, 0=29
    DIGIT_VK = {18: 1, 19: 2, 20: 3, 21: 4, 23: 5, 22: 6, 26: 7, 28: 8, 25: 9, 29: 0}
    # 备选：小键盘数字键 vk
    DIGIT_VK2 = {83: 1, 84: 2, 85: 3, 86: 4, 87: 5, 88: 6, 89: 7, 91: 8, 92: 9, 82: 0}

    # 字母键 → 操作名映射（避开抖音快捷键）
    # 抖音占用: G关注 Z点赞 X评论 J清屏 K连播 H全屏 F作者主页 空格播放
    # 可用: A B C D E I L M N O P Q R S T U V W Y
    LETTER_MAP = {
        'c': 'comment',   # 评论区 (抖音X)
        'l': 'like',      # 点赞 (抖音Z)
        'o': 'collect',   # 收藏
        'q': 'follow',    # 关注 (抖音G)
        'p': 'loop',      # 连播 (抖音K)
        'm': 'mute',      # 静音
        'd': 'display',   # 清屏 (抖音J)
    }
    # 方向键
    ARROW_MAP = {
        'right': 'seek_fwd', 'left': 'seek_bwd',
    }

    def on_release(key):
        try:
            char = key.char.lower() if hasattr(key, 'char') and key.char else ''
            key_name = key.name.lower() if hasattr(key, 'name') and key.name else ''

            # 字母键 → 采集原子操作
            if char in LETTER_MAP:
                op = LETTER_MAP[char]
                print(f"\n[{op}] 采集原子操作锚点...", flush=True)
                asyncio.run_coroutine_threadsafe(on_step(op), loop)
                return

            # 方向键 → 采集快进/快退
            if key_name in ARROW_MAP:
                op = ARROW_MAP[key_name]
                print(f"\n[{op}] 采集原子操作锚点...", flush=True)
                asyncio.run_coroutine_threadsafe(on_step(op), loop)
                return

            # 数字键 1-9 → 采集页面状态
            if hasattr(key, 'char') and key.char and key.char.isdigit():
                step = int(key.char)
                if 1 <= step <= 9:
                    asyncio.run_coroutine_threadsafe(on_step(step), loop)
                    return
                elif step == 0:
                    print("\n0 退出采集...")
                    asyncio.run_coroutine_threadsafe(show_summary(), loop)
                    return False

            # 方法2：通过 vk 检测数字（备选）
            if hasattr(key, 'vk') and key.vk in DIGIT_VK:
                step = DIGIT_VK[key.vk]
                if 1 <= step <= 9:
                    asyncio.run_coroutine_threadsafe(on_step(step), loop)
                    return
                elif step == 0:
                    print("\n0 退出采集...")
                    asyncio.run_coroutine_threadsafe(show_summary(), loop)
                    return False
        except (ValueError, AttributeError):
            pass

    listener = keyboard.Listener(on_release=on_release)
    listener.start()
    return listener


async def console_fallback():
    """终端输入模式（热键不可用时的降级）"""
    print("\n📟 终端输入模式")
    print("   输入步骤号(1-8)按回车采集，0退出\n")
    while True:
        try:
            cmd = input("步骤? ").strip()
            if not cmd:
                continue
            step = int(cmd)
            if 1 <= step <= 8:
                await on_step(step)
            elif step == 0:
                await show_summary()
                break
            else:
                print("  请输入 1-8 采集, 0 退出")
        except (ValueError, KeyboardInterrupt):
            break


# ── 主流程 ──
async def main():
    global loop
    loop = asyncio.get_event_loop()

    # 启动浏览器
    conn = await init_browser()

    # 尝试全局热键模式
    use_hotkey = False
    listener = None
    try:
        print("⌨️ 尝试启动全局热键（数字键1-8采集，0退出）...")
        listener = _start_hotkey_listener()
        use_hotkey = True
        print("✅ 全局热键就绪！在浏览器窗口按数字键即可采集\n")
    except Exception as e:
        print(f"⚠️ 热键启动失败: {e}")
        print("📟 降级到终端输入模式\n")

    if use_hotkey:
        print("📌 请在 Camoufox 窗口中操作")
        print("   操作完直接按数字键 1-8 采集，按 0 退出")
        print("   （不需要切换到终端）\n")
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        await show_summary()
    else:
        print("   操作完在下方输入数字(1-8)按回车采集")
        print("   输入 0 退出\n")
        await console_fallback()

    # 清理
    if listener:
        listener.stop()
    print("\n👋 采集结束")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 已退出")
