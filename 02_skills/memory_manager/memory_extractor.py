#!/usr/bin/env python3
"""
memory_extractor.py — 记忆固化提取器

从本机 L2 事实库（facts.db）和每日摘要中，检测满足固化条件的记忆，
生成标准 MD 知识卡并推送到协同收件箱 inbox/memory/。

固化条件（满足任意一条即触发）：
  1. 用户主动标记 --solidify <fact_id>
  2. 高频引用：同一主谓对（subject+predicate）在 N 天内出现 >= threshold 次
  3. 高置信度：confidence >= 0.85 且 version >= 2（被多次确认未被推翻）

使用：
  python3 memory_extractor.py --root ~/workbuddy-agent-os/agent-sync --local ~/workbuddy-agent-os/agent-local
  python3 memory_extractor.py --root ~/workbuddy-agent-os/agent-sync --local ~/workbuddy-agent-os/agent-local --solidify FACT-2026-0001
  python3 memory_extractor.py --root ~/workbuddy-agent-os/agent-sync --local ~/workbuddy-agent-os/agent-local --dry-run
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path


# ─── 固化阈值配置 ─────────────────────────────────────────────────
DEFAULT_FREQ_DAYS = 7        # 高频检测窗口（天）
DEFAULT_FREQ_THRESHOLD = 3   # 窗口内出现次数阈值
DEFAULT_CONFIDENCE_MIN = 0.85  # 高置信度阈值
DEFAULT_VERSION_MIN = 2        # 最小版本数（被多次确认）


def parse_args():
    parser = argparse.ArgumentParser(description="AgentOS 记忆固化提取器")
    parser.add_argument("--root", default="~/workbuddy-agent-os/agent-sync", help="agent-os 根目录")
    parser.add_argument("--local", default="~/workbuddy-agent-os/agent-local", help="~/workbuddy-agent-os/agent-local")
    parser.add_argument("--solidify", default=None, help="强制固化指定 fact_id")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写文件")
    parser.add_argument("--freq-days", type=int, default=DEFAULT_FREQ_DAYS)
    parser.add_argument("--freq-threshold", type=int, default=DEFAULT_FREQ_THRESHOLD)
    parser.add_argument("--confidence-min", type=float, default=DEFAULT_CONFIDENCE_MIN)
    parser.add_argument("--version-min", type=int, default=DEFAULT_VERSION_MIN)
    return parser.parse_args()


def open_facts_db(local_root: Path):
    """打开本机 L2 事实库"""
    # L2 事实库路径（daily_digest.py 写入的路径）
    db_path = local_root / "memory" / "raw" / "04_memory" / "long_term" / "facts.db"
    if not db_path.exists():
        print(f"[WARN] 事实库不存在: {db_path}")
        return None, None
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor()


def detect_high_frequency(cursor, days: int, threshold: int) -> list:
    """
    检测高频引用事实：
    在近 N 天内，subject+predicate 组合出现 >= threshold 次的最新事实
    """
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT subject, predicate, COUNT(*) as cnt,
               MAX(confidence) as max_conf,
               MAX(date_modified) as latest_date
        FROM facts
        WHERE date_created >= ? AND superseded_by = ''
        GROUP BY subject, predicate
        HAVING cnt >= ?
        ORDER BY cnt DESC
    """, (since, threshold))
    groups = cursor.fetchall()

    results = []
    for row in groups:
        # 取该组最新/最高置信度的事实记录
        cursor.execute("""
            SELECT * FROM facts
            WHERE subject = ? AND predicate = ? AND superseded_by = ''
            ORDER BY confidence DESC, version DESC
            LIMIT 1
        """, (row["subject"], row["predicate"]))
        fact = cursor.fetchone()
        if fact:
            results.append(dict(fact) | {"solidify_reason": f"高频引用（{row['cnt']}次/{days}天）"})
    return results


