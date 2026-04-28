#!/usr/bin/env python3
"""
AgentOS 记忆体初始化脚本
用途：首次运行时创建 L1 索引文件、L2 事实库、L3 原文目录
使用：python3 agent_memory_init.py --root ~/agent-os
"""

import argparse
import json
import os
import sqlite3
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="AgentOS 记忆体初始化")
    parser.add_argument("--root", required=True, help="agent-os 根目录路径")
    return parser.parse_args()


def init_l1_index(root: str):
    """初始化 L1 关键词索引"""
    index_path = Path(root) / "04_memory" / "vector_db" / "keyword_index.json"
    if index_path.exists():
        print(f"[INFO] L1 索引已存在: {index_path}")
        return

    index_data = {
        "version": "1.0.0",
        "last_updated": "",
        "entries": []
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    print(f"[OK] L1 关键词索引已创建: {index_path}")


def init_l2_facts(root: str):
    """初始化 L2 事实库"""
    db_path = Path(root) / "04_memory" / "long_term" / "facts.db"
    if db_path.exists():
        print(f"[INFO] L2 事实库已存在: {db_path}")
        return

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS facts (
        id TEXT PRIMARY KEY,
        subject TEXT NOT NULL,
        predicate TEXT NOT NULL,
        object TEXT NOT NULL,
        confidence REAL DEFAULT 0.7,
        nature TEXT DEFAULT 'fact',
        domain TEXT,
        source TEXT,
        date_created TEXT,
        date_modified TEXT,
        previous_version TEXT,
        superseded_by TEXT,
        version INTEGER DEFAULT 1
    )''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_subject ON facts(subject)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_domain ON facts(domain)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_confidence ON facts(confidence)')

    conn.commit()
    conn.close()
    print(f"[OK] L2 事实库已创建: {db_path}")


def init_l3_raw(root: str):
    """初始化 L3 原文存档目录"""
    raw_dir = Path(root) / "04_memory" / "long_term" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = raw_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    print(f"[OK] L3 原文目录已就绪: {raw_dir}")


def init_logs(root: str):
    """初始化日志目录"""
    log_dir = Path(root) / "04_memory" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 创建空日志文件
    for log_name in ["kb_ingest.log", "errors.log", "conflicts.log", "kb_reclassify.log"]:
        log_file = log_dir / log_name
        if not log_file.exists():
            log_file.touch()

    print(f"[OK] 日志目录已就绪: {log_dir}")


def main():
    args = parse_args()
    root = os.path.expanduser(args.root)

    print("=" * 50)
    print("AgentOS 记忆体初始化")
    print("=" * 50)

    init_l1_index(root)
    init_l2_facts(root)
    init_l3_raw(root)
    init_logs(root)

    print()
    print("=" * 50)
    print("[OK] 记忆体初始化完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
