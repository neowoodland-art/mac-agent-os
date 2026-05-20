"""
小红书 DOM 选择器集中管理
基于 2026-05-20 Playwright + Camoufox 实际 DOM 分析结果

分析环境:
- URL: https://www.xiaohongshu.com/explore
- 分辨率: 702x783 (Camoufox 窗口)
- 状态: 未登录（登录弹窗已隐藏）
"""

# ════════════════════════════════════════════════════════════
# 首页/发现页 (Explore)
# ════════════════════════════════════════════════════════════

# 瀑布流容器
FEED_CONTAINER = "#app .layout.limit"

# 笔记卡片 — section.note-item (DOM 分析确认)
NOTE_CARD = "section.note-item"

# 笔记卡片封面图链接
NOTE_CARD_COVER = "a.cover.mask.ld"

# 笔记卡片中的图片
NOTE_CARD_IMG = "a.cover.mask.ld img"

# 笔记卡片标题
NOTE_CARD_TITLE = ".title, [class*=title]"

# 笔记卡片作者信息
NOTE_CARD_AUTHOR = ".author, [class*=author]"

# 笔记卡片点赞数
NOTE_CARD_LIKES = ".like-count, [class*=like], [class*=count]"

# ════════════════════════════════════════════════════════════
# 笔记详情页 (Note Detail)
# ════════════════════════════════════════════════════════════

# 详情页主容器
NOTE_DETAIL_CONTAINER = ".note-detail, [class*=note-detail], .note-page"

# 笔记标题
NOTE_TITLE = ".title, h1, [class*=note-title]"

# 笔记内容文字
NOTE_CONTENT = ".content, [class*=content], .desc"

# 笔记图片
NOTE_IMAGES = ".note-content img, [class*=note-content] img"

# 作者头像
AUTHOR_AVATAR = ".avatar, [class*=avatar]"

# 作者昵称
AUTHOR_NAME = ".author-name, [class*=author-name], .nickname"

# ════════════════════════════════════════════════════════════
# 互动按钮
# ════════════════════════════════════════════════════════════

# 点赞按钮
LIKE_BUTTON = ".like-btn, [class*=like-btn], .interaction-like, button:has([class*=like])"

# 收藏按钮
COLLECT_BUTTON = ".collect-btn, [class*=collect-btn], .interaction-collect, button:has([class*=collect])"

# 关注按钮
FOLLOW_BUTTON = ".follow-btn, [class*=follow-btn], .interaction-follow"

# 分享按钮
SHARE_BUTTON = ".share-btn, [class*=share-btn]"

# ════════════════════════════════════════════════════════════
# 评论区
# ════════════════════════════════════════════════════════════

# 评论入口/评论数按钮
COMMENT_ENTRY = ".comment-btn, [class*=comment-btn], .interaction-comment, [class*=comment-count]"

# 评论区容器
COMMENT_SECTION = ".comment-section, [class*=comment-section], .comment-list"

# 评论输入框
COMMENT_INPUT = ".comment-input, [class*=comment-input] input, [contenteditable=true], textarea[placeholder*=评论]"

# 评论发送按钮
COMMENT_SEND = ".send-btn, [class*=send-btn], button:has-text('发送'), button[type=submit]"

# ════════════════════════════════════════════════════════════
# 搜索
# ════════════════════════════════════════════════════════════

# 搜索框
SEARCH_INPUT = "input.search-input"

# 搜索按钮
SEARCH_BUTTON = ".search-icon, [class*=search-icon], button:has-text('搜索')"

# 搜索结果页
SEARCH_RESULT_CONTAINER = ".search-result, [class*=search-result]"

# 搜索结果笔记卡片
SEARCH_NOTE_CARD = ".search-result .note-item, .search-result-item"

# ════════════════════════════════════════════════════════════
# 导航
# ════════════════════════════════════════════════════════════

# 左侧导航栏
LEFT_NAV = "nav, aside, [class*=sidebar]"

# 首页链接
NAV_HOME = 'a[href*="/explore"], a:has-text("发现")'

# 消息链接
NAV_MESSAGE = 'a[href*="/message"], a:has-text("消息")'

# 通知链接
NAV_NOTIFICATION = 'a[href*="/notification"], a:has-text("通知")'

# ════════════════════════════════════════════════════════════
# 弹窗/遮罩
# ════════════════════════════════════════════════════════════

# 登录弹窗
LOGIN_MODAL = "[class*=login], [class*=modal], [role=dialog], .reds-alert"

# 登录弹窗关闭按钮
LOGIN_MODAL_CLOSE = ".close-btn, [class*=close], button:has-text('关闭'), [class*=mask]"

# 通用遮罩层
OVERLAY = "[class*=mask], [class*=overlay], [class*=modal], div[style*='position: fixed']"

# ════════════════════════════════════════════════════════════
# 锚点验证选择器 (用于操作前后状态校验)
# ════════════════════════════════════════════════════════════

ANCHORS = {
    # 首页锚点: 瀑布流有笔记卡片
    "home_page": "section.note-item",

    # 笔记详情页锚点: 有笔记内容或标题
    "note_detail": ".note-detail, [class*=note-detail], .title, h1",

    # 视频播放页锚点: 有 video 元素
    "video_page": "video",

    # 评论区打开锚点: 评论列表可见
    "comment_open": ".comment-section, [class*=comment-section]",

    # 搜索页锚点: 搜索结果容器
    "search_page": ".search-result, [class*=search-result]",

    # 页面加载完成锚点: body 有内容
    "page_loaded": "#app",
}

# ════════════════════════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════════════════════════

def get_note_links_js() -> str:
    """JS 代码: 获取当前页面所有笔记链接"""
    return """
    () => {
        const links = [...document.querySelectorAll('a[href*="/explore/"]')];
        return [...new Set(links.map(a => a.href))].filter(h => h.includes('/explore/')).slice(0, 10);
    }
    """


def get_note_cards_js() -> str:
    """JS 代码: 获取笔记卡片元素列表"""
    return """
    () => {
        const cards = [...document.querySelectorAll('section.note-item')];
        return cards.map((card, i) => ({
            index: i,
            href: card.querySelector('a')?.href || '',
            title: card.textContent?.trim().substring(0, 50) || '',
            rect: card.getBoundingClientRect ? {
                x: Math.round(card.getBoundingClientRect().x),
                y: Math.round(card.getBoundingClientRect().y),
                w: Math.round(card.getBoundingClientRect().width),
                h: Math.round(card.getBoundingClientRect().height)
            } : null
        }));
    }
    """


def dismiss_login_modal_js() -> str:
    """JS 代码: 尝试关闭登录弹窗"""
    return """
    () => {
        // 关闭登录弹窗
        document.querySelectorAll('[class*=modal], [class*=dialog], [class*=mask], [role=dialog]').forEach(m => {
            m.style.display = 'none';
        });
        // 移除 fixed 遮罩
        document.querySelectorAll('div').forEach(d => {
            const s = window.getComputedStyle(d);
            if (s.position === 'fixed' && parseInt(s.zIndex) > 100) {
                d.style.display = 'none';
            }
        });
        return 'modal dismissed';
    }
    """
