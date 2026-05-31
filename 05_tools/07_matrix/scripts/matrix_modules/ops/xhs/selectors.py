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


def find_refresh_button_js() -> str:
    """
    JS 代码: 查找小红书瀑布流页面右下角的刷新 FAB 按钮

    策略:
    1. 先用常见选择器查找刷新类按钮
    2. 再用 SVG 扫描（刷新图标通常用 SVG 箭头）
    3. 过滤出右下角区域（x > viewport 60%, y > viewport 60%）的元素
    """
    return """
    () => {
        const vw = window.innerWidth, vh = window.innerHeight;
        const btns = [];

        // 方式1: 常见刷新按钮选择器
        const selectors = [
            'button[class*="refresh"]',
            '[class*="refresh-btn"]',
            '[class*="reload"]',
            'button[class*="fab"]',
            '[class*="float-btn"]',
            '[class*="floating"]',
        ];
        for (const sel of selectors) {
            const els = document.querySelectorAll(sel);
            els.forEach(el => {
                const r = el.getBoundingClientRect();
                if (r.width > 20 && r.height > 20 && r.width < 100 && r.height < 100) {
                    btns.push({x: r.x, y: r.y, w: r.width, h: r.height, text: el.textContent?.trim() || '', sel: sel});
                }
            });
        }

        // 方式2: SVG 扫描 — 查找包含旋转箭头路径的 SVG（刷新图标特征）
        document.querySelectorAll('svg').forEach(svg => {
            const parent = svg.closest('button, a, [class*="btn"], [class*="icon"], [role="button"], div');
            if (!parent) return;
            const r = parent.getBoundingClientRect();
            if (r.width < 15 || r.height < 15 || r.width > 120 || r.height > 120) return;
            // 检查 SVG 内是否有旋转箭头路径（arc + rotate 是刷新图标的典型特征）
            const paths = svg.querySelectorAll('path, circle');
            const hasRotation = [...paths].some(p => {
                const d = (p.getAttribute('d') || '').toLowerCase();
                const transform = (p.getAttribute('transform') || svg.getAttribute('transform') || '').toLowerCase();
                return d.includes('a') && (d.includes('m') || d.includes('l')) ||
                       transform.includes('rotate') ||
                       d.includes('arc');
            });
            if (hasRotation) {
                btns.push({x: r.x, y: r.y, w: r.width, h: r.height, text: parent.textContent?.trim() || '', sel: 'svg-scan'});
            }
        });

        // 方式3: 查找固定定位在右下角的可点击元素
        document.querySelectorAll('button, a, [role="button"], div[style*="cursor"]').forEach(el => {
            const s = window.getComputedStyle(el);
            if (s.position !== 'fixed') return;
            const r = el.getBoundingClientRect();
            if (r.x > vw * 0.6 && r.y > vh * 0.6 && r.width < 100 && r.height < 100 && r.width > 20 && r.height > 20) {
                // 避免重复
                if (!btns.some(b => Math.abs(b.x - r.x) < 10 && Math.abs(b.y - r.y) < 10)) {
                    btns.push({x: r.x, y: r.y, w: r.width, h: r.height, text: el.textContent?.trim() || '', sel: 'fixed-position'});
                }
            }
        });

        if (!btns.length) return {found: false};

        // 优先选右下角的按钮（x 最大 + y 最大）
        btns.sort((a, b) => (b.x + b.y) - (a.x + a.y));
        const best = btns[0];
        return {
            found: true,
            x: Math.round(best.x + best.w / 2),
            y: Math.round(best.y + best.h / 2),
            w: Math.round(best.w),
            h: Math.round(best.h),
            text: best.text,
            method: best.sel
        };
    }
    """


def find_qr_wall_back_button_js() -> str:
    """
    JS 代码: 检测小红书 QR 检测墙并查找"返回首页"按钮

    QR 墙特征:
    - 页面中央出现大弹窗
    - body 文本包含"扫码"、"二维码"等关键词
    - 弹窗内有"返回首页"或类似按钮
    """
    return """
    () => {
        const bodyText = document.body?.innerText?.toLowerCase() || '';
        // QR 墙关键词检测
        const qrKeywords = ['扫码', '二维码', 'qrcode', '扫描', 'scan code', '非常用登录', '验证'];
        const isQrWall = qrKeywords.some(kw => bodyText.includes(kw));

        if (!isQrWall) return {found: false, reason: 'no_qr_keywords'};

        // 查找弹窗中的返回按钮
        const backKeywords = ['返回首页', '返回', '首页', '回到首页', '确定', '我知道了', '关闭'];
        const candidates = [];

        // 搜索弹窗内所有可点击元素
        document.querySelectorAll('button, a, [role="button"], [class*="btn"], span[class*="text"], div[class*="text"]').forEach(el => {
            const text = el.textContent?.trim();
            if (!text) return;
            const textLower = text.toLowerCase();
            // 精确匹配或包含匹配
            const matched = backKeywords.some(kw => {
                if (textLower === kw) return true;
                if (textLower.includes(kw) && text.length < 15) return true;
                return false;
            });
            if (!matched) return;

            const r = el.getBoundingClientRect();
            if (r.width < 5 || r.height < 5) return; // 不可见

            // 优先级: "返回首页" > "返回" > "首页" > 其他
            let priority = 99;
            if (textLower === '返回首页' || textLower === '回到首页') priority = 10;
            else if (textLower === '返回') priority = 20;
            else if (textLower === '首页') priority = 30;
            else priority = 50;

            candidates.push({
                x: Math.round(r.x + r.width / 2),
                y: Math.round(r.y + r.height / 2),
                w: Math.round(r.width),
                h: Math.round(r.height),
                text: text,
                priority: priority
            });
        });

        if (!candidates.length) return {found: false, reason: 'no_back_button'};

        // 按优先级排序
        candidates.sort((a, b) => a.priority - b.priority);
        const best = candidates[0];
        return {
            found: true,
            x: best.x,
            y: best.y,
            w: best.w,
            h: best.h,
            text: best.text,
            priority: best.priority
        };
    }
    """
