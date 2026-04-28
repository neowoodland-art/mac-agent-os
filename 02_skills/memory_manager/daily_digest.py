#!/usr/bin/env python3
"""
AgentOS 每日对话提炼脚本
用途：从对话记录中提取关键事实，更新 L1 索引、L2 摘要库、L3 原文存档

数据源优先级（按顺序逐一尝试，全部合并）：
  1. WorkBuddy Claw 工作记忆日志    → ~/WorkBuddy/Claw/.workbuddy/memory/YYYY-MM-DD.md
  2. WorkBuddy 系统用户画像         → ~/.workbuddy/memery/*.md
  3. agent-os 每日摘要              → ~/agent-os/04_memory/daily_summaries/YYYY-MM-DD.md

使用：
  python3 daily_digest.py --root ~/agent-os --date 2026-04-25
  python3 daily_digest.py --root ~/agent-os          # 默认处理昨天
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path


# ─── 数据源路径配置 ──────────────────────────────────────────────
# 如果工作记忆路径变更，只改这里即可
WORKBUDDY_MEMORY_DIR = Path.home() / "WorkBuddy" / "Claw" / ".workbuddy" / "memory"
WORKBUDDY_SYSTEM_MEMERY_DIR = Path.home() / ".workbuddy" / "memery"


def parse_args():
    parser = argparse.ArgumentParser(description="AgentOS 每日对话提炼")
    parser.add_argument("--root", required=True, help="agent-os 根目录路径")
    parser.add_argument("--date", default=None, help="日期 (YYYY-MM-DD)，默认昨天")
    parser.add_argument("--bootstrap", action="store_true",
                        help="冷启动模式：处理所有可用日期，用于首次初始化")
    return parser.parse_args()


def load_conversations(root: str, target_date: str) -> list:
    """
    从以下来源加载对话内容（全部合并）：
      1. WorkBuddy Claw 工作记忆日志（每次工作后由 AI 写入）
      2. WorkBuddy 系统用户画像文件
      3. agent-os/04_memory/daily_summaries/（上一轮提炼结果，避免信息丢失）
    """
    conversations = []

    # ── 来源 1：Claw 工作记忆日志（最核心的数据源）──────────────────
    claw_daily = WORKBUDDY_MEMORY_DIR / f"{target_date}.md"
    if claw_daily.exists():
        content = claw_daily.read_text(encoding="utf-8")
        if content.strip():
            conversations.append({
                "source": str(claw_daily),
                "source_type": "claw_daily_log",
                "date": target_date,
                "content": content
            })
            print(f"  [+] 来源1 Claw工作日志: {claw_daily} ({len(content)} 字符)")
    else:
        print(f"  [-] 来源1 Claw工作日志不存在: {claw_daily}")

    # ── 来源 2：WorkBuddy 系统用户画像 ──────────────────────────────
    if WORKBUDDY_SYSTEM_MEMERY_DIR.exists():
        for md_file in WORKBUDDY_SYSTEM_MEMERY_DIR.glob("*_memery.md"):
            content = md_file.read_text(encoding="utf-8")
            # 检查文件中是否包含目标日期（粗过滤）
            if target_date in content or "Last updated" in content:
                conversations.append({
                    "source": str(md_file),
                    "source_type": "workbuddy_system_memery",
                    "date": target_date,
                    "content": content
                })
                print(f"  [+] 来源2 系统用户画像: {md_file.name} ({len(content)} 字符)")

    # ── 来源 3：上一轮 agent-os 摘要（防丢失）──────────────────────
    daily_dir = Path(root) / "04_memory" / "daily_summaries"
    prev_summary = daily_dir / f"{target_date}.md"
    if prev_summary.exists():
        content = prev_summary.read_text(encoding="utf-8")
        if content.strip():
            conversations.append({
                "source": str(prev_summary),
                "source_type": "agent_os_summary",
                "date": target_date,
                "content": content
            })
            print(f"  [+] 来源3 上轮摘要: {prev_summary.name} ({len(content)} 字符)")

    return conversations


def load_all_available_dates(root: str) -> list:
    """冷启动模式：扫描所有可用日期（用于首次运行）"""
    dates = set()

    # 扫描 Claw 工作记忆日志
    if WORKBUDDY_MEMORY_DIR.exists():
        for f in WORKBUDDY_MEMORY_DIR.glob("????-??-??.md"):
            dates.add(f.stem)

    # 扫描 agent-os daily_summaries
    daily_dir = Path(root) / "04_memory" / "daily_summaries"
    if daily_dir.exists():
        for f in daily_dir.glob("????-??-??.md"):
            dates.add(f.stem)

    return sorted(dates)


def extract_facts(content: str, date: str, source_type: str = "unknown") -> list:
    """
    从对话内容中提取关键事实。

    提取策略：
    - Claw工作日志（claw_daily_log）：按 ## 章节和 ### 子项提取结构化决策
    - 系统用户画像（workbuddy_system_memery）：提取用户基本信息和偏好
    - 通用：包含决策/配置/部署等关键词的行
    """
    facts = []

    if source_type == "workbuddy_system_memery":
        # 用户画像：提取姓名、城市、偏好等结构化信息
        patterns = [
            (r"\*\*Name\*\*[：:]\s*(.+)", "user_profile", "name"),
            (r"\*\*City\*\*[：:]\s*(.+)", "user_profile", "city"),
            (r"用户名\s*(.+?)，", "user_profile", "username"),
            (r"常居\s*(.+?)。", "user_profile", "city"),
        ]
        for pattern, subject, predicate in patterns:
            m = re.search(pattern, content)
            if m:
                facts.append({
                    "subject": subject,
                    "predicate": predicate,
                    "object": m.group(1).strip()[:200],
                    "confidence": 0.9,
                    "nature": "fact",
                    "domain": "personal-management",
                    "date_created": date,
                    "date_modified": date,
                    "version": 1,
                    "source": source_type
                })

        # 提取偏好段落整体
        pref_match = re.search(r"(偏好.{10,200})", content, re.DOTALL)
        if pref_match:
            facts.append({
                "subject": "user",
                "predicate": "preference",
                "object": pref_match.group(1).strip()[:300],
                "confidence": 0.85,
                "nature": "opinion",
                "domain": "personal-management",
                "date_created": date,
                "date_modified": date,
                "version": 1,
                "source": source_type
            })
        return facts

    # ── 通用提取：决策/配置/完成事项 ────────────────────────────────
    lines = content.split("\n")
    current_section = ""

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # 记录当前章节标题（用于 domain 推断）
        if line_stripped.startswith("## ") or line_stripped.startswith("### "):
            current_section = line_stripped.lstrip("#").strip()
            continue

        # 决策性关键词
        decision_keywords = [
            "决定", "确认", "选择", "修改", "配置", "部署", "安装", "更新",
            "修复", "完成", "创建", "初始化", "验证", "生成", "已部署", "已完成",
            "设计决策", "关键决策"
        ]

        for kw in decision_keywords:
            if kw in line_stripped and len(line_stripped) > 10:
                # 推断领域
                domain = "personal-management"
                if any(w in current_section for w in ["代码", "脚本", "技能", "工具", "初始化", "部署"]):
                    domain = "engineering"
                elif any(w in current_section for w in ["知识", "记忆", "学习"]):
                    domain = "personal-management"

                facts.append({
                    "subject": "ghai",
                    "predicate": kw,
                    "object": (f"[{current_section}] " if current_section else "") + line_stripped[:250],
                    "confidence": 0.75,
                    "nature": "fact",
                    "domain": domain,
                    "date_created": date,
                    "date_modified": date,
                    "version": 1,
                    "source": source_type
                })
                break  # 一行只取一次

    return facts


def check_duplicate(fact: dict, cursor) -> bool:
    """检查事实是否已存在（去重）"""
    cursor.execute(
        "SELECT id FROM facts WHERE subject = ? AND predicate = ? AND object = ?",
        (fact["subject"], fact["predicate"], fact["object"])
    )
    return cursor.fetchone() is not None


def check_conflict(fact: dict, cursor):
    """检查是否存在内容不同但主谓相同的旧事实（冲突）"""
    cursor.execute(
        "SELECT id, object, confidence FROM facts WHERE subject = ? AND predicate = ? AND object != ?",
        (fact["subject"], fact["predicate"], fact["object"])
    )
    return cursor.fetchone()


def generate_fact_id(date: str, index: int) -> str:
    return f"FACT-{date}-{index:04d}"


def update_l1_index(root: str, facts: list):
    """更新 L1 关键词索引"""
    index_path = Path(root) / "04_memory" / "vector_db" / "keyword_index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
    else:
        index_data = {"version": "1.0.0", "last_updated": "", "entries": []}

    # 避免重复插入：已有 fact_id 的不重复加
    existing_ids = {e.get("fact_id") for e in index_data["entries"]}

    for fact in facts:
        fid = fact.get("id", "")
        if fid in existing_ids:
            continue
        keywords = list(set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', fact["object"])))[:12]
        entry = {
            "fact_id": fid,
            "keywords": keywords,
            "domain": fact.get("domain", ""),
            "nature": fact.get("nature", "fact"),
            "summary": fact["object"][:120],
            "date": fact.get("date_created", ""),
            "source": fact.get("source", "")
        }
        index_data["entries"].append(entry)
        existing_ids.add(fid)

    index_data["last_updated"] = datetime.now().isoformat()

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)


def update_l2_facts(root: str, facts: list, date: str):
    """更新 L2 事实库（SQLite）"""
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

    # 获取当日已有多少条，生成连续 ID
    cursor.execute("SELECT COUNT(*) FROM facts WHERE date_created = ?", (date,))
    existing_count = cursor.fetchone()[0]

    conflicts = []
    duplicates = 0
    inserted = 0

    for i, fact in enumerate(facts):
        fact_id = generate_fact_id(date, existing_count + i + 1)
        fact["id"] = fact_id

        if check_duplicate(fact, cursor):
            duplicates += 1
            fact["_skipped"] = True
            continue

        conflict = check_conflict(fact, cursor)
        if conflict:
            existing_id, existing_obj, existing_conf = conflict
            if fact["confidence"] > existing_conf:
                # 新事实置信度更高 → 覆盖，保留旧值到 previous_version
                cursor.execute(
                    """UPDATE facts SET object=?, confidence=?, date_modified=?,
                       previous_version=?, version=version+1 WHERE id=?""",
                    (fact["object"], fact["confidence"], date, existing_obj, existing_id)
                )
                conflicts.append({"action": "override", "fact_id": existing_id,
                                   "reason": f"新事实置信度更高({fact['confidence']} > {existing_conf})"})
            else:
                conflicts.append({"action": "skip", "fact_id": fact_id,
                                   "reason": f"旧事实置信度更高({existing_conf} >= {fact['confidence']})，需用户确认"})
            duplicates += 1
            fact["_skipped"] = True
            continue

        cursor.execute(
            """INSERT INTO facts
               (id, subject, predicate, object, confidence, nature, domain, source,
                date_created, date_modified, version)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (fact_id, fact["subject"], fact["predicate"], fact["object"],
             fact.get("confidence", 0.7), fact.get("nature", "fact"),
             fact.get("domain", ""), fact.get("source", ""),
             fact.get("date_created", date), fact.get("date_modified", date),
             fact.get("version", 1))
        )
        inserted += 1

    conn.commit()
    conn.close()
    return {"inserted": inserted, "duplicates": duplicates, "conflicts": conflicts}


