#!/usr/bin/env python3
"""
AgentOS 记忆体冷启动脚本
用途：首次运行时，将已有的 MEMORY.md 和工作日志全量写入 L1/L2/L3
      这是记忆系统的「时间起点」——没有此步骤，L1/L2 将永远为空

使用：
  python3 bootstrap_from_memory.py --root ~/agent-os
  python3 bootstrap_from_memory.py --root ~/agent-os --dry-run   # 预览不写入

数据来源（全量导入）：
  1. ~/WorkBuddy/Claw/.workbuddy/memory/MEMORY.md       ← 长期精炼记忆
  2. ~/WorkBuddy/Claw/.workbuddy/memory/YYYY-MM-DD.md   ← 所有历史日志
  3. ~/.workbuddy/memery/*.md                            ← 系统用户画像（V79+）
"""

import argparse
import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

WORKBUDDY_MEMORY_DIR = Path.home() / "WorkBuddy" / "Claw" / ".workbuddy" / "memory"
WORKBUDDY_SYSTEM_MEMERY_DIR = Path.home() / ".workbuddy" / "memery"

TODAY = datetime.now().strftime("%Y-%m-%d")


def parse_args():
    parser = argparse.ArgumentParser(description="AgentOS 记忆体冷启动")
    parser.add_argument("--root", required=True, help="agent-os 根目录路径")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入")
    return parser.parse_args()


def ensure_db(root: str):
    """确保 L2 数据库存在并建好表"""
    db_path = Path(root) / "04_memory" / "long_term" / "facts.db"
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
    return db_path


def parse_memory_md(content: str) -> list:
    """
    解析 MEMORY.md 的结构化内容，提取事实列表。
    支持格式：
      - **字段名**：值
      - 普通列表项
    """
    facts = []
    lines = content.split("\n")
    current_section = "general"

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(">"):
            continue

        # 章节标题
        if stripped.startswith("## "):
            current_section = stripped[3:].strip()
            continue
        if stripped.startswith("# "):
            continue

        # 格式 1：**Key**：Value 或 **Key**: Value
        m = re.match(r'\*\*(.+?)\*\*[：:]\s*(.+)', stripped)
        if m:
            key, value = m.group(1).strip(), m.group(2).strip()
            if len(value) > 5:
                facts.append({
                    "subject": "ghai",
                    "predicate": key,
                    "object": value[:300],
                    "confidence": 0.9,
                    "nature": "fact",
                    "domain": _infer_domain(current_section, value),
                    "source": "MEMORY.md"
                })
            continue

        # 格式 2：- 列表项（含有实质内容的行）
        if stripped.startswith("- ") and len(stripped) > 10:
            item = stripped[2:].strip()
            # 过滤纯说明性短句
            if len(item) < 15 or item.startswith("(") or item.startswith("（"):
                continue
            predicate = _infer_predicate(current_section, item)
            facts.append({
                "subject": "ghai",
                "predicate": predicate,
                "object": item[:300],
                "confidence": 0.8,
                "nature": "fact",
                "domain": _infer_domain(current_section, item),
                "source": "MEMORY.md"
            })

    return facts


def _infer_domain(section: str, text: str) -> str:
    """根据章节标题和内容推断 domain"""
    section_lower = section.lower()
    if any(w in section_lower for w in ["项目", "工具", "agenos", "技能"]):
        return "engineering"
    if any(w in section_lower for w in ["偏好", "用户", "个人"]):
        return "personal-management"
    if any(w in section_lower for w in ["金融", "股票", "finance"]):
        return "finance"
    if any(w in text for w in ["代码", "脚本", "Node", "Python", "npm"]):
        return "engineering"
    return "personal-management"


def _infer_predicate(section: str, text: str) -> str:
    """根据章节和文本推断谓语"""
    if "偏好" in section or "偏好" in text:
        return "preference"
    if "工具" in section or "工具链" in section:
        return "uses_tool"
    if "项目" in section:
        return "owns_project"
    if "关注" in section:
        return "focuses_on"
    if "动态" in section:
        return "recent_activity"
    return "knows"


