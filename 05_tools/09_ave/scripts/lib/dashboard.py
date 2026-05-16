from __future__ import annotations

"""
AVE dashboard — 生产监控数据层

职责:
  SQLite schema 初始化 + 埋点封装
  CLI 自动写 DB, FastAPI 后端读 DB

设计原则:
  - 所有操作 try/except 包裹, 失败不影响 CLI 主线
  - DB 路径: agent-local/tools/ave/data/ave.db
  - 连接池: 每次调用创建新连接 (CLI 场景, 无并发问题)

用法:
  from lib.dashboard import init_db, log_production, log_step, log_asset

  init_db()
  pid = log_production(strategy="oral", script_name="test", config={"key": "val"})
  log_step(pid, "tts", "completed", cost=0.3, detail="85字")
  log_step(pid, "compose", "completed", cost=0.0, detail="2 clips")
  log_asset(pid, "generated_clip", "/tmp/out.mp4", tags=["hermit", "kling"])
"""
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

# ── DB 路径 ───────────────────────────────────────────────
LOCAL_ROOT = Path(os.environ.get("AVE_LOCAL_DIR",
    str(Path.home() / "workbuddy-agent-os/agent-local")))
DB_DIR = LOCAL_ROOT / "tools" / "ave" / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "ave.db"

# ── Schema ────────────────────────────────────────────────
# 从 PLANS/DASHBOARD_DESIGN.md 导出, 6 表
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS productions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy        TEXT NOT NULL,
    status          TEXT DEFAULT 'running',
    script_path     TEXT,
    script_name     TEXT,
    output_path     TEXT,
    duration_sec    REAL,
    total_cost      REAL DEFAULT 0.0,
    config_json     TEXT,
    error_message   TEXT,
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    completed_at    TEXT
);

CREATE TABLE IF NOT EXISTS production_steps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    production_id   INTEGER NOT NULL REFERENCES productions(id),
    step_name       TEXT NOT NULL,
    status          TEXT DEFAULT 'pending',
    started_at      TEXT,
    ended_at        TEXT,
    duration_sec    REAL,
    cost            REAL DEFAULT 0.0,
    detail          TEXT,
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS assets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_type      TEXT NOT NULL,
    name            TEXT,
    file_path       TEXT,
    file_size       INTEGER,
    hash            TEXT,
    source          TEXT,
    meta_json       TEXT,
    production_id   INTEGER,
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS asset_tags (
    asset_id        INTEGER NOT NULL REFERENCES assets(id),
    tag             TEXT NOT NULL,
    PRIMARY KEY (asset_id, tag)
);

CREATE TABLE IF NOT EXISTS production_assets (
    production_id   INTEGER NOT NULL REFERENCES productions(id),
    asset_id        INTEGER NOT NULL REFERENCES assets(id),
    role            TEXT,
    PRIMARY KEY (production_id, asset_id)
);

