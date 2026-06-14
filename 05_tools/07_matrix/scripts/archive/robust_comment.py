#!/usr/bin/env python3
"""
robust_comment.py — 鲁棒评论流程（带重试）

流程：
  1. 进入视频 → 开评论区
  2. 找底部输入框（input/textrea/contenteditable）
  3. 找不到 → 下滑换视频 → 重试（最多3次）
  4. 找到 → 点击 → fill → Alt+Enter
"""
import asyncio, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector
LOG = '/tmp/robust_comment.log'
def log(m):
    with open(LOG, 'a') as f: f.write(m + '\n')
    print(m, flush=True)

async def find_bottom_input(page):
    """找底部输入框"""
    return await page.evaluate("""() => {
        var h = window.innerHeight;
        var all = document.querySelectorAll('input, textarea, [contenteditable]');
        for (var i = 0; i < all.length; i++) {
            var c = all[i];
            if (!c.offsetParent) continue;
            var ce = c.getAttribute('contenteditable');
            if (ce === 'false') continue;
            var r = c.getBoundingClientRect();
            if (r.bottom > h - 120 && r.bottom < h + 50) {
                return {tag: c.tagName, cls: (c.className||'').slice(0,35),
                        x: Math.round(r.left+r.width/2), y: Math.round(r.top+r.height/2),
                        w: Math.round(r.width), h: Math.round(r.height),
                        ph: c.getAttribute('placeholder')||''};
            }
        }
        return null;
    }""")

async def try_enter_video_and_comment(page):
    """进入视频+打开评论，返回是否成功"""
    await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(4)
    card = page.locator('.discover-video-card-item').first
    if await card.count() == 0: return False
    await card.click(force=True); await asyncio.sleep(1)
    await card.click(force=True); await asyncio.sleep(4)
    # 开评论
    vid = page.locator('video').first
    if await vid.count() > 0:
        box = await vid.bounding_box()
        if box: await page.mouse.click(box['x']+box['width']//2, box['y']+box['height']//3)
    await asyncio.sleep(0.5)
    await page.keyboard.press('x')
    await asyncio.sleep(2)
    has_cl = await page.evaluate('() => !!document.querySelector("[data-e2e=comment-list]")')
    if not has_cl:
        # DOM 点评论图标兜底
        await page.evaluate("""() => {
            var b = document.querySelector('[data-e2e="video-comment-count"]') ||
                     document.querySelector('[data-e2e="feed-comment-icon"]');
            if (b) b.click();
        }""")
        await asyncio.sleep(2)
    return True

async def swipe_down(page):
    """下滑换视频——先关弹窗回精选页，再点不同的卡片"""
    log('  📱 切换视频...')
    # 先按 Escape 退出弹窗
    await page.keyboard.press('Escape')
    await asyncio.sleep(1)
    # 滚动让页面加载不同卡片
    await page.mouse.wheel(0, 400)
    await asyncio.sleep(2)

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()
    log('='*50)
    log('🦀 鲁棒评论测试')

    for attempt in range(3):
        log(f'\n📡 第{attempt+1}次尝试')
        await try_enter_video_and_comment(page)
        inp = await find_bottom_input(page)
        log(f'  输入框: {inp}')

        if inp:
            # 找到了，开始互动
            log(f'🎯 找到输入框 ({inp["x"]}, {inp["y"]}) cls={inp["cls"]} ph="{inp["ph"]}"')
            await page.mouse.click(inp['x'], inp['y'])
            await asyncio.sleep(0.5)
            await page.mouse.click(inp['x'], inp['y'])
            await asyncio.sleep(0.5)

            ae = await page.evaluate('() => document.activeElement?.tagName || "none"')
            log(f'  activeElement: {ae}')

            if inp['tag'] in ('INPUT', 'TEXTAREA'):
                await page.keyboard.type('好内容', delay=40)
            else:
                await page.keyboard.type('好内容', delay=40)
            await asyncio.sleep(1.5)

            val = await page.evaluate('() => document.activeElement?.value || document.activeElement?.textContent || ""')
            log(f' 输入值: "{val}"')

            if val:
                log(' ⌨️ Alt+Enter...')
                await page.keyboard.press('Alt+Enter')
                await asyncio.sleep(3)

                has_v = await page.evaluate('() => !!document.querySelector("input[placeholder*=验证码]")')
                val2 = await page.evaluate('() => document.activeElement?.value || document.activeElement?.textContent || ""')
                log(f' 验证码: {"✅" if has_v else "❌"}  输入框: "{val2}"')

                if has_v:
                    log('\n🎉 完整链路跑通！')
                elif val2 != val:
                    log('\n✅ 已发送（内容变化）')
                else:
                    log('\n⚠️ 可能未发送')
                break
            else:
                log('  ❌ 文字输入失败')
        else:
            # 没找到输入框，下滑换视频
            log('  ⚠️ 没找到输入框，下滑重试')
            await swipe_down(page)

    else:
        log('\n❌ 3次尝试均失败')
        log('需要检查：可能直播间/广告视频，或页面结构变化')

    await conn.browser.close()

asyncio.run(main())
