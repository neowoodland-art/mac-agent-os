-- ============================================================
-- 口播素材系统数据库初始化
-- 使用：sqlite3 data/database.db < schema.sql
-- ============================================================

-- 开启 WAL 模式，提高并发读取
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- 素材元数据表
CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,                -- 平台：xiaohongshu / douyin / bilibili
    original_id TEXT NOT NULL,             -- 平台内唯一 ID
    url TEXT,                              -- 原始链接
    title TEXT,                            -- 标题
    description TEXT,                      -- 描述/正文
    author TEXT,                           -- 作者
    author_id TEXT,                        -- 作者 ID
    cover_url TEXT,                        -- 封面图 URL
    cover_local TEXT,                      -- 本地封面图路径
    music_name TEXT,                       -- BGM 名称
    tags_platform TEXT,                    -- 平台自带标签（逗号分隔）
    duration INTEGER,                      -- 时长（秒）
    like_count INTEGER DEFAULT 0,          -- 点赞数
    collect_count INTEGER DEFAULT 0,       -- 收藏数
    comment_count INTEGER DEFAULT 0,       -- 评论数
    share_count INTEGER DEFAULT 0,         -- 分享数
    raw_json TEXT,                         -- 原始 JSON 数据（完整备份）
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 采集时间
    analyzed INTEGER DEFAULT 0,            -- 0:未分析 1:已分析 2:分析失败
    download_status TEXT DEFAULT 'none',   -- none / pending / downloading / done / failed
    local_files TEXT,                      -- JSON: {"video":"path","audio":"path"}
    notes TEXT                             -- 用户备注
);

-- 平台+ID 联合唯一索引（去重）
CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_id ON materials(platform, original_id);

-- 查询常用索引
CREATE INDEX IF NOT EXISTS idx_analyzed ON materials(analyzed);
CREATE INDEX IF NOT EXISTS idx_download_status ON materials(download_status);
CREATE INDEX IF NOT EXISTS idx_platform ON materials(platform);
CREATE INDEX IF NOT EXISTS idx_fetched_at ON materials(fetched_at);

-- AI 分析结果表
CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER UNIQUE NOT NULL,   -- 关联素材
    tags TEXT,                             -- AI 标签（逗号分隔）
    golden_quote TEXT,                     -- 可引用金句
    core_idea TEXT,                        -- 核心立意
    structure TEXT,                        -- 口播脚本结构
    emotion TEXT,                          -- 整体情绪
    worth_downloading TEXT,                -- yes / no / maybe
    download_reason TEXT,                  -- 下载理由
    raw_model_output TEXT,                 -- 模型原始返回（调试）
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE
);

-- 采集批次记录表
CREATE TABLE IF NOT EXISTS collect_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    keyword TEXT NOT NULL,
    count INTEGER DEFAULT 0,               -- 本次采集数量
    jsonl_file TEXT,                       -- JSONL 文件路径
    status TEXT DEFAULT 'pending',         -- pending / running / done / failed
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_batch_status ON collect_batches(status);
