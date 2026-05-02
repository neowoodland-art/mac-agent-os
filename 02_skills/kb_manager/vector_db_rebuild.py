#!/usr/bin/env python3
"""
vector_db_rebuild.py — 双轨向量库重建工具

重建两套向量库：
  - local：agent-os-local/ 下的私有内容（记忆、本机笔记）
  - global：agent-os/03_knowledge/ 下的协同知识库

向量库存储在 agent-os-local/vector_db/ 下（永不同步）：
  agent-os-local/vector_db/local/chroma/    ← 私有内容
  agent-os-local/vector_db/global/chroma/   ← 协同知识（每机自行重建）

使用：
  python3 vector_db_rebuild.py --local ~/workbuddy-agent-os/agent-local --root ~/workbuddy-agent-os/agent-sync
  python3 vector_db_rebuild.py --local ~/workbuddy-agent-os/agent-local --root ~/workbuddy-agent-os/agent-sync --track local
  python3 vector_db_rebuild.py --local ~/workbuddy-agent-os/agent-local --root ~/workbuddy-agent-os/agent-sync --track global
  python3 vector_db_rebuild.py --local ~/workbuddy-agent-os/agent-local --root ~/workbuddy-agent-os/agent-sync --incremental
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="AgentOS 双轨向量库重建")
    parser.add_argument("--root", default="~/workbuddy-agent-os/agent-sync", help="agent-os 根目录")
    parser.add_argument("--local", default="~/workbuddy-agent-os/agent-local", help="~/workbuddy-agent-os/agent-local")
    parser.add_argument("--track", choices=["local", "global", "both"], default="both",
                        help="重建哪套向量库 (默认 both)")
    parser.add_argument("--incremental", action="store_true",
                        help="增量模式：只添加新文件，不清空已有向量库")
    parser.add_argument("--dry-run", action="store_true",
                        help="预览模式：只列出待处理文件，不写入向量库")
    return parser.parse_args()


# ─── 文件扫描 ─────────────────────────────────────────────────────

def scan_md_files(dirs: list[Path], exclude_patterns: list = None) -> list[dict]:
    """扫描 MD 文件，返回文档列表"""
    exclude_patterns = exclude_patterns or []
    docs = []
    for base_dir in dirs:
        if not base_dir.exists():
            continue
        for md_file in sorted(base_dir.rglob("*.md")):
            # 跳过隐藏文件和排除目录
            if any(p in str(md_file) for p in exclude_patterns):
                continue
            if md_file.name.startswith("."):
                continue
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                if len(content.strip()) < 50:
                    continue

                meta = extract_frontmatter(content)
                body = strip_frontmatter(content)

                docs.append({
                    "id": meta.get("id") or f"FILE-{md_file.stat().st_mtime_ns}",
                    "file": str(md_file),
                    "title": meta.get("title", md_file.stem),
                    "content": body[:2000],  # 限制长度
                    "metadata": {
                        "id": meta.get("id", ""),
                        "title": meta.get("title", md_file.stem),
                        "nature": meta.get("nature", ""),
                        "domain": meta.get("domain", ""),
                        "confidence": str(meta.get("confidence", "")),
                        "source_type": meta.get("source_type", ""),
                        "date_created": meta.get("date_created", ""),
                        "file_path": str(md_file),
                    }
                })
            except Exception as e:
                print(f"  [SKIP] {md_file.name}: {e}")
    return docs


def extract_frontmatter(content: str) -> dict:
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    meta = {}
    for line in content[3:end].split("\n"):
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta


def strip_frontmatter(content: str) -> str:
    if not content.startswith("---"):
        return content
    end = content.find("---", 3)
    return content[end + 3:].strip() if end != -1 else content


# ─── 向量库操作 ───────────────────────────────────────────────────

def get_chroma_client(db_path: Path):
    """获取 ChromaDB 客户端"""
    try:
        import chromadb
        db_path.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=str(db_path))
    except ImportError:
        print("[ERROR] chromadb 未安装。请运行: pip install chromadb")
        return None
    except Exception as e:
        print(f"[ERROR] 初始化 ChromaDB 失败: {e}")
        return None


def upsert_documents(client, collection_name: str, docs: list, incremental: bool = False):
    """向 ChromaDB 写入文档"""
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )

    if not incremental:
        # 全量重建：清空后写入
        existing = collection.get(include=[])
        if existing["ids"]:
            collection.delete(ids=existing["ids"])

    # 增量模式：获取已有 ID
    existing_ids = set()
    if incremental:
        existing = collection.get(include=[])
        existing_ids = set(existing["ids"])

    new_docs = [d for d in docs if d["id"] not in existing_ids]
    if not new_docs:
        print(f"  [INFO] {collection_name}: 无新文档（共{len(docs)}个，全部已存在）")
        return 0

    # 批量写入（ChromaDB 建议每批 ≤ 5000）
    batch_size = 500
    total_added = 0
    for i in range(0, len(new_docs), batch_size):
        batch = new_docs[i:i + batch_size]
        collection.add(
            ids=[d["id"] for d in batch],
            documents=[d["content"] for d in batch],
            metadatas=[d["metadata"] for d in batch]
        )
        total_added += len(batch)

    return total_added


# ─── 关键词索引（轻量fallback） ──────────────────────────────────

def build_keyword_index(docs: list, index_path: Path):
    """构建关键词索引（JSON格式，无需向量库也可检索）"""
    entries = []
    for doc in docs:
        meta = doc["metadata"]
        content = doc["content"]
        keywords = list(set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{4,}', content)))[:20]
        entries.append({
            "fact_id": doc["id"],
            "title": meta.get("title", ""),
            "keywords": keywords,
            "domain": meta.get("domain", ""),
            "nature": meta.get("nature", ""),
            "summary": content[:150].replace("\n", " "),
            "date": meta.get("date_created", ""),
            "source": meta.get("source_type", ""),
            "file": meta.get("file_path", "")
        })

    index_data = {
        "version": "2.0.0",
        "last_updated": datetime.now().isoformat(),
        "total": len(entries),
        "entries": entries
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] 关键词索引: {len(entries)} 条 → {index_path}")


# ─── 主流程 ──────────────────────────────────────────────────────

def rebuild_local(local_root: Path, incremental: bool, dry_run: bool):
    """重建本地向量库（私有内容）"""
    print("\n── 重建 local 向量库 ──")
    local_db_path = local_root / "vector_db" / "local" / "chroma"
    keyword_index_path = local_root / "vector_db" / "local" / "keyword_index.json"

    # 扫描本机私有内容
    scan_dirs = [
        local_root / "memory" / "raw",
        local_root / "memory" / "long_term",
        local_root / "materials" / "refined_for_inbox",
    ]
    docs = scan_md_files(scan_dirs)
    print(f"  扫描到 {len(docs)} 个文档")

    if dry_run:
        for d in docs[:5]:
            print(f"  [预览] {d['title']} ({d['metadata'].get('nature', '?')})")
        return

    # 构建关键词索引（始终构建，不依赖 chromadb）
    build_keyword_index(docs, keyword_index_path)

    # 构建向量索引（可选，需 chromadb）
    client = get_chroma_client(local_db_path)
    if client:
        added = upsert_documents(client, "local_memory", docs, incremental)
        print(f"  [OK] ChromaDB local: 新增 {added} 条向量")
    else:
        print("  [INFO] 跳过 ChromaDB，仅使用关键词索引")


def rebuild_global(root: Path, local_root: Path, incremental: bool, dry_run: bool):
    """重建协同向量库（知识库内容）"""
    print("\n── 重建 global 向量库 ──")
    global_db_path = local_root / "vector_db" / "global" / "chroma"
    keyword_index_path = local_root / "vector_db" / "global" / "keyword_index.json"

    # 扫描协同知识库（排除 inbox 等临时目录）
    kb_root = root / "03_knowledge"
    scan_dirs = [
        kb_root / "10_concepts",
        kb_root / "20_methods",
        kb_root / "30_facts",
        kb_root / "40_references",
        kb_root / "50_resources",
        kb_root / "60_opinions",
        kb_root / "01_daily",
    ]
    exclude = ["00_inbox", "00_stream", "90_archive", "99_system", ".obsidian"]
    docs = scan_md_files(scan_dirs, exclude_patterns=exclude)
    print(f"  扫描到 {len(docs)} 个文档")

    if dry_run:
        for d in docs[:5]:
            print(f"  [预览] {d['title']} ({d['metadata'].get('domain', '?')})")
        return

    build_keyword_index(docs, keyword_index_path)

    client = get_chroma_client(global_db_path)
    if client:
        added = upsert_documents(client, "global_knowledge", docs, incremental)
        print(f"  [OK] ChromaDB global: 新增 {added} 条向量")
    else:
        print("  [INFO] 跳过 ChromaDB，仅使用关键词索引")


def main():
    args = parse_args()
    root = Path(args.root).expanduser()
    local_root = Path(args.local).expanduser()

    print("=" * 60)
    print("AgentOS 双轨向量库重建")
    print(f"  agent-os:       {root}")
    print(f"  agent-os-local: {local_root}")
    print(f"  重建范围: {args.track}")
    if args.incremental:
        print("  [增量模式]")
    if args.dry_run:
        print("  [DRY-RUN 模式]")
    print("=" * 60)

    if args.track in ("local", "both"):
        rebuild_local(local_root, args.incremental, args.dry_run)

    if args.track in ("global", "both"):
        rebuild_global(root, local_root, args.incremental, args.dry_run)

    print("\n[完成] 向量库重建完毕")
    print("  下次检索时将自动使用新的向量库（kb_search.py）")


if __name__ == "__main__":
    main()
