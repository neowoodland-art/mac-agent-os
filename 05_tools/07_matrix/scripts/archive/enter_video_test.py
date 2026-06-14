#!/usr/bin/env python3
"""
enter_video_test.py — 单步测试：从精选页直接导航到视频URL

流程：
  1. 启动浏览器 → 精选页
  2. 读第一个卡片的 data-aweme-id
  3. 导航到 https://www.douyin.com/video/{id}
  4. 报告是否进入视频播放页
"""
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_connector import CDPConnector

LOG = '/tmp/enter_video_test.log'
def log(m):
    with open(LOG, 'a') as f: f.write(f'[{time.strftime("%H:%M:%S")}] {m}\n')
    print(m, flush=True)

async def read_sig(page):
    return await page.evaluate("""() => ({
        url: location.href,
        title: document.title,
        vc: document.querySelectorAll('video').length,
        cards: document.querySelectorAll('.discover-video-card-item').length,
        hasDigg: !!document.querySelector('[data-e2e="video-player-digg"]'),
        winW: window.innerWidth, winH: window.innerHeight,
    })""")

async def main():
    ID_DIR = os.path.expanduser('~/workbuddy-agent-os/agent-local/tools/matrix/identities/douyin_01_camo')
    log('🚀 启动浏览器...')
    conn = CDPConnector(identity_dir=ID_DIR, headless=False, window=(702,783), window_position=(652,0))
    await conn.connect()
    page = conn.page
    await conn.init_anti_detection()

    # 导航到首页
    log('📍 导航到 douyin.com...')
    await page.goto('https://www.douyin.com/', timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(6)

    sig0 = await read_sig(page)
    log(f'📊 精选页: cards={sig0["cards"]}, vc={sig0["vc"]}')

    # 读取第一个卡片的 aweme-id
    aweme_id = await page.evaluate("""() => {
        const card = document.querySelector('.discover-video-card-item');
        if (!card) return null;
        return card.getAttribute('data-aweme-id') || '';
    }""")
    log(f'🎯 卡片 data-aweme-id: {aweme_id}')

    if not aweme_id:
        log('❌ 未找到卡片 aweme-id')
        conn.browser.close()
        return

    # 直接导航到视频URL
    video_url = f'https://www.douyin.com/video/{aweme_id}'
    log(f'📍 导航到视频URL: {video_url[:50]}...')
    await page.goto(video_url, timeout=20000, wait_until='domcontentloaded')
    await asyncio.sleep(5)

    sig1 = await read_sig(page)
    is_player = sig1['vc'] >= 2 and sig1['hasDigg']
    log(f'📊 播放页: vc={sig1["vc"]}, digg={sig1["hasDigg"]}, URL={sig1["url"][:50]}')

    if is_player:
        log('✅ 成功进入视频播放页！')
    elif '/video/' in sig1['url']:
        log('⚠️ URL是视频页，但特征码不完全匹配')
    else:
        log('❌ 未进入视频播放页')

    log('\n✅ 完成，浏览器保持打开')
    log('按 Ctrl+C 退出')
    while True: await asyncio.sleep(10)

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: log('👋 退出')
    except Exception as e:
        import traceback; log(f'❌ {e}'); log(traceback.format_exc())