def detect_high_confidence(cursor, conf_min: float, version_min: int) -> list:
    """检测高置信度且多次确认的事实"""
    cursor.execute("""
        SELECT * FROM facts
        WHERE confidence >= ? AND version >= ? AND superseded_by = ''
        ORDER BY confidence DESC, version DESC
    """, (conf_min, version_min))
    rows = cursor.fetchall()
    return [dict(r) | {"solidify_reason": f"高置信度({r['confidence']:.2f})·已确认{r['version']}次"} for r in rows]


def get_fact_by_id(cursor, fact_id: str) -> dict:
    """按ID获取指定事实"""
    cursor.execute("SELECT * FROM facts WHERE id = ?", (fact_id,))
    row = cursor.fetchone()
    return dict(row) | {"solidify_reason": "用户主动固化"} if row else None


def already_solidified(inbox_memory_dir: Path, fact_id: str) -> bool:
    """检查该事实是否已被推送到inbox（避免重复）"""
    for md in inbox_memory_dir.glob("*.md"):
        content = md.read_text(encoding="utf-8", errors="ignore")[:500]
        if fact_id in content:
            return True
    return False


def generate_memory_card(fact: dict, today: str) -> tuple[str, str]:
    """
    生成记忆固化知识卡 MD 内容

    返回: (filename, content)
    """
    fact_id = fact.get("id", "")
    subject = fact.get("subject", "unknown")
    predicate = fact.get("predicate", "")
    obj = fact.get("object", "")
    domain = fact.get("domain", "personal-management")
    nature = fact.get("nature", "fact")
    confidence = fact.get("confidence", 0.7)
    source = fact.get("source", "memory_system")
    reason = fact.get("solidify_reason", "")
    version = fact.get("version", 1)
    date_created = fact.get("date_created", today)

    # 生成知识卡 ID（MEM前缀区别于KB）
    mem_id = f"MEM-{today.replace('-', '')}-{fact_id[-4:] if len(fact_id) >= 4 else '0001'}"

    # 标题：用 predicate + 前40字
    title = f"{predicate}: {obj[:40]}{'...' if len(obj) > 40 else ''}"

    frontmatter = f"""---
id: {mem_id}
source_fact_id: {fact_id}
title: "{title}"
nature: {nature}
domain: [{domain}]
confidence: {confidence}
source: "{source}"
source_type: memory_solidification
solidify_reason: "{reason}"
subject: "{subject}"
predicate: "{predicate}"
version: {version}
date_created: {date_created}
date_solidified: {today}
status: draft
track: memory
---"""

    body = f"""# {title}

**来源**：本机记忆系统（自动固化）  
**固化原因**：{reason}  
**主体**：{subject}  
**谓语**：{predicate}  
**置信度**：{confidence:.2f}  
**原始事实ID**：`{fact_id}`

---

## 内容

{obj}

---

> *本卡片由 memory_extractor.py 自动生成，请主机审核后归档入知识库。*
"""

    safe_pred = re.sub(r'[^\w\u4e00-\u9fff-]', '_', predicate)[:20]
    filename = f"MEM-{today.replace('-', '')}-{safe_pred}-{fact_id[-6:]}.md"

    return filename, frontmatter + "\n" + body


def write_to_inbox(inbox_memory_dir: Path, filename: str, content: str, dry_run: bool) -> Path:
    """写入协同 inbox/memory/ 分区"""
    inbox_memory_dir.mkdir(parents=True, exist_ok=True)
    target = inbox_memory_dir / filename
    if not dry_run:
        target.write_text(content, encoding="utf-8")
    return target


def mark_solidified(cursor, conn, fact_id: str, dry_run: bool):
    """在 facts.db 中标记该事实已固化（用 superseded_by 记录固化标记）"""
    if dry_run:
        return
    cursor.execute(
        "UPDATE facts SET superseded_by = ? WHERE id = ?",
        (f"SOLIDIFIED:{datetime.now().strftime('%Y-%m-%d')}", fact_id)
    )
    conn.commit()


