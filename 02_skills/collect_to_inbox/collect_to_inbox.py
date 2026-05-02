#!/usr/bin/env python3
"""
collect_to_inbox.py —— 扫描知识库各分类目录，提取主要内容生成标准化 MD 放入收件箱

用法：
  python3 collect_to_inbox.py --root ~/workbuddy-agent-os/agent-sync [--dry-run] [--force]

参数：
  --root    agent-os 根目录（默认 ~/workbuddy-agent-os/agent-sync）
  --dry-run 只预览不写入
  --force   忽略 collected 标记，重新收集
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# 扫描的源目录配置：(相对路径, 提取策略)
SCAN_DIRS = [
    ("03_knowledge/50_resources/视频笔记", "extract_summary"),
    ("03_knowledge/50_resources/字幕存档", "extract_head"),
    ("03_knowledge/50_resources/阅读笔记", "extract_summary"),
    ("03_knowledge/50_resources/全文存档", "extract_head"),
    ("03_knowledge/50_resources/翻译存档", "extract_summary"),
    ("03_knowledge/50_resources/灵感素材", "extract_summary"),
    ("03_knowledge/50_resources/语音转写", "extract_key_points"),
    ("03_knowledge/20_methods", "extract_method"),
    ("03_knowledge/01_daily/闪念笔记", "extract_key_points"),
    ("03_knowledge/40_references", "extract_summary"),
]

# 不扫描的目录
SKIP_DIRS = {"00_inbox", "99_system", "90_archive", "10_concepts", "30_facts", "60_opinions", "50_resources/资源索引"}


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 Frontmatter，返回 (metadata_dict, body_text)"""
    if not content.startswith("---"):
        return {}, content
    
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    
    fm_text = content[3:end].strip()
    body = content[end + 3:].strip()
    
    metadata = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val:
                metadata[key] = val
    
    return metadata, body


def extract_summary(body: str, max_chars: int = 500) -> str:
    """提取摘要：取前 max_chars 字符"""
    if len(body) <= max_chars:
        return body
    return body[:max_chars] + "\n\n...（内容已截断，完整内容见源文件）"


def extract_head(body: str, max_chars: int = 500) -> str:
    """提取头部内容"""
    return extract_summary(body, max_chars)


def extract_key_points(body: str, max_chars: int = 500) -> str:
    """提取关键要点：优先提取列表项"""
    lines = body.split("\n")
    points = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("- ", "* ", "1.", "2.", "3.", "4.", "5.")):
            points.append(stripped)
        if len("\n".join(points)) > max_chars:
            break
    
    if points:
        result = "\n".join(points[:20])
        if len(result) > max_chars:
            result = result[:max_chars] + "\n\n...（内容已截断）"
        return result
    
    return extract_summary(body, max_chars)


def extract_method(body: str, max_chars: int = 500) -> str:
    """提取方法论：方法名 + 步骤"""
    lines = body.split("\n")
    # 提取标题和编号列表
    method_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith(("-", "*", "1.", "2.", "3.", "4.", "5.")):
            method_lines.append(stripped)
        if len("\n".join(method_lines)) > max_chars:
            break
    
    if method_lines:
        return "\n".join(method_lines[:30])
    
    return extract_summary(body, max_chars)


EXTRACT_FUNCS = {
    "extract_summary": extract_summary,
    "extract_head": extract_head,
    "extract_key_points": extract_key_points,
    "extract_method": extract_method,
}


def infer_nature(source_dir: str, metadata: dict) -> str:
    """根据源目录和元数据推断 nature"""
    dir_lower = source_dir.lower()
    if "方法" in dir_lower or "method" in dir_lower:
        return "method"
    if "视频笔记" in dir_lower:
        return "resource"
    if "字幕" in dir_lower or "转写" in dir_lower:
        return "reference"
    if "阅读" in dir_lower or "全文" in dir_lower:
        return "reference"
    if "翻译" in dir_lower:
        return "reference"
    if "灵感" in dir_lower:
        return "opinion"
    if "闪念" in dir_lower:
        return "opinion"
    if "references" in dir_lower:
        return "reference"
    # 从 tags 推断
    tags = metadata.get("tags", "")
    if "方法论" in tags or "方法" in tags:
        return "method"
    if "概念" in tags:
        return "concept"
    return "resource"


def infer_domain(metadata: dict) -> str:
    """从标签推断领域"""
    tags = metadata.get("tags", "").lower()
    domain_keywords = {
        "技术": ["编程", "代码", "开发", "tech", "python", "javascript", "ai", "llm", "机器学习"],
        "金融": ["投资", "股票", "基金", "finance", "交易", "财经"],
        "产品": ["产品", "设计", "ux", "product"],
        "效率": ["效率", "工具", "workflow", "自动化"],
        "阅读": ["读书", "阅读", "书评", "book"],
        "生活": ["生活", "旅行", "美食", "健身"],
    }
    for domain, keywords in domain_keywords.items():
        if any(kw in tags for kw in keywords):
            return domain
    return "general"


