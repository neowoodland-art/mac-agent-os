#!/usr/bin/env python3
"""
AgentOS 知识入库脚本
用途：将网页内容或纯文本清洗、分类、生成知识卡片并写入 Obsidian 知识库
使用：python3 kb_ingest.py --root ~/workbuddy-agent-os/agent-sync --url https://example.com
     python3 kb_ingest.py --root ~/workbuddy-agent-os/agent-sync --file input.md
     python3 kb_ingest.py --root ~/workbuddy-agent-os/agent-sync --text "原始文本内容"
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path


# 预定义领域列表
DOMAINS = [
    "计算机科学", "人工智能", "金融", "法律", "医学", "物理", "数学",
    "心理学", "哲学", "历史", "工程", "设计", "商业", "个人管理",
    "个人洞见", "其他"
]

# 知识属性类型
NATURE_TYPES = ["fact", "opinion", "method", "regulation", "reference", "data", "quote", "axiom"]

# nature → 目录映射
NATURE_DIR_MAP = {
    "concept": "10_concepts",
    "method": "20_methods",
    "fact": "30_facts",
    "reference": "40_references/docs",
    "resource": "50_resources",
    "opinion": "60_opinions",
    "data": "30_facts",
    "regulation": "30_facts",
    "quote": "60_opinions",
    "axiom": "10_concepts",
}

# 领域英文 → 中文映射
DOMAIN_DIR_MAP = {
    "计算机科学": "cs",
    "人工智能": "ai",
    "金融": "finance",
    "法律": "law",
    "医学": "medicine",
    "物理": "physics",
    "数学": "math",
    "心理学": "psychology",
    "哲学": "philosophy",
    "历史": "history",
    "工程": "engineering",
    "设计": "design",
    "商业": "business",
    "个人管理": "personal-management",
    "个人洞见": "personal-insight",
    "其他": "other",
}


def parse_args():
    parser = argparse.ArgumentParser(description="AgentOS 知识入库")
    parser.add_argument("--root", required=True, help="agent-os 根目录路径")
    parser.add_argument("--url", default=None, help="网页 URL")
    parser.add_argument("--file", default=None, help="输入文件路径")
    parser.add_argument("--text", default=None, help="直接输入文本")
    parser.add_argument("--title", default=None, help="知识标题")
    parser.add_argument("--domain", default=None, help="领域（逗号分隔）")
    parser.add_argument("--nature", default=None, help="知识属性")
    parser.add_argument("--tags", default=None, help="标签（逗号分隔）")
    parser.add_argument("--inbox", action="store_true", help="仅放入收件箱，不分类")
    return parser.parse_args()


def fetch_url_content(url: str) -> str:
    """抓取网页内容"""
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            content = trafilatura.extract(downloaded)
            return content or ""
    except ImportError:
        pass

    # fallback: 用 urllib
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    # 简单提取正文（去除 HTML 标签）
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:10000]  # 限制长度


def classify_content(content: str, title: str = "") -> dict:
    """
    分类知识内容（简化版，实际应调用 LLM）
    返回: {domain, nature, confidence, tags, summary}
    """
    # 简单规则分类
    domain = "其他"
    nature = "fact"
    confidence = 0.5
    tags = []
    summary = content[:60]

    # 关键词匹配领域
    domain_keywords = {
        "计算机科学": ["代码", "编程", "程序", "数据库", "服务器", "API", "Python", "JavaScript", "算法"],
        "人工智能": ["AI", "模型", "训练", "深度学习", "LLM", "GPT", "embedding", "向量"],
        "金融": ["股票", "基金", "投资", "利率", "市场", "财报", "估值"],
        "个人洞见": ["我觉得", "我认为", "感悟", "心得", "人生", "经历"],
    }

    for d, keywords in domain_keywords.items():
        for kw in keywords:
            if kw.lower() in content.lower():
                domain = d
                break
        if domain != "其他":
            break

    # 关键词匹配 nature
    if any(kw in content for kw in ["应该", "步骤", "方法", "如何"]):
        nature = "method"
    elif any(kw in content for kw in ["我认为", "我觉得", "可能", "也许"]):
        nature = "opinion"
    elif any(kw in content for kw in ["规定", "法规", "制度", "条例"]):
        nature = "regulation"

    return {
        "domain": domain,
        "nature": nature,
        "confidence": confidence,
        "tags": tags,
        "summary": summary
    }


def generate_kb_id(date: str, index: int = 1) -> str:
    """生成知识 ID"""
    return f"KB-{date.replace('-', '')}-{index:03d}"


def generate_frontmatter(kb_id: str, title: str, classification: dict, source: str = "") -> str:
    """生成 Frontmatter"""
    domain = classification.get("domain", "其他")
    if isinstance(domain, str):
        domain = [domain]

    fm = f"""---
