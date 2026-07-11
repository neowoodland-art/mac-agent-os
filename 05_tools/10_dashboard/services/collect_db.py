"""
collect_db.py — 采集系统 SQLite 数据库层 v1

表结构：
  - collect_tasks:    采集任务（单次/批量/定时）
  - collect_items:    采集内容（带统一 schema，按 platform+item_id 去重）
  - collect_comments: 评论区（按 item_id 关联）
  - collect_sources:  采集源（定时监控用）
"""
import json, sqlite3, time, os
from datetime import datetime
from pathlib import Path
from typing import Optional

_THIS_DIR = Path(__file__).resolve().parent
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL",
                   str(Path.home() / "workbuddy-agent-os" / "agent-local")))
DEFAULT_DB = AGENT_LOCAL / "data" / "collect.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS collect_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL DEFAULT 'single',                    -- 'single'/'batch'/'scheduled'
    platform TEXT,                                          -- 'douyin'/'xhs'/'bilibili'/'zhihu'/'web'
    target TEXT NOT NULL,                                   -- 原始输入(URL/sec_uid/关键词)
    depth TEXT DEFAULT 'light',                             -- 'light'/'deep'
    tool_level INTEGER DEFAULT 2,                           -- 1/2/3
    machine TEXT,                                           -- 执行机器
    status TEXT DEFAULT 'pending',                          -- 'pending'/'running'/'completed'/'failed'
    total_targets INTEGER DEFAULT 0,
    completed_targets INTEGER DEFAULT 0,
    summary TEXT,                                           -- 摘要 JSON
    created_at TEXT DEFAULT (datetime('now','localtime')),
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS collect_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES collect_tasks(id),
    platform TEXT NOT NULL,
    item_id TEXT NOT NULL,                                  -- 平台内唯一 ID
    url TEXT,
    title TEXT,
    author_name TEXT,
    author_id TEXT,
    published_at TEXT,
    collected_at TEXT DEFAULT (datetime('now','localtime')),
    text_content TEXT,
    tags TEXT,                                              -- JSON array
    stats TEXT,                                             -- JSON: {likes,comments,shares,views}
    extra TEXT,                                             -- JSON: 平台特有字段
    media TEXT,                                             -- JSON: [{type,url,duration}]
    ai_analysis TEXT,                                       -- JSON: L2 深度分析
    UNIQUE(platform, item_id)
);

CREATE TABLE IF NOT EXISTS collect_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_db_id INTEGER REFERENCES collect_items(id),
    author_name TEXT,
    text TEXT,
    likes INTEGER DEFAULT 0,
    replied_at TEXT
);