def write_log(root: Path, log_entries: list):
    """记录固化日志"""
    log_dir = root / "04_memory" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "memory_solidification.log"
    with open(log_file, "a", encoding="utf-8") as f:
        for entry in log_entries:
            f.write(f"{entry}\n")


def main():
    args = parse_args()
    root = Path(args.root).expanduser()
    local_root = Path(args.local).expanduser()
    today = datetime.now().strftime("%Y-%m-%d")

    # 协同 inbox/memory/ 路径
    inbox_memory_dir = root / "03_knowledge" / "00_stream" / "inbox" / "memory"

    print("=" * 60)
    print("AgentOS 记忆固化提取器")
    print(f"  root:  {root}")
    print(f"  local: {local_root}")
    print(f"  inbox: {inbox_memory_dir}")
    if args.dry_run:
        print("  [DRY-RUN 模式，不写入文件]")
    print("=" * 60)

    conn, cursor = open_facts_db(local_root)
    if conn is None:
        print("[ERROR] 无法打开事实库，退出")
        sys.exit(1)

    # ── 收集待固化事实 ────────────────────────────────────────────
    candidates = []
    seen_ids = set()

    if args.solidify:
        # 模式1：用户主动指定
        fact = get_fact_by_id(cursor, args.solidify)
        if fact:
            candidates.append(fact)
            seen_ids.add(fact["id"])
            print(f"[INFO] 用户指定固化: {args.solidify}")
        else:
            print(f"[ERROR] 未找到事实: {args.solidify}")
            conn.close()
            sys.exit(1)
    else:
        # 模式2：高频检测
        freq_facts = detect_high_frequency(cursor, args.freq_days, args.freq_threshold)
        for f in freq_facts:
            if f["id"] not in seen_ids:
                candidates.append(f)
                seen_ids.add(f["id"])

        # 模式3：高置信度检测
        conf_facts = detect_high_confidence(cursor, args.confidence_min, args.version_min)
        for f in conf_facts:
            if f["id"] not in seen_ids:
                candidates.append(f)
                seen_ids.add(f["id"])

        print(f"[INFO] 检测到 {len(candidates)} 条候选固化事实")

    if not candidates:
        print("[INFO] 无需固化，退出")
        conn.close()
        return

    # ── 过滤已固化 ────────────────────────────────────────────────
    new_candidates = []
    for fact in candidates:
        if already_solidified(inbox_memory_dir, fact["id"]):
            print(f"  ⏭ 已固化跳过: {fact['id']}")
        else:
            new_candidates.append(fact)

    print(f"[INFO] 新增固化: {len(new_candidates)} 条")

    if not new_candidates:
        conn.close()
        return

    # ── 生成并写入知识卡 ──────────────────────────────────────────
    log_entries = []
    pushed = 0

    for fact in new_candidates:
        filename, content = generate_memory_card(fact, today)
        target = write_to_inbox(inbox_memory_dir, filename, content, args.dry_run)

        action = "[DRY-RUN]" if args.dry_run else "[写入]"
        print(f"  {action} {filename}")
        print(f"        原因: {fact['solidify_reason']}")

        # 标记已固化（仅非dry-run）
        mark_solidified(cursor, conn, fact["id"], args.dry_run)

        log_entries.append(
            f"{datetime.now().isoformat()} | {fact['id']} | {fact['solidify_reason']} | {filename}"
        )
        pushed += 1

    # ── 记录日志 ──────────────────────────────────────────────────
    if not args.dry_run and log_entries:
        write_log(root, log_entries)

    conn.close()

    print(f"\n[完成] 固化推送 {pushed} 条 → {inbox_memory_dir}")
    print("  主维护机可通过 inbox_refine.py 将这些内容归档入知识库。")


if __name__ == "__main__":
    main()
