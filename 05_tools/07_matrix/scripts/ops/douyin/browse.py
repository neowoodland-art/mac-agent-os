"""
抖音 — 浏览类操作
"""
import random


async def goto_home(page):
    """回到抖音首页"""
    await page.goto("https://www.douyin.com/", timeout=15000)
    return "home"


async def goto_video(page, video_url: str = None):
    """进入视频播放页，如果不指定 URL 则随机选择一个"""
    if not video_url:
        links = await page.evaluate("""() => {
            const links = [...document.querySelectorAll('a[href*="/video/"]')];
            return [...new Set(links.map(a => a.href))].slice(0, 5);
        }""")
        if not links:
            return None
        video_url = random.choice(links)
    await page.goto(video_url, timeout=15000, wait_until="domcontentloaded")
    return video_url


async def scroll_feed(page, distance: int = None):
    """滑动 feed 流"""
    import random
    dist = distance or random.randint(200, 700)
    await page.evaluate(f"window.scrollBy(0, {dist})")
    return dist
