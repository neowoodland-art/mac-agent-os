#!/usr/bin/env python3
"""
inbox_refine.py - 知识库收件箱提纯脚本

将 00_inbox/ 中的原始内容按知识属性分类归档到对应目录，
更新知识库首页统计和变更日志。

用法：
    python3 inbox_refine.py --root ~/agent-os [--dry-run] [--date YYYY-MM-DD]
"""

import os
import sys
import json
import re
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# 导入 LLM 分类器
try:
    from llm_classifier import classify_content_enhanced
    LLM_AVAILABLE = True
except ImportError:
    print("⚠️  LLM 分类器不可用，将使用启发式规则")
    LLM_AVAILABLE = False


# ── 配置 ──────────────────────────────────────────

NATURE_TO_DIR = {
    "fact": "30_facts",
    "method": "20_methods",
    "concept": "10_concepts",
    "axiom": "10_concepts",
    "regulation": "30_facts",
    "reference": "40_references",
    "data": "30_facts",
    "opinion": "60_opinions",
    "quote": "60_opinions",
}

SOURCE_TYPE_CONFIDENCE = {
    "official_doc": 0.9,
    "literature": 0.8,
    "experiment": 0.7,
    "personal_exp": 0.5,
    "social_media": 0.3,
    "unknown": 0.4,
}

DIR_CHINESE = {
    "00_inbox": "📥 收件箱",
    "01_daily": "📅 日记",
    "10_concepts": "💡 概念层",
    "20_methods": "🔧 方法层",
    "30_facts": "📋 事实层",
    "40_references": "📎 参考层",
    "50_resources": "🛠 资源层",
    "60_opinions": "💭 观点层",
    "90_archive": "🗄 归档层",
}

TRACKED_DIRS = [
    "00_inbox", "01_daily", "10_concepts", "20_methods",
    "30_facts", "40_references", "50_resources", "60_opinions", "90_archive"
]


# ── 工具函数 ──────────────────────────────────────

def count_md_files(directory: Path) -> int:
    """统计目录下 .md 文件数量"""
    if not directory.exists():
        return 0
    return sum(1 for f in directory.rglob("*.md") if f.is_file())


def latest_modified(directory: Path) -> str:
    """获取目录下最近修改的 .md 文件日期"""
    if not directory.exists():
        return "—"
    md_files = list(directory.rglob("*.md"))
    if not md_files:
        return "—"
    latest = max(f.stat().st_mtime for f in md_files)
    return datetime.fromtimestamp(latest).strftime("%Y-%m-%d")


def generate_id(date_str: str, knowledge_root: Path) -> str:
    """生成唯一知识ID：KB-YYYYMMDD-NNN"""
    prefix = f"KB-{date_str.replace('-', '')}"
    # 扫描已有ID确定序号
    existing = set()
    for md in knowledge_root.rglob("*.md"):
        content = md.read_text(encoding="utf-8", errors="ignore")[:500]
        m = re.search(r'^id:\s*(KB-\d{8}-\d+)', content, re.MULTILINE)
        if m:
            existing.add(m.group(1))
    n = 1
    while f"{prefix}-{n:03d}" in existing:
        n += 1
    return f"{prefix}-{n:03d}"


def parse_frontmatter(text: str) -> dict:
    """解析 YAML frontmatter"""
    if not text.startswith("---"):
        return {}
    match = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def build_frontmatter(kb_id: str, title: str, nature: str, domain: str,
                      confidence: float, source: str, source_type: str,
                      date_str: str, summary: str = "", tags: list = None) -> str:
    """构建知识卡片 frontmatter"""
    if tags is None:
        tags = ["待补充"]
    
    # 确保 domain 是列表格式
    if isinstance(domain, str):
        domain_list = [domain]
    else:
        domain_list = domain if isinstance(domain, list) else ["other"]
    
    # 构建 tags 字符串
    tags_str = ", ".join([f'"{tag}"' for tag in tags])
    
    return f"""---
id: {kb_id}
title: "{title}"
type: {nature if nature in ('concept', 'fact', 'method', 'opinion', 'reference') else 'concept'}
status: published
nature: {nature}
domain: [{", ".join(domain_list)}]
subdomain: []
tags: [{tags_str}]
confidence: {confidence}
source: "{source}"
source_type: {source_type}
date_created: {date_str}
date_modified: {date_str}
version: 1
previous_version: ""
superseded_by: ""
summary: "{summary}"
---"""


# ── 分类逻辑 ──────────────────────────────────────

