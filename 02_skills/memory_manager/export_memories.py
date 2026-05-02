#!/usr/bin/env python3
"""
AgentOS 记忆导出脚本
用途：将 L1 索引 + L2 事实库 + L3 原文目录 + 日志打包为 JSON + Markdown 归档
使用：python3 export_memories.py --root ~/workbuddy-agent-os/agent-sync --output ~/backup/
"""

import argparse
import json
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="AgentOS 记忆导出")
    parser.add_argument("--root", required=True, help="agent-os 根目录路径")
    parser.add_argument("--output", required=True, help="导出目录路径")
    return parser.parse_args()


def export_l2(db_path: str, output_dir: Path):
    """导出 L2 事实库为 JSON"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM facts ORDER BY date_created DESC")
    facts = [dict(row) for row in cursor.fetchall()]
    conn.close()

    out_file = output_dir / "l2_facts.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(facts, f, ensure_ascii=False, indent=2)
    print(f"  [OK] L2 导出: {len(facts)} 条事实 → {out_file.name}")
    return facts


def export_l1(index_path: Path, output_dir: Path):
    """导出 L1 关键词索引"""
    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    out_file = output_dir / "l1_keyword_index.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] L1 导出: {len(data['entries'])} 条索引 → {out_file.name}")


def export_l3(raw_dir: Path, output_dir: Path):
    """导出 L3 原文存档"""
    l3_out = output_dir / "l3_raw"
    l3_out.mkdir(parents=True, exist_ok=True)
    count = 0
    for md_file in raw_dir.glob("*.md"):
        shutil.copy2(md_file, l3_out / md_file.name)
        count += 1
    print(f"  [OK] L3 导出: {count} 个文件 → l3_raw/")


def export_logs(log_dir: Path, output_dir: Path):
    """导出日志文件"""
    logs_out = output_dir / "logs"
    logs_out.mkdir(parents=True, exist_ok=True)
    count = 0
    for log_file in log_dir.glob("*.log"):
        shutil.copy2(log_file, logs_out / log_file.name)
        count += 1
    print(f"  [OK] 日志导出: {count} 个文件 → logs/")


def main():
    args = parse_args()
    root = os.path.expanduser(args.root)
    output_dir = Path(os.path.expanduser(args.output))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = output_dir / f"agent-os-memory-{timestamp}"
    export_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("AgentOS 记忆导出")
    print("=" * 50)
    print(f"源目录: {root}/04_memory/")
    print(f"导出到: {export_dir}\n")

    # 写入元数据
    meta = {
        "export_time": datetime.now().isoformat(),
        "source_root": root,
        "agent_os_version": "2.0",
    }
    with open(export_dir / "export_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 逐层导出
    memory_root = Path(root) / "04_memory"
    export_l1(memory_root / "vector_db" / "keyword_index.json", export_dir)
    export_l2(str(memory_root / "long_term" / "facts.db"), export_dir)
    export_l3(memory_root / "long_term" / "raw", export_dir)
    export_logs(memory_root / "logs", export_dir)

    # 打包（可选）
    archive_path = str(export_dir) + ".zip"
    shutil.make_archive(str(export_dir), "zip", export_dir.parent, export_dir.name)

    print(f"\n[OK] 导出完成！")
    print(f"  目录: {export_dir}")
    print(f"  压缩包: {archive_path}")


if __name__ == "__main__":
    main()
