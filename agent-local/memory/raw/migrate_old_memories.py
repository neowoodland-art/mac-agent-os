"""
一次性迁移脚本：将旧版 agent-os/.workbuddy/memory/ → 新版 facts.db
使用 bootstrap_from_memory.py 的解析逻辑，直接插入新系统
"""
import sys, os, sqlite3, re, json
from datetime import datetime
from pathlib import Path

# 插入父目录以导入 bootstrap_from_memory
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "02_skills" / "memory_manager"))
from bootstrap_from_memory import parse_daily_log, parse_memory_md, insert_facts_to_l2, ensure_db, _infer_domain, _infer_predicate

ROOT = Path.home() / "workbuddy-agent-os" / "agent-sync"
RAW_DIR = Path(__file__).resolve().parent
TODAY = datetime.now().strftime("%Y-%m-%d")

def main():
    print("=" * 60)
    print("旧版记忆 → 新版 facts.db 迁移")
    print(f"来源: {RAW_DIR}")
    print(f"目标: {ROOT / '04_memory' / 'long_term' / 'facts.db'}")
    print("=" * 60)

    db_path = ensure_db(str(ROOT))
    all_facts = []

    # 1. MEMORY.md（长期记忆）
    mem_path = RAW_DIR / "MEMORY.md"
    if mem_path.exists() and mem_path.stat().st_size > 0:
        print(f"\n[来源1] MEMORY.md")
        content = mem_path.read_text(encoding="utf-8")
        facts = parse_memory_md(content)
        print(f"  → 解析出 {len(facts)} 条")
        all_facts.extend(facts)
    else:
        print(f"\n[来源1] MEMORY.md 为空或不存，跳过")

    # 2. 每日工作日志
    print(f"\n[来源2] 工作日志 ({RAW_DIR})")
    log_files = sorted(RAW_DIR.glob("????-??-??.md"))
    log_total = 0
    for log_file in log_files:
        if log_file.name == "MEMORY.md":
            continue
        date_str = log_file.stem
        content = log_file.read_text(encoding="utf-8")
        facts = parse_daily_log(content, date_str)
        # 也尝试解析 **Key**: Value 格式（与 MEMORY.md 共用解析器）
        facts_mem = parse_memory_md(content)
        all_unique = []
        seen = set()
        for f in facts + facts_mem:
            key = (f["predicate"], f["object"])
            if key not in seen:
                seen.add(key)
                all_unique.append(f)
        print(f"  → {date_str}: {len(all_unique)} 条")
        log_total += len(all_unique)
        all_facts.extend(all_unique)

    print(f"\n  合计解析: {len(all_facts)} 条")

    # 3. 写入 L2
    print(f"\n[写入] L2 facts.db")
    result = insert_facts_to_l2(db_path, all_facts, dry_run=False)
    print(f"  新增: {result['inserted']} 条, 跳过(重复): {result['skipped']} 条")

    # 4. 验证
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM facts")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM facts WHERE source LIKE 'daily_log_%'")
    daily = cursor.fetchone()[0]
    cursor.execute("SELECT source, COUNT(*) FROM facts GROUP BY source ORDER BY COUNT(*) DESC LIMIT 10")
    sources = cursor.fetchall()
    conn.close()

    print(f"\n[验证] facts.db 总计: {total} 条")
    print(f"  其中每日日志来源: {daily} 条")
    print(f"  来源分布: {dict(sources)}")

    print("\n✅ 迁移完成")

if __name__ == "__main__":
    main()