id: {kb_id}
title: "{title}"
type: {classification.get('nature', 'concept')}
status: draft
nature: {classification.get('nature', 'fact')}
domain: {json.dumps(domain, ensure_ascii=False)}
confidence: {classification.get('confidence', 0.5)}
source: "{source}"
date_created: {datetime.now().strftime('%Y-%m-%d')}
date_modified: {datetime.now().strftime('%Y-%m-%d')}
version: 1
summary: "{classification.get('summary', '')[:60]}"
---"""
    return fm


def determine_target_dir(root: str, nature: str, domain: str) -> Path:
    """确定知识卡片的目标目录"""
    base_dir = NATURE_DIR_MAP.get(nature, "10_concepts")
    domain_dir = DOMAIN_DIR_MAP.get(domain, "other")

    # 概念类知识按领域分子目录
    if base_dir == "10_concepts":
        return Path(root) / "03_knowledge" / base_dir / domain_dir
    else:
        return Path(root) / "03_knowledge" / base_dir


def write_knowledge_card(root: str, target_dir: Path, filename: str,
                         frontmatter: str, content: str):
    """写入知识卡片文件"""
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / filename

    full_content = frontmatter + "\n\n" + content
    file_path.write_text(full_content, encoding="utf-8")
    return file_path


def log_ingest(root: str, kb_id: str, decision: str, reason: str, confidence: float):
    """记录入库日志"""
    log_dir = Path(root) / "04_memory" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "kb_ingest.log"

    timestamp = datetime.now().isoformat()
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {kb_id} | {decision} | {reason} | {confidence}\n")


def main():
    args = parse_args()
    root = os.path.expanduser(args.root)

    # 获取内容
    content = ""
    source = ""

    if args.url:
        print(f"[INFO] 抓取网页: {args.url}")
        content = fetch_url_content(args.url)
        source = args.url
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"[ERROR] 文件不存在: {args.file}")
            return
        content = file_path.read_text(encoding="utf-8")
        source = str(file_path)
    elif args.text:
        content = args.text
        source = "direct_input"
    else:
        print("[ERROR] 请指定 --url, --file 或 --text")
        return

    if not content.strip():
        print("[ERROR] 内容为空")
        return

    title = args.title or "未命名知识"

    # 分类
    if args.inbox:
        # 仅放入收件箱
        target_dir = Path(root) / "03_knowledge" / "00_inbox"
        classification = {
            "domain": args.domain or "其他",
            "nature": args.nature or "fact",
            "confidence": 0.5,
            "tags": [],
            "summary": content[:60]
        }
    else:
        # 自动分类
        classification = classify_content(content, title)
        # 命令行参数覆盖
        if args.domain:
            classification["domain"] = args.domain
        if args.nature:
            classification["nature"] = args.nature

    # 生成知识卡片
    today = datetime.now().strftime("%Y-%m-%d")
    kb_id = generate_kb_id(today)
    frontmatter = generate_frontmatter(kb_id, title, classification, source)

    if args.inbox:
        target_dir = Path(root) / "03_knowledge" / "00_inbox"
    else:
        target_dir = determine_target_dir(root, classification["nature"], classification["domain"])

    # 生成文件名（英文，用时间戳确保唯一）
    safe_title = re.sub(r'[^\w\u4e00-\u9fff-]', '_', title)[:50]
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_title}.md"

    # 写入
    file_path = write_knowledge_card(root, target_dir, filename, frontmatter, content)
    print(f"[OK] 知识卡片已创建: {file_path}")

    # 记录日志
    log_ingest(root, kb_id, "created", "自动分类入库", classification["confidence"])

    print(f"[INFO] KB-ID: {kb_id}")
    print(f"[INFO] 领域: {classification['domain']}")
    print(f"[INFO] 属性: {classification['nature']}")
    print(f"[INFO] 置信度: {classification['confidence']}")


if __name__ == "__main__":
    main()
