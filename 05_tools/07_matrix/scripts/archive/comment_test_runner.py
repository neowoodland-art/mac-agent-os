#!/usr/bin/env python3
"""
comment_test_runner.py — 评论区状态机测试脚本 (v3)

与原 _retry_enter_video 逻辑一致，只测试评论状态机本身。
"""
import asyncio, os, sys, json, time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))
from cdp_connector import CDPConnector

LOG_FILE = '/tmp/comment_test.log'
def log(m):
    with open(LOG_FILE, 'a') as f: f.write(m + '\n')
    print(m, flush=True)


async def test():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    log(f"\n{'='*55}")
    log(f" 🦀 评论状态机测试 v3")
    log(f"{'='*55}")

    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()

    # 导入需要的函数
    from matrix_modules.nurture.runner import (
        _send_comment, _safe_goto, _dismiss_popups,
        _activate_window, _check_anchor
    )

    # ── 进入播放页（与原 _retry_enter_video 一致）──
    log("\n📍 进入播放页...")
    for attempt in range(3):
        log(f"  尝试 {attempt+1}/3")
        await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        await _dismiss_popups(page)

        card = page.locator('.discover-video-card-item').first
        if await card.count() == 0:
            continue

        await _activate_window()
        await card.click()
        await asyncio.sleep(1)
        await card.click()
        await asyncio.sleep(4)

        if await _check_anchor(page, 'video_page', timeout=3):
            # 点视频区域获取焦点
            vid = page.locator('video').first
            if await vid.count() > 0:
                box = await vid.bounding_box()
                if box:
                    await page.mouse.click(box['x'] + box['width']//2,
                                           box['y'] + box['height']//3)
            log(f"  ✅ 进入播放页成功")
            break
    else:
        log(f"  ❌ 无法进入播放页")
        return

    # ── 发送评论（新状态机）──
    log(f"\n{'─'*50}")
    log(f" 💬 测试评论状态机")
    log(f"{'─'*50}")
    await asyncio.sleep(2)
    await _activate_window()
    result = await _send_comment(page, LOG_FILE)
    log(f"\n📊 评论结果: {result}")

    # ── 回首页再测一次 ──
    log(f"\n{'─'*50}")
    log(f" 🔄 第2轮: 回到首页 → 进入播放页 → 评论")
    log(f"{'─'*50}")
    await _safe_goto(page, "https://www.douyin.com/")
    await asyncio.sleep(2)

    for attempt in range(2):
        await asyncio.sleep(2)
        card = page.locator('.discover-video-card-item').first
        if await card.count() > 0:
            await _activate_window()
            await card.click()
            await asyncio.sleep(1)
            await card.click()
            await asyncio.sleep(3)
            if await _check_anchor(page, 'video_page', timeout=3):
                break

    await asyncio.sleep(2)
    await _activate_window()
    result2 = await _send_comment(page, LOG_FILE)
    log(f"\n📊 第2轮结果: {result2}")

    # ── 汇总 ──
    log(f"\n{'='*55}")
    log(f" ✅ 测试完成，浏览器保持打开")
    log(f"   完整日志: cat /tmp/comment_test.log")

    while True: await asyncio.sleep(10)

if __name__ == '__main__':
    try: asyncio.run(test())
    except KeyboardInterrupt: print("\n👋 退出")
    except Exception as e:
        import traceback; traceback.print_exc()
