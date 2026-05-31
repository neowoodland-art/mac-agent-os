"""
抖音 — 交互类操作（点赞、收藏、评论）
"""


async def like(page) -> str:
    """点赞当前视频"""
    return await page.evaluate("""() => {
        const b = document.querySelector('[data-e2e="feed-active-video-double-like"]');
        if (b) { b.click(); return '👍'; }
        const b2 = document.querySelector('[data-e2e="like-count"]');
        if (b2) { b2.click(); return '👍'; }
        return '-';
    }""")


async def collect(page) -> str:
    """收藏当前视频"""
    return await page.evaluate("""() => {
        const b = document.querySelector('[data-e2e="video-collect"]');
        return b ? (b.click(), '⭐') : '-';
    }""")


async def comment(page, text: str = "不错") -> str:
    """评论当前视频（目前只打开评论区，不发送）"""
    return await page.evaluate("""() => {
        const btn = document.querySelector('[data-e2e="video-comment-count"]');
        if (btn) { btn.click(); return '💬open'; }
        return '-';
    }""")


async def next_video(page) -> str:
    """下滑到下一个视频"""
    await page.evaluate("window.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown'}))")
    return "↓next"