def archive_to_l3(root: str, date: str, conversations: list):
    """将原始对话内容压缩归档到 L3"""
    raw_dir = Path(root) / "04_memory" / "long_term" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    archive_file = raw_dir / f"{date}.md"

    if archive_file.exists():
        # 追加模式，不覆盖历史
        return

    content = f"# L3 原文存档 — {date}\n\n"
    for conv in conversations:
        content += f"## 来源：{conv['source_type']} | {conv['source']}\n\n"
        content += conv["content"]
        content += "\n\n---\n\n"

    archive_file.write_text(content, encoding="utf-8")
    print(f"  [OK] L3 原文已归档: {archive_file}")


def save_daily_summary(root: str, date: str, facts: list, stats: dict):
    """保存每日提炼摘要"""
    summary_dir = Path(root) / "04_memory" / "daily_summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_file = summary_dir / f"{date}.md"

    content = f"# {date} 记忆提炼摘要\n\n"
    content += f"> 提炼时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    content += f"## 统计\n"
    content += f"- 新增事实: {stats['inserted']}\n"
    content += f"- 重复跳过: {stats['duplicates']}\n"
    content += f"- 冲突处理: {len(stats['conflicts'])}\n\n"

    if facts:
        content += "## 提取的事实\n\n"
        for fact in facts:
            marker = "📌" if fact.get("nature") == "fact" else "💭"
            content += f"- {marker} **[{fact.get('domain', '?')}]** `{fact.get('predicate')}` → {fact['object'][:120]}\n"

    if stats["conflicts"]:
        content += "\n## 冲突记录\n\n"
        for c in stats["conflicts"]:
            content += f"- `{c['fact_id']}`: **{c['action']}** — {c['reason']}\n"

    summary_file.write_text(content, encoding="utf-8")
    print(f"  [OK] 每日摘要已保存: 04_memory/daily_summaries/{date}.md")