def parse_daily_log(content: str, date: str) -> list:
    """解析每日工作日志，提取完成事项和决策"""
    facts = []
    lines = content.split("\n")
    current_section = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("## ") or stripped.startswith("### "):
            current_section = stripped.lstrip("#").strip()
            continue

        # 提取列表项（已完成事项）
        if (stripped.startswith("- ") or stripped.startswith("✅") or
                stripped.startswith("1.") or re.match(r'^\d+\.', stripped)):
            item = re.sub(r'^[-\d\.\s✅]+', '', stripped).strip()
            if len(item) < 10:
                continue
            facts.append({
                "subject": "ghai",
                "predicate": "completed",
                "object": (f"[{current_section}] " if current_section else "") + item[:250],
                "confidence": 0.8,
                "nature": "fact",
                "domain": _infer_domain(current_section, item),
                "source": f"daily_log_{date}"
            })

    return facts


def insert_facts_to_l2(db_path: Path, facts: list, dry_run: bool = False) -> dict:
    """批量插入事实到 L2，自动去重"""
    if dry_run:
        print(f"  [DRY-RUN] 将写入 {len(facts)} 条事实到 L2")
        for f in facts[:5]:
            print(f"    → [{f['domain']}] {f['predicate']}: {f['object'][:60]}...")
        if len(facts) > 5:
            print(f"    ... 还有 {len(facts)-5} 条")
        return {"inserted": 0, "skipped": len(facts)}

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    inserted = 0
    skipped = 0

    # 获取全局已有总数，用于生成唯一 ID
    cursor.execute("SELECT COUNT(*) FROM facts")
    base = cursor.fetchone()[0]

    for i, fact in enumerate(facts):
        # 精确去重：subject + predicate + object 三元组完全相同才跳过
        cursor.execute(
            "SELECT id FROM facts WHERE subject=? AND predicate=? AND object=?",
            (fact["subject"], fact["predicate"], fact["object"])
        )
        if cursor.fetchone():
            skipped += 1
            continue

        fact_id = f"FACT-BOOTSTRAP-{base + i + 1:05d}"
        cursor.execute(
            """INSERT INTO facts
               (id, subject, predicate, object, confidence, nature, domain, source,
                date_created, date_modified, version)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (fact_id, fact["subject"], fact["predicate"], fact["object"],
             fact.get("confidence", 0.7), fact.get("nature", "fact"),
             fact.get("domain", ""), fact.get("source", "bootstrap"),
             TODAY, TODAY, 1)
        )
        fact["id"] = fact_id
        inserted += 1

    conn.commit()
    conn.close()
    return {"inserted": inserted, "skipped": skipped}


def update_l1_index(root: str, facts: list, dry_run: bool = False):
    """将事实写入 L1 关键词索引"""
    index_path = Path(root) / "04_memory" / "vector_db" / "keyword_index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
    else:
        index_data = {"version": "1.0.0", "last_updated": "", "entries": []}

    existing_ids = {e.get("fact_id") for e in index_data["entries"]}
    added = 0

    for fact in facts:
        fid = fact.get("id", "")
        if not fid or fid in existing_ids:
            continue
        keywords = list(set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', fact["object"])))[:12]
        index_data["entries"].append({
            "fact_id": fid,
            "keywords": keywords,
            "domain": fact.get("domain", ""),
            "nature": fact.get("nature", "fact"),
            "summary": fact["object"][:120],
            "date": TODAY,
            "source": fact.get("source", "")
        })
        existing_ids.add(fid)
        added += 1

    index_data["last_updated"] = datetime.now().isoformat()

    if not dry_run:
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    return added


def archive_to_l3(root: str, source_name: str, content: str, dry_run: bool = False):
    """归档原文到 L3"""
    raw_dir = Path(root) / "04_memory" / "long_term" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    archive_file = raw_dir / f"bootstrap_{source_name}.md"

    if dry_run:
        print(f"  [DRY-RUN] 将归档到 L3: {archive_file.name}")
        return

    archive_file.write_text(
        f"# L3 Bootstrap 存档 — {source_name}\n> 冷启动时间: {datetime.now().isoformat()}\n\n{content}",
        encoding="utf-8"
    )
    print(f"  [OK] L3 归档: {archive_file.name}")


def main():
    args = parse_args()
    root = os.path.expanduser(args.root)
    dry_run = args.dry_run

    print("=" * 60)
    print("AgentOS 记忆体冷启动（Bootstrap）")
    print(f"时间起点: {TODAY}")
    if dry_run:
        print("[DRY-RUN 模式：仅预览，不写入任何文件]")
    print("=" * 60)

    db_path = ensure_db(root)
    all_facts = []

    # ── 来源 1：MEMORY.md 长期精炼记忆 ─────────────────────────────
    memory_md = WORKBUDDY_MEMORY_DIR / "MEMORY.md"
    if memory_md.exists():
        print(f"\n[来源1] MEMORY.md 长期记忆")
        content = memory_md.read_text(encoding="utf-8")
        facts = parse_memory_md(content)
        print(f"  → 解析出 {len(facts)} 条事实")
        archive_to_l3(root, "MEMORY_md", content, dry_run)
        all_facts.extend(facts)
    else:
        print(f"[WARN] MEMORY.md 不存在: {memory_md}")

    # ── 来源 2：每日工作日志（所有历史日期）──────────────────────────
    print(f"\n[来源2] 工作日志（{WORKBUDDY_MEMORY_DIR}）")
    log_total = 0
    if WORKBUDDY_MEMORY_DIR.exists():
        for log_file in sorted(WORKBUDDY_MEMORY_DIR.glob("????-??-??.md")):
            date_str = log_file.stem
            content = log_file.read_text(encoding="utf-8")
            facts = parse_daily_log(content, date_str)
            print(f"  → {date_str}: {len(facts)} 条")
            archive_to_l3(root, f"daily_{date_str}", content, dry_run)
            all_facts.extend(facts)
            log_total += len(facts)
    print(f"  合计: {log_total} 条")

    # ── 来源 3：WorkBuddy 系统用户画像 ──────────────────────────────
    print(f"\n[来源3] 系统用户画像（{WORKBUDDY_SYSTEM_MEMERY_DIR}）")
    if WORKBUDDY_SYSTEM_MEMERY_DIR.exists():
        for md_file in WORKBUDDY_SYSTEM_MEMERY_DIR.glob("*_memery.md"):
            content = md_file.read_text(encoding="utf-8")
            # 从用户画像提取结构化信息
            facts = []
            # 提取偏好段
            for pattern, pred, conf in [
                (r"用户名\s*([\w]+)，", "username", 0.95),
                (r"常居\s*([^\n。，,]+)", "city", 0.95),
                (r"(偏好.{20,200}?)[\n。]", "preference_summary", 0.85),
                (r"(期望.{20,200}?)[\n。]", "expectation", 0.85),
            ]:
                m = re.search(pattern, content, re.DOTALL)
                if m:
                    facts.append({
                        "subject": "ghai",
                        "predicate": pred,
                        "object": m.group(1).strip()[:300],
                        "confidence": conf,
                        "nature": "fact",
                        "domain": "personal-management",
                        "source": f"system_memery_{md_file.stem}"
                    })
            print(f"  → {md_file.name}: {len(facts)} 条")
            archive_to_l3(root, f"system_{md_file.stem}", content, dry_run)
            all_facts.extend(facts)

    # ── 写入 L2 + L1 ─────────────────────────────────────────────
    print(f"\n[总计] {len(all_facts)} 条候选事实")
    print("\n[写入 L2] 更新 facts.db...")
    stats = insert_facts_to_l2(db_path, all_facts, dry_run)
    print(f"  → 新增 {stats['inserted']} 条，跳过重复 {stats['skipped']} 条")

    print("\n[写入 L1] 更新 keyword_index.json...")
    l1_added = update_l1_index(root, all_facts, dry_run)
    print(f"  → L1 索引新增 {l1_added} 条")

    # ── 输出摘要 ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    if dry_run:
        print("✅ DRY-RUN 完成，未写入任何文件")
    else:
        print("✅ 冷启动完成！记忆系统已建立初始状态")
        print(f"   L1 关键词索引: {Path(root) / '04_memory' / 'vector_db' / 'keyword_index.json'}")
        print(f"   L2 事实库:     {Path(root) / '04_memory' / 'long_term' / 'facts.db'}")
        print(f"   L3 原文存档:   {Path(root) / '04_memory' / 'long_term' / 'raw' / '*.md'}")
        print()
        print("下一步：每日自动提炼已配置，从明天起 daily_digest.py 将自动运行")
    print("=" * 60)


if __name__ == "__main__":
    main()