CREATE TABLE IF NOT EXISTS cost_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    production_id   INTEGER REFERENCES productions(id),
    step_name       TEXT,
    service         TEXT NOT NULL,
    duration_s      REAL DEFAULT 0,
    resolution      TEXT,
    chars           INTEGER DEFAULT 0,
    cost_yuan       REAL DEFAULT 0,
    status          TEXT DEFAULT 'success',
    note            TEXT,
    logged_at       TEXT DEFAULT (datetime('now','localtime'))
);
"""


# ═══════════════════════════════════════════════════════════
# 初始化
# ═══════════════════════════════════════════════════════════

def init_db() -> bool:
    """初始化 DB schema, 不存在则创建"""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"  [dashboard] DB 初始化失败: {e}")
        return False


def _get_conn() -> sqlite3.Connection | None:
    """获取 DB 连接 (带 try/except)"""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"  [dashboard] DB 连接失败: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# 埋点函数
# ═══════════════════════════════════════════════════════════

def log_production(
    strategy: str,
    script_path: str = "",
    script_name: str = "",
    config: dict | None = None,
) -> int:
    """
    记录一条 production 开始

    返回:
      production_id (失败返回 -1)
    """
    conn = _get_conn()
    if not conn:
        return -1
    try:
        cur = conn.execute(
            """INSERT INTO productions (strategy, status, script_path, script_name, config_json)
               VALUES (?, 'running', ?, ?, ?)""",
            (strategy, script_path, script_name, json.dumps(config or {}, ensure_ascii=False)),
        )
        conn.commit()
        pid = cur.lastrowid
        return pid
    except Exception as e:
        print(f"  [dashboard] log_production 失败: {e}")
        return -1
    finally:
        conn.close()


def complete_production(
    production_id: int,
    status: str = "completed",
    output_path: str = "",
    duration_sec: float = 0.0,
    total_cost: float = 0.0,
    error_message: str = "",
):
    """标记 production 完成"""
    conn = _get_conn()
    if not conn:
        return
    try:
        conn.execute(
            """UPDATE productions SET status=?, output_path=?, duration_sec=?,
               total_cost=?, error_message=?, completed_at=datetime('now','localtime')
               WHERE id=?""",
            (status, output_path, duration_sec, total_cost, error_message, production_id),
        )
        conn.commit()
    except Exception as e:
        print(f"  [dashboard] complete_production 失败: {e}")
    finally:
        conn.close()


def log_step(
    production_id: int,
    step_name: str,
    status: str = "completed",
    cost: float = 0.0,
    detail: str = "",
    error_message: str = "",
) -> bool:
    """
    记录一步生产步骤

    参数:
      production_id: 所属 production ID
      step_name: 步骤名 (tts, search_material, compose, bgm, lipsync, ...)
      status: completed / failed
      cost: 该步骤费用
      detail: 文字详情
    """
    conn = _get_conn()
    if not conn:
        return False
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """INSERT INTO production_steps
               (production_id, step_name, status, started_at, ended_at, cost, detail, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (production_id, step_name, status, now, now, cost, detail, error_message),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"  [dashboard] log_step 失败: {e}")
        return False
    finally:
        conn.close()


