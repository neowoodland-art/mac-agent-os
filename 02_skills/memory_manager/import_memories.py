#!/usr/bin/env python3
"""
AgentOS 记忆导入脚本
用途：从导出归档恢复记忆，合并时智能去重
使用：python3 import_memories.py --root ~/agent-os --input ~/backup/agent-os-memory-20260426.zip
"""

import argparse
import json
import os
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="AgentOS 记忆导入")
    parser.add_argument("--root", required=True, help="agent-os 根目录路径")
    parser.add_argument("--input", required=True, help="导入的 zip 文件或目录路径")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不实际写入")
    return parser.parse_args()


def extract_source(input_path: str) -> Path:
    """从 zip 或目录获取源路径"""
    p = Path(input_path)
    if p.is_dir():
        return p
    if p.suffix == ".zip":
        extract_dir = p.parent / p.stem
        if extract_dir.exists():
            print(f"  [INFO] 解压目录已存在: {extract_dir}")
        else:
            with zipfile.ZipFile(p, "r") as z:
                z.extractall(extract_dir)
            print(f"  [OK] 已解压: {extract_dir}")
        return extract_dir
    raise ValueError(f"不支持的输入格式: {input_path}")


def import_l2(src_dir: Path, db_path: Path, dry_run: bool):
    """导入 L2 事实，智能去重"""
    src_file = src_dir / "l2_facts.json"
    if not src_file.exists():
        print("  [WARN] 未找到 l2_facts.json，跳过 L2 导入")
        return

    with open(src_file, "r", encoding="utf-8") as f:
        imported_facts = json.load(f)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 确保表存在
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

    inserted = 0
    skipped = 0
    updated = 0

    for fact in imported_facts:
        fid = fact.get("id", "")
        # 检查是否已存在
        cursor.execute("SELECT id, object, confidence FROM facts WHERE id = ?", (fid,))
        existing = cursor.fetchone()

        if existing:
            # 已存在，检查是否需要更新
            if fact.get("date_modified", "") > (existing[2] or ""):
                # 导入版本更新 → 覆盖
                if not dry_run:
                    cursor.execute(
                        """UPDATE facts SET object=?, confidence=?, nature=?, domain=?,
                           source=?, date_modified=?, version=? WHERE id=?""",
                        (fact["object"], fact["confidence"], fact["nature"],
                         fact["domain"], fact["source"], fact["date_modified"],
                         fact.get("version", 1), fid)
                    )
                updated += 1
            else:
                skipped += 1
            continue

        # 三元组去重
        cursor.execute(
            "SELECT id FROM facts WHERE subject=? AND predicate=? AND object=?",
            (fact["subject"], fact["predicate"], fact["object"])
        )
        if cursor.fetchone():
            skipped += 1
            continue

        # 新事实，插入
        if not dry_run:
            cursor.execute(
                """INSERT INTO facts
                   (id, subject, predicate, object, confidence, nature, domain, source,
                    date_created, date_modified, version)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (fid, fact["subject"], fact["predicate"], fact["object"],
                 fact.get("confidence", 0.7), fact.get("nature", "fact"),
                 fact.get("domain", ""), fact.get("source", "import"),
                 fact.get("date_created", ""), fact.get("date_modified", ""),
                 fact.get("version", 1))
            )
        inserted += 1

    if not dry_run:
        conn.commit()
    conn.close()

    print(f"  L2 导入: 新增 {inserted} 条，更新 {updated} 条，跳过 {skipped} 条")


def import_l1(src_dir: Path, index_path: Path, db_path: Path, dry_run: bool):
    """导入 L1 关键词索引，与 L2 对齐"""
    src_file = src_dir / "l1_keyword_index.json"
    if not src_file.exists():
        print("  [WARN] 未找到 l1_keyword_index.json，跳过 L1 导入")
        return

    with open(src_file, "r", encoding="utf-8") as f:
        imported_data = json.load(f)

    # 获取 L2 中实际存在的 ID
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    l2_ids = {row[0] for row in cursor.execute("SELECT id FROM facts").fetchall()}
    conn.close()

    # 读取现有 L1
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            l1 = json.load(f)
    else:
        l1 = {"version": "1.0.0", "last_updated": "", "entries": []}

    existing_ids = {e["fact_id"] for e in l1["entries"]}
    added = 0

    for entry in imported_data["entries"]:
        fid = entry["fact_id"]
        if fid in existing_ids or fid not in l2_ids:
            continue
        l1["entries"].append(entry)
        existing_ids.add(fid)
        added += 1

    l1["last_updated"] = datetime.now().isoformat()

    if not dry_run:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(l1, f, ensure_ascii=False, indent=2)

    print(f"  L1 导入: 新增 {added} 条索引")


def import_l3(src_dir: Path, raw_dir: Path, dry_run: bool):
    """导入 L3 原文存档"""
    src_l3 = src_dir / "l3_raw"
    if not src_l3.exists():
        print("  [WARN] 未找到 l3_raw/ 目录，跳过 L3 导入")
        return

    raw_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for md_file in src_l3.glob("*.md"):
        dest = raw_dir / md_file.name
        if dest.exists():
            continue  # 不覆盖已有文件
        if not dry_run:
            shutil.copy2(md_file, dest)
        count += 1

    print(f"  L3 导入: {count} 个文件")


def main():
    args = parse_args()
    root = os.path.expanduser(args.root)
    dry_run = args.dry_run

    print("=" * 50)
    print("AgentOS 记忆导入")
    if dry_run:
        print("[DRY-RUN 模式：仅预览，不写入任何文件]")
    print("=" * 50)

    src_dir = extract_source(args.input)
    print(f"导入源: {src_dir}\n")

    memory_root = Path(root) / "04_memory"
    db_path = memory_root / "long_term" / "facts.db"
    index_path = memory_root / "vector_db" / "keyword_index.json"
    raw_dir = memory_root / "long_term" / "raw"

    import_l2(src_dir, db_path, dry_run)
    import_l1(src_dir, index_path, db_path, dry_run)
    import_l3(src_dir, raw_dir, dry_run)

    print(f"\n{'✅ DRY-RUN 完成' if dry_run else '✅ 导入完成！'}")


if __name__ == "__main__":
    main()