def write_conflict_log(root: str, conflicts: list, date: str):
    """写入冲突日志"""
    if not conflicts:
        return
    log_dir = Path(root) / "04_memory" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "conflicts.log"
    with open(log_file, "a", encoding="utf-8") as f:
        for c in conflicts:
            f.write(f"{datetime.now().isoformat()} | {date} | {c['fact_id']} | {c['action']} | {c['reason']}\n")


def process_date(root: str, target_date: str):
    """处理单个日期的完整流程"""
    print(f"\n{'='*55}")
    print(f"处理日期: {target_date}")
    print(f"{'='*55}")

    # 1. 加载对话
    print("[步骤1] 加载对话数据源...")
    conversations = load_conversations(root, target_date)

    if not conversations:
        print(f"  [WARN] {target_date} 无可用数据源，跳过")
        return

    # 2. 提取事实
    print(f"[步骤2] 提取关键事实...")
    all_facts = []
    for conv in conversations:
        facts = extract_facts(conv["content"], target_date, conv["source_type"])
        all_facts.extend(facts)
        print(f"  → 从 {conv['source_type']} 提取 {len(facts)} 条候选事实")

    if not all_facts:
        print(f"  [INFO] {target_date} 无新事实可提取")
        return

    print(f"  [INFO] 共 {len(all_facts)} 条候选事实")

    # 3. 更新 L2 事实库
    print("[步骤3] 更新 L2 事实库...")
    stats = update_l2_facts(root, all_facts, target_date)
    print(f"  [OK] 新增 {stats['inserted']} 条，重复 {stats['duplicates']} 条，冲突 {len(stats['conflicts'])} 条")

    # 4. 更新 L1 关键词索引（仅更新实际写入 L2 的事实，避免孤儿索引）
    print("[步骤4] 更新 L1 关键词索引...")
    inserted_facts = [f for f in all_facts if f.get("id") and not f.get("_skipped")]
    update_l1_index(root, inserted_facts)
    print(f"  [OK] L1 索引已更新 ({len(inserted_facts)} 条)")

    # 4.5 更新向量库（为新事实生成 embedding 写入 ChromaDB）
    if inserted_facts:
        try:
            print("[步骤4.5] 更新向量库...")
            # 动态导入同目录的 semantic_search 模块
            skill_dir = Path(__file__).parent
            if str(skill_dir) not in sys.path:
                sys.path.insert(0, str(skill_dir))
            from semantic_search import VectorStore
            vector_dir = str(Path(root) / "04_memory" / "vector_db" / "chroma")
            vs = VectorStore(vector_dir)
            items = []
            for f in inserted_facts:
                text = f"{f['subject']} {f['predicate']} {f['object']}"
                items.append({
                    "fact_id": f["id"],
                    "text": text,
                    "metadata": {
                        "summary": f["object"][:120],
                        "domain": f.get("domain", ""),
                        "nature": f.get("nature", "fact"),
                        "source": f.get("source", ""),
                        "date_created": f.get("date_created", target_date),
                        "confidence": f.get("confidence", 0.7)
                    }
                })
            vs.upsert_batch(items)
            print(f"  [OK] 向量库已更新 ({len(items)} 条)")
        except Exception as e:
            print(f"  [WARN] 向量库更新失败（不阻塞主流程）: {e}")

    # 5. 归档原文到 L3
    print("[步骤5] 归档原文到 L3...")
    archive_to_l3(root, target_date, conversations)

    # 6. 保存摘要
    print("[步骤6] 保存每日摘要...")
    save_daily_summary(root, target_date, all_facts, stats)

    # 7. 记录冲突
    print("[步骤7] 记录冲突...")
    write_conflict_log(root, stats["conflicts"], target_date)
    if stats["conflicts"]:
        print(f"  [WARN] {len(stats['conflicts'])} 条冲突已记录到 conflicts.log")

    return stats


def main():
    args = parse_args()
    root = os.path.expanduser(args.root)

    if args.bootstrap:
        # 冷启动模式：处理所有历史日期
        print("=" * 55)
        print("AgentOS 记忆体冷启动（处理所有历史记忆）")
        print("=" * 55)
        dates = load_all_available_dates(root)
        if not dates:
            print("[WARN] 未找到任何历史记忆文件")
            return
        print(f"发现 {len(dates)} 个日期: {', '.join(dates)}")
        for d in dates:
            process_date(root, d)
        print("\n[OK] 冷启动完成！")
    else:
        # 普通模式：处理指定日期（默认昨天）
        if args.date:
            target_date = args.date
        else:
            target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        process_date(root, target_date)


if __name__ == "__main__":
    main()