def collect_to_inbox(root_dir: str, dry_run: bool = False, force: bool = False):
    """主函数：扫描各目录，提取内容到收件箱"""
    root = Path(root_dir).expanduser()
    inbox_dir = root / "03_knowledge" / "00_inbox"
    
    stats = {"scanned": 0, "collected": 0, "skipped_collected": 0, "skipped_duplicate": 0, "errors": 0}
    
    # 确保收件箱存在
    if not dry_run:
        inbox_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取收件箱已有文件名集合（用于去重）
    existing_inbox = set()
    if inbox_dir.exists():
        for f in inbox_dir.glob("*.md"):
            existing_inbox.add(f.name)
    
    collected_date = datetime.now().strftime("%Y-%m-%d")
    
    for rel_dir, extract_strategy in SCAN_DIRS:
        scan_dir = root / rel_dir
        if not scan_dir.exists():
            continue
        
        # 递归扫描子目录（灵感素材下有平台子目录）
        for md_file in sorted(scan_dir.rglob("*.md")):
            stats["scanned"] += 1
            
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception as e:
                print(f"  ❌ 读取失败: {md_file.name} - {e}")
                stats["errors"] += 1
                continue
            
            metadata, body = parse_frontmatter(content)
            
            # 检查是否已收集
            if not force and metadata.get("collected") == "true":
                stats["skipped_collected"] += 1
                continue
            
            # 去重检查
            dest_name = md_file.name
            if dest_name in existing_inbox:
                stats["skipped_duplicate"] += 1
                continue
            
            # 提取内容
            extract_func = EXTRACT_FUNCS.get(extract_strategy, extract_summary)
            extracted = extract_func(body)
            
            # 推断属性
            nature = infer_nature(rel_dir, metadata)
            domain = infer_domain(metadata)
            title = metadata.get("title", md_file.stem)
            source_date = metadata.get("date", collected_date)
            tags = metadata.get("tags", "")
            source_rel = str(md_file.relative_to(root))
            
            # 生成收件箱文件内容
            inbox_content = f"""---
title: "{title}"
source_dir: {rel_dir}
source_file: {md_file.name}
date: {source_date}
collected_date: {collected_date}
tags: {tags}
nature: {nature}
domain: {domain}
status: inbox
---

# {title}

> 来源：{rel_dir}

{extracted}
"""
            
            if dry_run:
                print(f"  📥 [预览] {md_file.name} → 00_inbox/{dest_name}")
                print(f"     nature={nature}, domain={domain}, 策略={extract_strategy}")
            else:
                # 写入收件箱
                dest_path = inbox_dir / dest_name
                dest_path.write_text(inbox_content, encoding="utf-8")
                print(f"  📥 {md_file.name} → 00_inbox/{dest_name}")
                
                # 标记原文件为已收集
                if content.startswith("---"):
                    # 在 Frontmatter 末尾添加 collected 标记
                    end = content.find("---", 3)
                    if end != -1:
                        fm = content[3:end]
                        if "collected:" not in fm:
                            fm += f"\ncollected: true\ncollected_date: {collected_date}"
                            new_content = "---" + fm + content[end:]
                            md_file.write_text(new_content, encoding="utf-8")
                else:
                    # 没有 Frontmatter，添加一个简单的
                    new_content = f"---\ncollected: true\ncollected_date: {collected_date}\n---\n\n{content}"
                    md_file.write_text(new_content, encoding="utf-8")
                
                existing_inbox.add(dest_name)
            
            stats["collected"] += 1
    
    # 输出统计
    print(f"\n{'[预览] ' if dry_run else ''}收集统计：")
    print(f"  扫描文件：{stats['scanned']}")
    print(f"  提取到收件箱：{stats['collected']}")
    print(f"  跳过（已收集）：{stats['skipped_collected']}")
    print(f"  跳过（重复）：{stats['skipped_duplicate']}")
    print(f"  错误：{stats['errors']}")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="收集各分类目录内容到收件箱")
    parser.add_argument("--root", default="~/workbuddy-agent-os/agent-sync", help="agent-os 根目录")
    parser.add_argument("--dry-run", action="store_true", help="只预览不写入")
    parser.add_argument("--force", action="store_true", help="忽略 collected 标记，重新收集")
    args = parser.parse_args()
    
    print(f"=== Collect to Inbox ===")
    print(f"根目录：{args.root}")
    print(f"模式：{'预览' if args.dry_run else '执行'}")
    print()
    
    collect_to_inbox(args.root, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