CREATE TABLE IF NOT EXISTS collect_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    source_type TEXT NOT NULL,                              -- 'user'/'hashtag'/'keyword'/'url_list'
    target TEXT NOT NULL,                                   -- sec_uid/话题ID/关键词/URL
    display_name TEXT,
    schedule TEXT,                                          -- CRON 表达式
    depth TEXT DEFAULT 'light',
    tool_level INTEGER DEFAULT 2,
    last_collected TEXT,
    status TEXT DEFAULT 'active',                           -- 'active'/'paused'
    UNIQUE(platform, source_type, target)
);
"""


class CollectDB:
    """采集数据库操作"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DEFAULT_DB)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()

    # ── 任务管理 ──

    def create_task(self, type: str, platform: str, target: str,
                    depth: str = "light", tool_level: int = 2,
                    machine: str = "", total_targets: int = 1) -> int:
        conn = self._get_conn()
        try:
            cur = conn.execute(
                "INSERT INTO collect_tasks (type,platform,target,depth,tool_level,machine,total_targets) VALUES (?,?,?,?,?,?,?)",
                (type, platform, target, depth, tool_level, machine, total_targets)
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def update_task_status(self, task_id: int, status: str,
                           summary: str = None, completed: int = None):
        conn = self._get_conn()
        try:
            sets = ["status=?"]
            params = [status]
            if summary:
                sets.append("summary=?")
                params.append(summary)
            if completed:
                sets.append("completed_targets=?")
                params.append(completed)
            if status in ("completed", "failed"):
                sets.append("completed_at=datetime('now','localtime')")
            params.append(task_id)
            conn.execute(f"UPDATE collect_tasks SET {','.join(sets)} WHERE id=?", params)
            conn.commit()
        finally:
            conn.close()

    def get_task(self, task_id: int) -> Optional[dict]:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM collect_tasks WHERE id=?", (task_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_tasks(self, status: str = None, platform: str = None,
                   limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        try:
            where = []
            params = []
            if status:
                where.append("status=?")
                params.append(status)
            if platform:
                where.append("platform=?")
                params.append(platform)
            sql = "SELECT * FROM collect_tasks"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    # ── 采集内容 ──

    def insert_item(self, task_id: int, platform: str, item_id: str,
                    url: str = "", title: str = "", author_name: str = "",
                    author_id: str = "", published_at: str = "",
                    text_content: str = "", tags: list = None,
                    stats: dict = None, extra: dict = None,
                    media: list = None) -> int:
        conn = self._get_conn()
        try:
            cur = conn.execute(
                """INSERT OR IGNORE INTO collect_items
                   (task_id,platform,item_id,url,title,author_name,author_id,
                    published_at,text_content,tags,stats,extra,media)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (task_id, platform, item_id, url, title, author_name, author_id,
                 published_at, text_content,
                 json.dumps(tags or [], ensure_ascii=False),
                 json.dumps(stats or {}, ensure_ascii=False),
                 json.dumps(extra or {}, ensure_ascii=False),
                 json.dumps(media or [], ensure_ascii=False))
            )
            conn.commit()
            return cur.lastrowid or self.get_item_id(platform, item_id)
        finally:
            conn.close()

    def get_item_id(self, platform: str, item_id: str) -> Optional[int]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id FROM collect_items WHERE platform=? AND item_id=?",
                (platform, item_id)
            ).fetchone()
            return row["id"] if row else None
        finally:
            conn.close()

    def item_exists(self, platform: str, item_id: str) -> bool:
        return self.get_item_id(platform, item_id) is not None

    def get_item(self, db_id: int) -> Optional[dict]:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM collect_items WHERE id=?", (db_id,)).fetchone()
            if not row:
                return None
            item = dict(row)
            for f in ("tags", "stats", "extra", "media", "ai_analysis"):
                if item.get(f):
                    try:
                        item[f] = json.loads(item[f])
                    except:
                        pass
            return item
        finally:
            conn.close()

    def list_items(self, platform: str = None, author_id: str = None,
                   limit: int = 100) -> list[dict]:
        conn = self._get_conn()
        try:
            where = []
            params = []
            if platform:
                where.append("platform=?")
                params.append(platform)
            if author_id:
                where.append("author_id=?")
                params.append(author_id)
            sql = "SELECT * FROM collect_items"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY collected_at DESC LIMIT ?"
            params.append(limit)
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    # ── 评论 ──

    def insert_comments(self, item_db_id: int, comments: list[dict]):
        if not comments:
            return
        conn = self._get_conn()
        try:
            for c in comments:
                conn.execute(
                    "INSERT INTO collect_comments (item_db_id,author_name,text,likes,replied_at) VALUES (?,?,?,?,?)",
                    (item_db_id, c.get("nickname", c.get("author", "")),
                     c.get("text", ""), c.get("digg_count", c.get("likes", 0)),
                     c.get("create_time", ""))
                )
            conn.commit()
        finally:
            conn.close()

    def get_comments(self, item_db_id: int) -> list[dict]:
        conn = self._get_conn()
        try:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM collect_comments WHERE item_db_id=? ORDER BY likes DESC",
                (item_db_id,)).fetchall()]
        finally:
            conn.close()

    # ── 采集源（定时用）──

    def upsert_source(self, platform: str, source_type: str, target: str,
                      display_name: str = "", schedule: str = "",
                      depth: str = "light", tool_level: int = 2):
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO collect_sources
                   (platform,source_type,target,display_name,schedule,depth,tool_level)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(platform,source_type,target) DO UPDATE SET
                   display_name=excluded.display_name, schedule=excluded.schedule,
                   depth=excluded.depth, tool_level=excluded.tool_level,
                   status='active'""",
                (platform, source_type, target, display_name, schedule, depth, tool_level)
            )
            conn.commit()
        finally:
            conn.close()

    def list_sources(self, status: str = None) -> list[dict]:
        conn = self._get_conn()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM collect_sources WHERE status=? ORDER BY platform,target",
                    (status,)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM collect_sources ORDER BY platform,target").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_due_sources(self) -> list[dict]:
        """返回所有到期的定时采集源"""
        conn = self._get_conn()
        try:
            # 简化版：每 2 小时执行一次的逻辑
            rows = conn.execute(
                """SELECT * FROM collect_sources
                   WHERE status='active'
                   AND (last_collected IS NULL
                        OR datetime('now','localtime','-2 hours') > last_collected)"""
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_source_collected(self, source_id: int):
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE collect_sources SET last_collected=datetime('now','localtime') WHERE id=?",
                (source_id,))
            conn.commit()
        finally:
            conn.close()

    def delete_source(self, source_id: int):
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM collect_sources WHERE id=?", (source_id,))
            conn.commit()
        finally:
            conn.close()

    # ── 统计 ──

    def count_by_platform(self) -> dict:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT platform, COUNT(*) as cnt FROM collect_items GROUP BY platform"
            ).fetchall()
            result = {}
            for r in rows:
                result[r["platform"]] = r["cnt"]
            return result
        finally:
            conn.close()

    def count_today(self) -> int:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM collect_items WHERE date(collected_at)=date('now','localtime')"
            ).fetchone()
            return row["cnt"] if row else 0
        finally:
            conn.close()

    def sources_count(self) -> int:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) as cnt FROM collect_sources WHERE status='active'").fetchone()
            return row["cnt"] if row else 0
        finally:
            conn.close()

    def task_stats(self) -> dict:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM collect_tasks GROUP BY status"
            ).fetchall()
            result = {"total": 0}
            for r in rows:
                result[r["status"]] = r["cnt"]
                result["total"] += r["cnt"]
            return result
        finally:
            conn.close()
