#!/usr/bin/env python3
"""
蓝图入库脚本 — 将蓝图 JSON 写入 matrix.db
同时更新选择器手册到数据库
"""
import json
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime

from local_paths import data_path, config_path, code_dir

BASE_DIR = code_dir()
DB_PATH = data_path("matrix.db")
BLUEPRINT_DIR = code_dir() / "blueprints"


def seed_blueprints():
    """将所有蓝图 JSON 写入 task_blueprints 表"""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # 确保 task_blueprints 表存在
    cur.executescript("""
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
    """)

    # 扫描蓝图目录
    bp_files = list(BLUEPRINT_DIR.glob("*.json"))
    print(f"找到 {len(bp_files)} 个蓝图文件")

    for bp_file in bp_files:
        with open(bp_file, encoding="utf-8") as f:
            bp = json.load(f)

        bp_id = bp.get("id", bp_file.stem)
        task_id = f"task_{bp_id}"
        task_name = bp.get("name", bp_id)
        platform = bp.get("platform", "douyin")
        version = bp.get("version", "1.0.0")
        steps_json = json.dumps(bp.get("steps", []), ensure_ascii=False)
        entry_conditions = json.dumps({
            "entry_url": bp.get("entry_url", ""),
            "entry_page": bp.get("entry_page", ""),
        }, ensure_ascii=False)

        # 检查是否已存在
        existing = cur.execute(
            "SELECT id, version FROM task_blueprints WHERE id = ?", (bp_id,)
        ).fetchone()

        if existing:
            # 更新
            cur.execute("""
                UPDATE task_blueprints SET
                    task_name = ?, steps_json = ?, entry_conditions = ?,
                    version = ?, updated_at = datetime('now'), status = 'active'
                WHERE id = ?
            """, (task_name, steps_json, entry_conditions, version, bp_id))
            print(f"  🔄 更新: {bp_id} v{version}")
        else:
            # 插入
            cur.execute("""
                INSERT INTO task_blueprints
                (id, task_id, task_name, platform, version, status,
                 browser_framework, steps_json, entry_conditions)
                VALUES (?, ?, ?, ?, ?, 'active', 'chrome', ?, ?)
            """, (bp_id, task_id, task_name, platform, version, steps_json, entry_conditions))
            print(f"  ✅ 新增: {bp_id} v{version}")

    # 标记旧版 douyin_browse 为 deprecated
    cur.execute("""
        UPDATE task_blueprints SET
            status = 'deprecated',
            deprecation_reason = '被 douyin_browse_v2 替代，V2使用data-e2e选择器',
            replaced_by_version = '2.0.0',
            updated_at = datetime('now')
        WHERE id = 'douyin_browse' AND status = 'active'
    """)

    conn.commit()
    conn.close()
    print(f"\n✅ 蓝图入库完成")


def seed_selectors():
    """将选择器手册关键数据写入数据库（ui_changes 表用作选择器存档）"""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    selectors = {
        # 全局
        "search_input": '[data-e2e="searchbar-input"]',
        "search_button": '[data-e2e="searchbar-button"]',
        "nav_recommend": '[data-e2e="douyin-navigation"] a:has-text("推荐")',
        # 视频互动
        "digg": '[data-e2e="video-player-digg"]',
        "comment_icon": '[data-e2e="feed-comment-icon"]',
        "collect": '[data-e2e="video-player-collect"]',
        "share": '[data-e2e="video-player-share"]',
        "follow": '[data-e2e="feed-follow-icon"]',
        "prev_arrow": '[data-e2e="video-switch-prev-arrow"]',
        "next_arrow": '[data-e2e="video-switch-next-arrow"]',
        # 评论区
        "comment_list": '[data-e2e="comment-list"]',
        "comment_editor": '.public-DraftEditor-content',
        "comment_send": '.commentInput-right-ct .WFB7wUOX',
        # 搜索结果
        "search_card": '.search-result-card',
        # 验证码
        "verify_panel": '.second-verify-panel',
        "verify_input": '.uc-ui-verify_sms-verify_input',
        "verify_confirm": '.uc-ui-verify_sms-verify_button.primary',
        "verify_cancel": '.uc-ui-verify_sms-verify_button.second',
    }

    for name, selector in selectors.items():
        cur.execute("""
            INSERT OR REPLACE INTO ui_changes
            (id, task_id, platform, element_changed, old_selector, new_selector, resolution, notes)
            VALUES (?, ?, ?, ?, ?, ?, 'current', ?)
        """, (
            f"selector_{name}", "douyin_all", "douyin",
            name, selector, selector,
            f"抖音 Web 选择器 | 验证时间: {datetime.now().strftime('%Y-%m-%d')}"
        ))

    conn.commit()
    conn.close()
    print(f"✅ {len(selectors)} 个选择器已存档")


def seed_accounts():
    """更新 accounts 表"""
    import yaml

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    accounts_file = config_path("accounts.yaml")
    if accounts_file.exists():
        with open(accounts_file, encoding="utf-8") as f:
            accounts = yaml.safe_load(f).get("accounts", [])

        for acc in accounts:
            cur.execute("""
                INSERT OR REPLACE INTO accounts
                (id, platform, username, phone, profile_dir, cdp_port, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                acc["id"], acc.get("platform", ""),
                acc.get("username", ""), acc.get("phone", ""),
                acc.get("profile_dir", ""), acc.get("port", 9222),
                "active" if acc.get("enabled", True) else "inactive",
                acc.get("notes", "")
            ))
        conn.commit()
        print(f"✅ {len(accounts)} 个账号已同步到数据库")

    conn.close()


if __name__ == "__main__":
    seed_blueprints()
    seed_selectors()
    seed_accounts()
