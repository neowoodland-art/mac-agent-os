-- anchor.db 数据库设计 v1.0
-- 锚点规则 + 原子操作 + 检测日志 + 校准

-- ── 1. 锚点规则表 ──
-- 每个状态由多条规则组成（同 state + logic_group = AND，不同 group = OR）
CREATE TABLE anchor_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    state_name  TEXT    NOT NULL,       -- HOME / PLAYER / SEARCH / DETAIL / POPUP
    field       TEXT    NOT NULL,       -- 检测字段: video_count, title, video_playing, card_count, url, has_search_input
    operator    TEXT    NOT NULL,       -- eq / neq / gt / gte / lt / lte / contains / not_contains / regex
    value       TEXT    NOT NULL,       -- 目标值（统一存字符串）
    logic_group INTEGER DEFAULT 0,     -- 0=AND组, 同组内AND, 不同组OR
    active      INTEGER DEFAULT 1,     -- 1=启用, 0=停用
    created_at  TEXT    DEFAULT (datetime('now','localtime')),
    updated_at  TEXT    DEFAULT (datetime('now','localtime'))
);

-- ── 2. 原子操作表 ──
-- 每个原子操作 = 一个操作标识 + 执行方式 + 验证规则
CREATE TABLE atomic_ops (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    op_name      TEXT    NOT NULL UNIQUE,  -- click_card, swipe_down, like, search, go_home, dismiss_popup
    description  TEXT,                      -- 操作描述
    action_type  TEXT    DEFAULT 'locator', -- locator / keyboard / evaluate / mouse
    target       TEXT,                      -- CSS选择器 / 按键名 / JS代码
    verify_rule  TEXT,                      -- 验证方式: video_src_change / video_count_gt / title_change
    retry_count  INTEGER DEFAULT 3,
    fallback_op  TEXT,                      -- 失败时降级的操作名
    created_at   TEXT    DEFAULT (datetime('now','localtime')),
    updated_at   TEXT    DEFAULT (datetime('now','localtime'))
);

-- ── 3. 状态迁移表 ──
-- 定义合法的状态转换（状态机）
CREATE TABLE state_transitions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    from_state TEXT NOT NULL,       -- HOME, PLAYER, SEARCH
    to_state   TEXT NOT NULL,       -- PLAYER, SEARCH, HOME
    via_op     TEXT NOT NULL,       -- click_card, swipe_down, search, go_home
    UNIQUE(from_state, to_state, via_op)
);

-- ── 4. 检测日志表 ──
-- 每次锚点检测的记录，用于成功率追踪
CREATE TABLE detection_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    identity        TEXT,                  -- douyin_01, douyin_02
    expected_state  TEXT,                  -- 操作前预期的状态
    detected_state  TEXT,                  -- 实际检测到的状态
    match           INTEGER,               -- 1=匹配, 0=不匹配
    anchor_snapshot TEXT,                  -- 锚点数据快照(JSON)
    screenshot_path TEXT,                  -- 截图路径
    timestamp       TEXT    DEFAULT (datetime('now','localtime'))
);
CREATE INDEX idx_detection_logs_match ON detection_logs(match, timestamp);

-- ── 5. 校准候选表 ──
-- AI或自动校准产生的新规则，对比验证后决定是否采纳
CREATE TABLE calibration_candidates (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    state_name    TEXT,                    -- 哪个状态的规则
    source        TEXT,                    -- ai / manual / auto_recovery
    old_rules     TEXT,                    -- 旧规则JSON
    new_rules     TEXT,                    -- 建议的新规则JSON
    test_count    INTEGER DEFAULT 0,       -- 测试次数
    test_pass     INTEGER DEFAULT 0,       -- 测试通过次数
    status        TEXT    DEFAULT 'pending', -- pending / accepted / rejected / testing
    created_at    TEXT    DEFAULT (datetime('now','localtime'))
);

-- ── 初始数据：基于2026-05-06手动采集的锚点 ──

-- HOME 状态规则
INSERT INTO anchor_rules (state_name, field, operator, value, logic_group) VALUES
('HOME', 'video_count', 'eq', '1', 0),
('HOME', 'title', 'contains', '抖音精选', 0);

-- PLAYER 状态规则（全屏播放）
INSERT INTO anchor_rules (state_name, field, operator, value, logic_group) VALUES
('PLAYER', 'video_count', 'gte', '3', 0),
('PLAYER', 'video_playing', 'eq', 'true', 0);

-- SEARCH 状态规则
INSERT INTO anchor_rules (state_name, field, operator, value, logic_group) VALUES
('SEARCH', 'title', 'contains', '搜索', 0),
('SEARCH', 'title', 'not_contains', '精选', 0);

-- SEARCH_PLAYER（从搜索结果进入的播放页）
INSERT INTO anchor_rules (state_name, field, operator, value, logic_group) VALUES
('SEARCH_PLAYER', 'video_count', 'gte', '3', 0),
('SEARCH_PLAYER', 'video_playing', 'eq', 'true', 0),
('SEARCH_PLAYER', 'url', 'contains', '/search/', 0);

-- 原子操作
INSERT INTO atomic_ops (op_name, description, action_type, target, verify_rule, retry_count) VALUES
('click_card',   '点击首页视频卡片',  'locator',  '.discover-video-card-item',  'video_count_gte_3', 3),
('swipe_down',   '下滑切换视频',     'keyboard', 'ArrowDown',                  'video_src_change',  2),
('like',         '点赞当前视频',     'locator',  '[data-e2e="like-count"]',   'like_count_change',  1),
('search',       '搜索关键词',       'evaluate', 'search_input',               'title_contains_搜索', 2),
('go_home',      '回到首页',         'locator',  'https://www.douyin.com/',    'video_count_eq_1',   2),
('dismiss_popup','关闭弹窗',         'locator',  'button:text-is("我知道了")','popup_gone',           2);

-- 状态迁移
INSERT INTO state_transitions (from_state, to_state, via_op) VALUES
('HOME',   'PLAYER', 'click_card'),
('PLAYER', 'PLAYER', 'swipe_down'),
('PLAYER', 'HOME',   'go_home'),
('HOME',   'SEARCH', 'search'),
('SEARCH', 'SEARCH_PLAYER', 'click_card');