def classify_content(text: str, fm: dict) -> dict:
    """
    增强版分类函数：优先使用 LLM 智能分类，失败时降级到启发式规则。
    如果 frontmatter 已有 nature/domain，优先使用。
    """
    # 如果 LLM 可用，直接使用增强版分类
    if LLM_AVAILABLE:
        try:
            # 直接使用 LLM 分类，分类器内部会处理降级
            result = classify_content_enhanced(text, fm, use_llm=True)
            # 适配现有结构
            return {
                "nature": result["nature"],
                "domain": result["domain"][0] if result["domain"] else "other",
                "confidence": result["confidence"],
                "source_type": result.get("source_type", "unknown"),
                "source": result.get("source", ""),
                "title": result.get("title", ""),
                "summary": result.get("summary", ""),
                "tags": result.get("tags", [])
            }
        except Exception as e:
            print(f"⚠️  LLM 分类失败，回退到启发式规则: {e}")
    
    # LLM 不可用或失败，使用启发式规则
    result = {
        "nature": "concept",
        "domain": "other",
        "confidence": 0.4,
        "source_type": "unknown",
        "source": "",
        "title": "",
        "summary": "",
        "tags": []
    }

    # 优先使用已有 frontmatter
    if fm.get("nature") and fm["nature"] in NATURE_TO_DIR:
        result["nature"] = fm["nature"]
    if fm.get("domain"):
        result["domain"] = fm["domain"]
    if fm.get("confidence"):
        try:
            result["confidence"] = float(fm["confidence"])
        except ValueError:
            pass
    if fm.get("source"):
        result["source"] = fm["source"]
    if fm.get("source_type"):
        result["source_type"] = fm["source_type"]
    if fm.get("title"):
        result["title"] = fm["title"]

    # 如果没有 nature，用启发式规则
    if not fm.get("nature"):
        lower = text.lower()
        # 方法类关键词
        method_kw = ["步骤", "教程", "如何", "how to", "方法", "指南", "最佳实践", "best practice"]
        fact_kw = ["数据", "统计", "报告", "结果", "事实", "date", "report"]
        opinion_kw = ["认为", "觉得", "观点", "推测", "假设", "opinion", "think"]
        reference_kw = ["论文", "文献", "引用", "参考", "paper", "reference"]

        if any(kw in lower for kw in method_kw):
            result["nature"] = "method"
        elif any(kw in lower for kw in fact_kw):
            result["nature"] = "fact"
        elif any(kw in lower for kw in opinion_kw):
            result["nature"] = "opinion"
        elif any(kw in lower for kw in reference_kw):
            result["nature"] = "reference"

    # confidence from source_type
    if result["source_type"] in SOURCE_TYPE_CONFIDENCE:
        result["confidence"] = SOURCE_TYPE_CONFIDENCE[result["source_type"]]
    
    # 生成简单标题和摘要
    if not result["title"]:
        first_line = text.split('\n')[0].strip('# ')
        if len(first_line) < 50:
            result["title"] = first_line
    
    if not result["summary"]:
        clean_text = re.sub(r'[#*\-`]', '', text)
        result["summary"] = clean_text[:100] + ("..." if len(clean_text) > 100 else "")

    return result


# ── 主流程 ─────────────────────────────────────────

