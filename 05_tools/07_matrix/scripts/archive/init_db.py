#!/usr/bin/env python3
"""
数据库初始化脚本 - 创建任务蓝图 SQLite 数据库
"""
import sqlite3
from local_paths import data_path

DB_PATH = data_path("matrix.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript("""
    -- 任务蓝图主表
    CREATE TABLE IF NOT EXISTS task_blueprints (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        task_name TEXT NOT NULL,
        platform TEXT NOT NULL,
        version TEXT NOT NULL DEFAULT '1.0.0',
        status TEXT NOT NULL DEFAULT 'active',
        browser_framework TEXT DEFAULT 'chrome',
        viewport_config TEXT,
        entry_conditions TEXT,
        steps_json TEXT,
        completion_check_json TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        deprecation_reason TEXT,
        replaced_by_version TEXT
    );

    -- 任务执行记录表
    CREATE TABLE IF NOT EXISTS task_executions (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        blueprint_id TEXT NOT NULL,
        account_id TEXT NOT NULL,
        browser_framework TEXT,
        proxy_ip TEXT,
        status TEXT NOT NULL DEFAULT 'running',
        started_at TEXT DEFAULT (datetime('now')),
        completed_at TEXT,
        duration_ms INTEGER,
        error_message TEXT,
        screenshots TEXT,
        logs TEXT
    );

    -- 原子操作执行日志
    CREATE TABLE IF NOT EXISTS operation_logs (
        id TEXT PRIMARY KEY,
        execution_id TEXT NOT NULL,
        step_id INTEGER,
        atomic_operation TEXT,
        pre_checks_passed INTEGER DEFAULT 0,
        execution_success INTEGER DEFAULT 0,
        post_checks_passed INTEGER DEFAULT 0,
        locator_used TEXT,
        duration_ms INTEGER,
        error_detail TEXT,
        screenshot_path TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    -- UI变更记录
    CREATE TABLE IF NOT EXISTS ui_changes (
        id TEXT PRIMARY KEY,
        task_id TEXT,
        platform TEXT,
        detected_at TEXT DEFAULT (datetime('now')),
        element_changed TEXT,
        old_selector TEXT,
        new_selector TEXT,
        affected_blueprints TEXT,
        resolution TEXT DEFAULT 'pending',
        notes TEXT
    );

    -- 账号信息表
    CREATE TABLE IF NOT EXISTS accounts (
        id TEXT PRIMARY KEY,
        platform TEXT NOT NULL,
        username TEXT,
        phone TEXT,
        profile_dir TEXT,
        cdp_port INTEGER,
        status TEXT DEFAULT 'active',
        last_active TEXT,
        cookie_valid_until TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    -- 索引
    CREATE INDEX IF NOT EXISTS idx_blueprints_task ON task_blueprints(task_id, status);
    CREATE INDEX IF NOT EXISTS idx_executions_account ON task_executions(account_id, started_at);
    CREATE INDEX IF NOT EXISTS idx_executions_status ON task_executions(status);
    CREATE INDEX IF NOT EXISTS idx_op_logs_exec ON operation_logs(execution_id);
    """)

    conn.commit()
    conn.close()
    print(f"✅ 数据库已初始化: {DB_PATH}")


if __name__ == "__main__":
    init_db()