def log_asset(
    production_id: int,
    asset_type: str,
    file_path: str = "",
    name: str = "",
    source: str = "",
    tags: list[str] | None = None,
    meta: dict | None = None,
) -> int:
    """
    记录一个生成/使用的资产

    返回:
      asset_id (失败返回 -1)
    """
    conn = _get_conn()
    if not conn:
        return -1
    try:
        file_size = os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0
        cur = conn.execute(
            """INSERT INTO assets (asset_type, name, file_path, file_size, source, meta_json, production_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (asset_type, name, file_path, file_size, source,
             json.dumps(meta or {}, ensure_ascii=False), production_id),
        )
        aid = cur.lastrowid

        # 关联 production ↔ asset
        conn.execute(
            "INSERT OR IGNORE INTO production_assets (production_id, asset_id, role) VALUES (?, ?, ?)",
            (production_id, aid, "output" if source == "generated" else "input"),
        )

        # 标签
        if tags:
            for tag in tags:
                conn.execute(
                    "INSERT OR IGNORE INTO asset_tags (asset_id, tag) VALUES (?, ?)",
                    (aid, tag.strip().lower()),
                )

        conn.commit()
        return aid
    except Exception as e:
        print(f"  [dashboard] log_asset 失败: {e}")
        return -1
    finally:
        conn.close()


def log_cost(
    production_id: int,
    service: str,
    step_name: str = "",
    duration_s: float = 0.0,
    resolution: str = "",
    chars: int = 0,
    cost_yuan: float = 0.0,
    status: str = "success",
    note: str = "",
):
    """记录费用明细"""
    conn = _get_conn()
    if not conn:
        return
    try:
        conn.execute(
            """INSERT INTO cost_log
               (production_id, step_name, service, duration_s, resolution, chars, cost_yuan, status, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (production_id, step_name, service, duration_s, resolution, chars, cost_yuan, status, note),
        )
        conn.commit()

        # 更新 production 累计费用
        conn.execute(
            "UPDATE productions SET total_cost = total_cost + ? WHERE id = ?",
            (cost_yuan, production_id),
        )
        conn.commit()
    except Exception as e:
        print(f"  [dashboard] log_cost 失败: {e}")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# 查询 API (供 FastAPI 后端使用)
# ═══════════════════════════════════════════════════════════

def get_productions(
    limit: int = 50,
    offset: int = 0,
    strategy: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """查询 production 列表"""
    conn = _get_conn()
    if not conn:
        return []
    try:
        where = []
        params = []
        if strategy:
            where.append("strategy = ?")
            params.append(strategy)
        if status:
            where.append("status = ?")
            params.append(status)
        where_clause = (" WHERE " + " AND ".join(where)) if where else ""
        rows = conn.execute(
            f"SELECT * FROM productions{where_clause} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"  [dashboard] get_productions 失败: {e}")
        return []
    finally:
        conn.close()


def get_production_detail(production_id: int) -> dict | None:
    """查询单条 production + steps + assets + costs"""
    conn = _get_conn()
    if not conn:
        return None
    try:
        prod = conn.execute(
            "SELECT * FROM productions WHERE id = ?", (production_id,)
        ).fetchone()
        if not prod:
            return None

        steps = conn.execute(
            "SELECT * FROM production_steps WHERE production_id = ? ORDER BY id",
            (production_id,),
        ).fetchall()

        assets = conn.execute(
            """SELECT a.*, GROUP_CONCAT(at.tag, ',') as tags
               FROM assets a
               LEFT JOIN asset_tags at ON at.asset_id = a.id
               WHERE a.production_id = ?
               GROUP BY a.id ORDER BY a.id""",
            (production_id,),
        ).fetchall()

        costs = conn.execute(
            "SELECT * FROM cost_log WHERE production_id = ? ORDER BY id",
            (production_id,),
        ).fetchall()

        return {
            "production": dict(prod),
            "steps": [dict(s) for s in steps],
            "assets": [dict(a) for a in assets],
            "costs": [dict(c) for c in costs],
        }
    except Exception as e:
        print(f"  [dashboard] get_production_detail 失败: {e}")
        return None
    finally:
        conn.close()


def get_assets(asset_type: str | None = None, tag: str | None = None,
               limit: int = 100, offset: int = 0) -> list[dict]:
    """查询资产列表"""
    conn = _get_conn()
    if not conn:
        return []
    try:
        where = []
        params = []
        if asset_type:
            where.append("a.asset_type = ?")
            params.append(asset_type)
        if tag:
            where.append("EXISTS (SELECT 1 FROM asset_tags WHERE asset_id = a.id AND tag = ?)")
            params.append(tag.lower())
        where_clause = (" WHERE " + " AND ".join(where)) if where else ""

        rows = conn.execute(
            f"""SELECT a.*, GROUP_CONCAT(at.tag, ',') as tags
                FROM assets a
                LEFT JOIN asset_tags at ON at.asset_id = a.id
                {where_clause}
                GROUP BY a.id
                ORDER BY a.id DESC LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"  [dashboard] get_assets 失败: {e}")
        return []
    finally:
        conn.close()


def get_summary() -> dict:
    """获取总览统计"""
    conn = _get_conn()
    if not conn:
        return {}
    try:
        total_prods = conn.execute("SELECT COUNT(*) FROM productions").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM productions WHERE status='completed'").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM productions WHERE status='failed'").fetchone()[0]
        total_cost = conn.execute("SELECT COALESCE(SUM(total_cost), 0) FROM productions").fetchone()[0]
        total_assets = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        # 本月
        month_start = datetime.now().strftime("%Y-%m-01")
        month_prods = conn.execute(
            "SELECT COUNT(*) FROM productions WHERE created_at >= ?", (month_start,)
        ).fetchone()[0]
        month_cost = conn.execute(
            "SELECT COALESCE(SUM(total_cost), 0) FROM productions WHERE created_at >= ?",
            (month_start,),
        ).fetchone()[0]

        return {
            "total_productions": total_prods,
            "completed": completed,
            "failed": failed,
            "total_cost": round(total_cost, 2),
            "total_assets": total_assets,
            "month_productions": month_prods,
            "month_cost": round(month_cost, 2),
        }
    except Exception as e:
        print(f"  [dashboard] get_summary 失败: {e}")
        return {}
    finally:
        conn.close()


def get_cost_breakdown() -> list[dict]:
    """按策略统计费用"""
    conn = _get_conn()
    if not conn:
        return []
    try:
        rows = conn.execute(
            """SELECT strategy,
                      COUNT(*) as count,
                      COALESCE(SUM(duration_sec), 0) as total_duration,
                      COALESCE(SUM(total_cost), 0) as total_cost,
                      ROUND(AVG(total_cost), 2) as avg_cost
               FROM productions
               GROUP BY strategy
               ORDER BY total_cost DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()