def refine_inbox(root: str, dry_run: bool = False, date_str: str = None):
    """执行收件箱提纯"""
    root = Path(os.path.expanduser(root))
    kb_root = root / "03_knowledge"
    inbox = kb_root / "00_inbox"

    if not inbox.exists():
        print(f"❌ 收件箱不存在: {inbox}")
        return

    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    md_files = sorted(inbox.glob("*.md"))

    if not md_files:
        print(f"📭 收件箱为空，无需提纯 ({date_str})")
        # 仍然更新首页统计
        update_homepage(kb_root)
        return

    print(f"📬 收件箱有 {len(md_files)} 个文件待提纯")

    archived = []
    skipped = []
    errors = []

    for md_file in md_files:
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            fm = parse_frontmatter(text)
            title = fm.get("title", md_file.stem)

            # 分类
            classification = classify_content(text, fm)
            nature = classification["nature"]
            target_dir_name = NATURE_TO_DIR.get(nature, "10_concepts")
            target_dir = kb_root / target_dir_name

            # 去重检查
            is_dup = False
            for existing in target_dir.rglob("*.md"):
                existing_text = existing.read_text(encoding="utf-8", errors="ignore")[:200]
                existing_fm = parse_frontmatter(existing_text)
                if existing_fm.get("title") == title:
                    is_dup = True
                    break

            if is_dup:
                print(f"  ⏭ 重复跳过: {title}")
                skipped.append(title)
                if not dry_run:
                    md_file.unlink()
                continue

            # 生成 ID 和新文件
            kb_id = generate_id(date_str, kb_root)
            domain = classification["domain"]
            confidence = classification["confidence"]
            source = classification["source"]
            source_type = classification["source_type"]

            # 构建新内容
            body = text
            if text.startswith("---"):
                # 去掉旧 frontmatter
                body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, count=1, flags=re.DOTALL)

            new_content = build_frontmatter(
                kb_id, 
                classification.get("title", title), 
                nature, 
                domain, 
                confidence, 
                source, 
                source_type, 
                date_str,
                classification.get("summary", ""),
                classification.get("tags", [])
            ) + "\n\n" + body.strip() + "\n"

            # 确定目标文件名
            safe_title = re.sub(r'[^\w\u4e00-\u9fff-]', '_', title)[:50]
            target_file = target_dir / f"{date_str}_{safe_title}.md"

            if dry_run:
                print(f"  🔍 [DRY] {title} → {target_dir_name}/ ({nature})")
            else:
                target_dir.mkdir(parents=True, exist_ok=True)
                target_file.write_text(new_content, encoding="utf-8")
                md_file.unlink()
                print(f"  ✅ {title} → {target_dir_name}/ ({nature}) [{kb_id}]")

            archived.append({
                "id": kb_id,
                "title": title,
                "nature": nature,
                "dir": target_dir_name,
            })

        except Exception as e:
            print(f"  ❌ 处理失败: {md_file.name} - {e}")
            errors.append(md_file.name)

    # 更新首页
    if not dry_run:
        update_homepage(kb_root)
        update_changelog(kb_root, date_str, archived, skipped)

    print(f"\n📊 提纯完成: 归档 {len(archived)}, 跳过 {len(skipped)}, 失败 {len(errors)}")


def update_homepage(kb_root: Path):
    """更新知识库首页统计"""
    readme = kb_root / "README.md"
    if not readme.exists():
        print("⚠️ 首页 README.md 不存在，跳过统计更新")
        return

    # 计算各目录统计
    stats = {}
    total = 0
    for dirname in TRACKED_DIRS:
        dirpath = kb_root / dirname
        count = count_md_files(dirpath)
        latest = latest_modified(dirpath)
        stats[dirname] = (count, latest)
        total += count

    # 构建统计表格
    table_lines = []
    for dirname in TRACKED_DIRS:
        count, latest = stats[dirname]
        emoji_name = DIR_CHINESE.get(dirname, dirname)
        table_lines.append(f"| {emoji_name} | {count} | {latest} |")
    table_lines.append(f"| **总计** | **{total}** | — |")

    table_text = "\n".join(table_lines)

    # 替换 README 中的统计部分
    content = readme.read_text(encoding="utf-8")
    pattern = r'(\| 📥 收件箱 \|.*?)(\| \*\*总计\*\* \| \*\*\d+\*\* \| — \|)'
    replacement = table_text
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # 更新最后更新日期
    today = datetime.now().strftime("%Y-%m-%d")
    content = re.sub(
        r'\*最后更新：.*? by inbox_refine 技能\*',
        f'*最后更新：{today} by inbox_refine 技能*',
        content
    )

    readme.write_text(content, encoding="utf-8")
    print(f"📄 首页统计已更新 (总计 {total} 个文件)")


def update_changelog(kb_root: Path, date_str: str, archived: list, skipped: list):
    """更新变更日志"""
    changelog = kb_root / "CHANGELOG.md"
    if not changelog.exists():
        initial = "# 知识库变更日志\n"
        changelog.write_text(initial, encoding="utf-8")

    content = changelog.read_text(encoding="utf-8")

    # 构建新条目
    entry = f"\n## {date_str}\n\n"
    if archived:
        entry += "### 归档\n"
        for item in archived:
            entry += f"- [{item['nature']}] {item['title']} → {item['dir']}/ ({item['id']})\n"
    if skipped:
        entry += f"\n### 跳过（重复）\n"
        for title in skipped:
            entry += f"- {title}\n"

    # 在第一个 ## 之前插入（跳过标题行）
    lines = content.split("\n")
    insert_idx = 1
    for i, line in enumerate(lines):
        if line.startswith("## "):
            insert_idx = i
            break

    lines.insert(insert_idx, entry)
    changelog.write_text("\n".join(lines), encoding="utf-8")
    print(f"📝 变更日志已更新")


# ── 入口 ──────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentOS 知识库收件箱提纯")
    parser.add_argument("--root", default="~/agent-os", help="agent-os 根目录")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不实际修改文件")
    parser.add_argument("--date", default=None, help="日期 (YYYY-MM-DD)")
    args = parser.parse_args()

    refine_inbox(args.root, args.dry_run, args.date)
