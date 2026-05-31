#!/usr/bin/env python3
"""
AgentOS 记忆清理与冲突消解脚本
用途：清理过期记忆、消解冲突、归档冷数据
使用：python3 memory_cleanup.py --root ~/workbuddy-agent-os/agent-sync [--dry-run]
"""

import argparse
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="AgentOS 记忆清理")
    parser.add_argument("--root", required=True, help="agent-os 根目录路径")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不实际执行")
    return parser.parse_args()


def cleanup_expired_facts(root: str, dry_run: bool = False):
    """清理过期事实（技术类知识 180 天未更新自动标记待复核）"""
    db_path = Path(root) / "04_memory" / "long_term" / "facts.db"
    if not db_path.exists():
        print("[WARN] facts.db 不存在，跳过")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 查找 180 天未更新的技术类事实
    cutoff = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT id, subject, date_modified FROM facts WHERE date_modified < ? AND nature != 'axiom' AND nature != 'opinion'",
        (cutoff,)
    )
    expired = cursor.fetchall()

    if not expired:
        print("[INFO] 无过期事实")
        conn.close()
        return

    print(f"[INFO] 发现 {len(expired)} 条可能过期的事实:")
    for fact in expired:
        print(f"  - {fact[0]}: {fact[1]} (最后更新: {fact[2]})")

    if not dry_run:
        for fact in expired:
            cursor.execute(
                "UPDATE facts SET confidence = confidence * 0.8 WHERE id = ?",
                (fact[0],)
            )
        conn.commit()
        print(f"[OK] 已降低 {len(expired)} 条过期事实的置信度")

    conn.close()


def archive_cold_data(root: str, dry_run: bool = False):
    """归档冷数据（超过 180 天未被检索的数据）"""
    archive_dir = Path(root) / "03_knowledge" / "90_archive" / "deprecated"

    # 检查 03_knowledge 下的文件修改时间
    knowledge_dir = Path(root) / "03_knowledge"
    cutoff = datetime.now() - timedelta(days=180)
    cold_files = []

    for md_file in knowledge_dir.rglob("*.md"):
        if "99_system" in str(md_file) or "90_archive" in str(md_file):
            continue
        mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
        if mtime < cutoff:
            cold_files.append(md_file)

    if cold_files:
        print(f"[INFO] 发现 {len(cold_files)} 个冷知识文件:")
        for f in cold_files:
            print(f"  - {f.relative_to(knowledge_dir)}")
        if not dry_run:
            print("[INFO] 冷数据归档需要确认，请手动处理或通过 kb_manager 技能执行")
    else:
        print("[INFO] 无冷数据需要归档")


def resolve_conflicts(root: str, dry_run: bool = False):
    """消解记忆冲突"""
    log_path = Path(root) / "04_memory" / "logs" / "conflicts.log"
    if not log_path.exists() or log_path.stat().st_size == 0:
        print("[INFO] 无待消解冲突")
        return

    with open(log_path, "r", encoding="utf-8") as f:
        conflicts = f.readlines()

    if conflicts:
        print(f"[INFO] 发现 {len(conflicts)} 条冲突记录:")
        for c in conflicts[:10]:  # 只显示前 10 条
            print(f"  - {c.strip()}")
        if len(conflicts) > 10:
            print(f"  ... 还有 {len(conflicts) - 10} 条")


def main():
    args = parse_args()
    root = os.path.expanduser(args.root)
    dry_run = args.dry_run

    print("=" * 50)
    print("AgentOS 记忆清理")
    if dry_run:
        print("[DRY-RUN 模式：仅预览，不执行]")
    print("=" * 50)

    cleanup_expired_facts(root, dry_run)
    archive_cold_data(root, dry_run)
    resolve_conflicts(root, dry_run)

    print()
    print("[OK] 记忆清理完成")


if __name__ == "__main__":
    main()
