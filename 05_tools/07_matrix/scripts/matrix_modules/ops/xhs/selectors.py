"""
小红书 DOM 选择器集中管理
基于 2026-05-20/2026-05-27 Playwright + Camoufox 实际 DOM 分析和测试

分析环境:
- URL: https://www.xiaohongshu.com/explore
- 分辨率: 702x783 (Camoufox 窗口)
- 状态: 未登录（登录弹窗已隐藏）

v2 更新 (2026-05-27):
- 新增 note-detail-mask / like-wrapper / collect-wrapper 实际 DOM 选择器
- 新增锚点检测函数 is_note_detail_mode_js()
- 新增 L 形鼠标路径辅助函数
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
# v2 更新: 基于实际 DOM 分析的精确选择器 (2026-05-27)
# ════════════════════════════════════════════════════════════

# 笔记详情遮罩层 (SPA 详情页容器)
NOTE_DETAIL_MASK = ".note-detail-mask, [class*=\"note-detail\"]"

# 底部互动栏点赞按钮 (span.like-wrapper, 实际 DOM 分析确认)
# 注意: 页面中有大量 like-wrapper (评论区每个回复也有), 需用 x > viewW*0.3 区分底部栏
LIKE_WRAPPER = "span.like-wrapper, [class*=\"like-wrapper\"]"

# 底部互动栏收藏按钮 (span.collect-wrapper)
COLLECT_WRAPPER = "span.collect-wrapper, [class*=\"collect-wrapper\"]"

# 底部互动栏 (interactions 容器)
INTERACTIONS_BAR = ".interactions, [class*=interactions]"

# ════════════════════════════════════════════════════════════
# 锚点验证选择器 (用于操作前后状态校验)
# ════════════════════════════════════════════════════════════

ANCHORS = {
    # 首页锚点: 瀑布流有笔记卡片
    "home_page": "section.note-item",

    # 笔记详情页锚点: 有笔记内容或标题
    "note_detail": ".note-detail, [class*=note-detail], .title, h1",

    # v2: 笔记详情遮罩锚点 (SPA 详情页容器)
    "note_detail_mask": ".note-detail-mask, [class*=note-detail]",

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


def get_bottom_bar_buttons_js() -> str:
    """JS 代码: 获取底部互动栏按钮（排除评论区里的 like-wrapper）"""
    return """
    () => {
        const viewW = window.innerWidth;
        const likeBtns = [...document.querySelectorAll('span.like-wrapper, [class*="like-wrapper"]')];
        const collectBtns = [...document.querySelectorAll('span.collect-wrapper, [class*="collect-wrapper"]')];

        // 底部栏按钮的特征: x > 视口宽度 30%
        let likeBtn = null;
        let collectBtn = null;

        for (const el of likeBtns) {
            const r = el.getBoundingClientRect();
            if (r.left > viewW * 0.3) {
                likeBtn = {
                    x: Math.round(r.x + r.width / 2),
                    y: Math.round(r.y + r.height / 2),
                    w: Math.round(r.width),
                    h: Math.round(r.height),
                    visible: r.bottom <= window.innerHeight && r.top >= 0,
                    cls: (el.className || '').substring(0, 50),
                    text: (el.textContent || '').trim().substring(0, 20),
                    isActive: (el.className || '').includes('active') || (el.className || '').includes('liked'),
                };
                break;
            }
        }

        for (const el of collectBtns) {
            const r = el.getBoundingClientRect();
            if (r.left > viewW * 0.3) {
                collectBtn = {
                    x: Math.round(r.x + r.width / 2),
                    y: Math.round(r.y + r.height / 2),
                    w: Math.round(r.width),
                    h: Math.round(r.height),
                    visible: r.bottom <= window.innerHeight && r.top >= 0,
                    cls: (el.className || '').substring(0, 50),
                    text: (el.textContent || '').trim().substring(0, 20),
                    isActive: (el.className || '').includes('active'),
                };
                break;
            }
        }
        return { like: likeBtn, collect: collectBtn };
    }
    """


def is_note_detail_mode_js() -> str:
    """JS 代码: 检测当前是否为笔记详情模式（而非图片查看器）

    返回:
        { is_detail: bool, reason: str, has_mask: bool,
          has_interact_bar: bool, has_lightbox: bool, ... }
    """
    return """
    () => {
        const viewW = window.innerWidth;
        const viewH = window.innerHeight;

        // 1. 检测 note-detail-mask
        const masks = document.querySelectorAll('.note-detail-mask, [class*="note-detail"]');
        const hasMask = masks.length > 0;

        // 2. 检测底部互动栏（x > 视口宽度30% 的 like-wrapper）
        const likeBtns = document.querySelectorAll('span.like-wrapper, [class*="like-wrapper"]');
        const collectBtns = document.querySelectorAll('span.collect-wrapper, [class*="collect-wrapper"]');
        let hasInteractBar = false;
        for (const el of likeBtns) {
            const r = el.getBoundingClientRect();
            if (r.left > viewW * 0.3) { hasInteractBar = true; break; }
        }
        if (!hasInteractBar) {
            for (const el of collectBtns) {
                const r = el.getBoundingClientRect();
                if (r.left > viewW * 0.3) { hasInteractBar = true; break; }
            }
        }

        // 3. 检测图片查看器特征
        const lightboxEls = document.querySelectorAll(
            '[class*="lightbox"], [class*="image-viewer"], [class*="fullscreen-image"]'
        );
        let lightboxFullscreen = false;
        for (const el of lightboxEls) {
            const r = el.getBoundingClientRect();
            if (r.width > viewW * 0.8 && r.height > viewH * 0.8) {
                lightboxFullscreen = true;
                break;
            }
        }

        // 4. URL 验证
        const urlPath = window.location.pathname || '';
        const hasNoteUrl = /^\\/explore\\/[a-f0-9]{20,}/.test(urlPath);

        // 综合判断
        const isDetail = hasMask && hasInteractBar && hasNoteUrl;
        let reason = '';
        if (isDetail) reason = '笔记详情模式';
        else if (hasMask && !hasInteractBar) reason = '疑似图片查看器';
        else if (!hasMask) reason = '不在详情页';
        else reason = '未知状态';

        return {
            is_detail: isDetail,
            reason: reason,
            has_mask: hasMask,
            has_interact_bar: hasInteractBar,
            lightbox_fullscreen: lightboxFullscreen,
            has_note_url: hasNoteUrl,
        };
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
