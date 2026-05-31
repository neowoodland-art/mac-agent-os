"""
anchor_db.py — 锚点规则数据库管理

锚点规则 + 原子操作 + 检测日志 + 校准候选 全部存储在 SQLite 中。
可拆解、可更新、可版本管理。
"""
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "anchor.db"
SCHEMA_PATH = DB_DIR / "schema.sql"


# ── 数据库初始化 ──

def get_conn() -> sqlite3.Connection:
    """获取数据库连接（每次调用创建新连接，线程安全）"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(force: bool = False):
    """初始化/重置数据库"""
    if force and DB_PATH.exists():
        DB_PATH.unlink()
    conn = get_conn()
    # 检查是否已初始化
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='anchor_rules'")
    if cursor.fetchone() and not force:
        conn.close()
        return

    # 执行 schema
    schema = SCHEMA_PATH.read_text(encoding='utf-8')
    conn.executescript(schema)
    conn.commit()
    conn.close()
    print(f"✅ 数据库已初始化: {DB_PATH}")


# ── 锚点规则 CRUD ──

def get_rules(state_name: str = None) -> list:
    """获取锚点规则
    
    Args:
        state_name: 指定状态名, None=返回所有
    Returns:
        [{state_name, field, operator, value, logic_group}, ...]
    """
    conn = get_conn()
    if state_name:
        rows = conn.execute(
            "SELECT * FROM anchor_rules WHERE state_name=? AND active=1 ORDER BY logic_group, id",
            (state_name,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM anchor_rules WHERE active=1 ORDER BY state_name, logic_group, id"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_rule(state_name: str, field: str, operator: str, value: str,
             logic_group: int = 0) -> int:
    """添加锚点规则"""
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO anchor_rules (state_name, field, operator, value, logic_group) VALUES (?,?,?,?,?)",
        (state_name, field, operator, value, logic_group)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def update_rule(rule_id: int, **kwargs):
    """更新规则字段"""
    allowed = {'field', 'operator', 'value', 'logic_group', 'active'}
    sets = []
    params = []
    for k, v in kwargs.items():
        if k in allowed:
            sets.append(f"{k}=?")
            params.append(v)
    if not sets:
        return
    params.append(rule_id)
    conn = get_conn()
    conn.execute(f"UPDATE anchor_rules SET {', '.join(sets)}, updated_at=datetime('now','localtime') WHERE id=?", params)
    conn.commit()
    conn.close()


def delete_rule(rule_id: int):
    """软删除规则"""
    update_rule(rule_id, active=0)


# ── 原子操作 CRUD ──

def get_ops(op_name: str = None) -> list:
    """获取原子操作"""
    conn = get_conn()
    if op_name:
        rows = conn.execute("SELECT * FROM atomic_ops WHERE op_name=?", (op_name,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM atomic_ops ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_op(op_name: str, description: str, action_type: str,
           target: str, verify_rule: str = None) -> int:
    """添加原子操作"""
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO atomic_ops (op_name, description, action_type, target, verify_rule) VALUES (?,?,?,?,?)",
        (op_name, description, action_type, target, verify_rule)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


# ── 检测日志 ──

def log_detection(identity: str, expected_state: str, detected_state: str,
                  match: bool, anchor_snapshot: dict = None,
                  screenshot_path: str = None):
    """记录一次锚点检测结果"""
    conn = get_conn()
    conn.execute(
        "INSERT INTO detection_logs (identity, expected_state, detected_state, match, anchor_snapshot, screenshot_path) VALUES (?,?,?,?,?,?)",
        (identity, expected_state, detected_state, int(match),
         json.dumps(anchor_snapshot, ensure_ascii=False) if anchor_snapshot else None,
         screenshot_path)
    )
    conn.commit()
    conn.close()


def get_recent_accuracy(identity: str = None, count: int = 50) -> float:
    """获取最近 N 次检测的成功率"""
    conn = get_conn()
    if identity:
        rows = conn.execute(
            "SELECT match FROM detection_logs WHERE identity=? ORDER BY id DESC LIMIT ?",
            (identity, count)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT match FROM detection_logs ORDER BY id DESC LIMIT ?",
            (count,)
        ).fetchall()
    conn.close()
    if not rows:
        return 1.0
    return sum(r['match'] for r in rows) / len(rows)


def get_recent_failures(identity: str = None, threshold: int = 5) -> bool:
    """检查最近是否连续失败 threshold 次"""
    conn = get_conn()
    if identity:
        rows = conn.execute(
            "SELECT match FROM detection_logs WHERE identity=? ORDER BY id DESC LIMIT ?",
            (identity, threshold)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT match FROM detection_logs ORDER BY id DESC LIMIT ?",
            (threshold,)
        ).fetchall()
    conn.close()
    if len(rows) < threshold:
        return False
    return all(r['match'] == 0 for r in rows)


# ── 校准候选 ──

def add_candidate(state_name: str, source: str, old_rules: list, new_rules: list) -> int:
    """添加校准候选"""
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO calibration_candidates (state_name, source, old_rules, new_rules) VALUES (?,?,?,?)",
        (state_name, source, json.dumps(old_rules, ensure_ascii=False),
         json.dumps(new_rules, ensure_ascii=False))
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def update_candidate(candidate_id: int, status: str, test_count: int = None, test_pass: int = None):
    """更新校准候选状态"""
    conn = get_conn()
    sets = ["status=?"]
    params = [status]
    if test_count is not None:
        sets.append("test_count=?")
        params.append(test_count)
    if test_pass is not None:
        sets.append("test_pass=?")
        params.append(test_pass)
    params.append(candidate_id)
    conn.execute(f"UPDATE calibration_candidates SET {', '.join(sets)} WHERE id=?", params)
    conn.commit()
    conn.close()


# ── 状态迁移 ──

def get_valid_next_states(from_state: str) -> list:
    """获取从当前状态可以迁移到哪些状态"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT to_state, via_op FROM state_transitions WHERE from_state=?",
        (from_state,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    # 初始化数据库并导入初始数据
    init_db(force=True)
    print(f"  规则数: {len(get_rules())}")
    print(f"  操作数: {len(get_ops())}")
