#!/usr/bin/env python3
"""
kb_search.py — 双轨知识库检索

先查本地向量库（agent-local/vector_db/local/），
再查协同向量库（agent-local/vector_db/global/），
结果合并展示，优先显示本地记忆。

向量库由 vector_db_rebuild.py 构建，基于 ChromaDB。

使用：
  python3 kb_search.py --query "记忆固化机制"
  python3 kb_search.py --query "Python装饰器" --top 10
  python3 kb_search.py --query "知识库" --track global   # 只查协同库
  python3 kb_search.py --query "今天的会议" --track local  # 只查本地库
  python3 kb_search.py --query "向量" --keyword           # 纯关键词搜索（无需向量库）
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="AgentOS 双轨知识库检索")
    parser.add_argument("--query", required=True, help="检索查询语句")
    parser.add_argument("--local", default="~/workbuddy-agent-os/agent-local", help="~/workbuddy-agent-os/agent-local")
    parser.add_argument("--root", default="~/workbuddy-agent-os/agent-sync", help="agent-os 根目录")
    parser.add_argument("--top", type=int, default=5, help="返回结果数（默认5）")
    parser.add_argument("--track", choices=["local", "global", "both"], default="both",
                        help="检索范围: local(本地) | global(协同) | both(默认)")
    parser.add_argument("--keyword", action="store_true",
                        help="纯关键词搜索（不使用向量库，适合没有重建向量库的环境）")
    parser.add_argument("--domain", default=None, help="过滤领域（如 ai / finance）")
    return parser.parse_args()


# ─── 向量库检索 ───────────────────────────────────────────────────

def get_embedding_model():
    """获取嵌入模型（优先 SentenceTransformers，fallback 到关键词）"""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model
    except ImportError:
        pass
    try:
        from chromadb.utils import embedding_functions
        return embedding_functions.DefaultEmbeddingFunction()
    except Exception:
        pass
    return None


def search_chroma(db_path: Path, query: str, top_n: int, domain_filter: str = None) -> list:
    """在指定 ChromaDB 中搜索"""
    try:
        import chromadb
    except ImportError:
        print("[WARN] chromadb 未安装，跳过向量检索")
        return []

    if not db_path.exists():
        return []

    try:
        client = chromadb.PersistentClient(path=str(db_path))
        collections = client.list_collections()
        if not collections:
            return []

        results = []
        for col in collections:
            collection = client.get_collection(col.name)
            where = {"domain": domain_filter} if domain_filter else None
            try:
                res = collection.query(
                    query_texts=[query],
                    n_results=min(top_n, collection.count()),
                    where=where,
                    include=["documents", "metadatas", "distances"]
                )
            except Exception:
                res = collection.query(
                    query_texts=[query],
                    n_results=min(top_n, collection.count()),
                    include=["documents", "metadatas", "distances"]
                )

            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]

            for doc, meta, dist in zip(docs, metas, dists):
                results.append({
                    "content": doc[:300],
                    "meta": meta,
                    "score": round(1 - dist, 4),  # 转换为相似度分数
                    "track": "local" if "local" in str(db_path) else "global"
                })

        return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]
    except Exception as e:
        print(f"[WARN] 向量检索出错: {e}")
        return []


# ─── 关键词检索（fallback） ───────────────────────────────────────

def search_keyword_index(index_path: Path, query: str, top_n: int) -> list:
    """从 keyword_index.json 关键词索引中搜索"""
    if not index_path.exists():
        return []
    try:
        with open(index_path, encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries", [])
    except Exception:
        return []

    query_terms = set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', query.lower()))
    scored = []
    for entry in entries:
        kws = {k.lower() for k in entry.get("keywords", [])}
        summary = entry.get("summary", "").lower()
        # 计算匹配分数
        kw_hits = len(query_terms & kws)
        content_hits = sum(1 for t in query_terms if t in summary)
        score = kw_hits * 2 + content_hits
        if score > 0:
            scored.append({
                "content": entry.get("summary", "")[:300],
                "meta": {
                    "id": entry.get("fact_id", ""),
                    "domain": entry.get("domain", ""),
                    "nature": entry.get("nature", ""),
                    "date": entry.get("date", "")
                },
                "score": score,
                "track": "local_index"
            })

    return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_n]


def search_md_files(search_dir: Path, query: str, top_n: int, domain_filter: str = None) -> list:
    """直接在 MD 文件中做关键词全文搜索"""
    if not search_dir.exists():
        return []

    query_terms = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', query.lower())
    if not query_terms:
        return []

    scored = []
    for md_file in search_dir.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            content_lower = content.lower()
            hits = sum(content_lower.count(term) for term in query_terms)
            if hits == 0:
                continue

            # 解析 frontmatter 获取元数据
            meta = {}
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    for line in content[3:end].split("\n"):
                        if ":" in line:
                            k, _, v = line.partition(":")
                            meta[k.strip()] = v.strip().strip('"')

            if domain_filter and meta.get("domain") and domain_filter not in meta.get("domain", ""):
                continue

            # 提取匹配片段
            snippet = ""
            for term in query_terms:
                idx = content_lower.find(term)
                if idx >= 0:
                    start = max(0, idx - 60)
                    end_idx = min(len(content), idx + 200)
                    snippet = "..." + content[start:end_idx].replace("\n", " ") + "..."
                    break

            scored.append({
                "content": snippet or content[:300],
                "meta": {
                    "id": meta.get("id", ""),
                    "title": meta.get("title", md_file.stem),
                    "domain": meta.get("domain", ""),
                    "nature": meta.get("nature", ""),
                    "file": str(md_file),
                },
                "score": hits,
                "track": "global_md"
            })
        except Exception:
            continue

    return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_n]


# ─── 结果展示 ─────────────────────────────────────────────────────

def format_result(idx: int, result: dict) -> str:
    meta = result.get("meta", {})
    track = result.get("track", "?")
    score = result.get("score", 0)
    title = meta.get("title", meta.get("id", "未知"))
    domain = meta.get("domain", "?")
    nature = meta.get("nature", "?")
    content = result.get("content", "")[:200].replace("\n", " ")

    track_icon = {"local": "🔒", "global": "🌐", "local_index": "📇", "global_md": "📄"}.get(track, "❓")

    return (f"\n{idx}. {track_icon}[{track}] {title}\n"
            f"   领域:{domain} 类型:{nature} 相关度:{score}\n"
            f"   {content}")


def main():
    args = parse_args()
    local_root = Path(args.local).expanduser()
    root = Path(args.root).expanduser()
    query = args.query
    top_n = args.top

    print(f"\n🔍 检索: '{query}' (范围:{args.track}, top:{top_n})")
    print("=" * 60)

    all_results = []

    if args.keyword:
        # 纯关键词模式
        if args.track in ("local", "both"):
            idx_path = local_root / "vector_db" / "local" / "keyword_index.json"
            results = search_keyword_index(idx_path, query, top_n)
            all_results.extend(results)

        if args.track in ("global", "both"):
            kb_dir = root / "03_knowledge"
            results = search_md_files(kb_dir, query, top_n, args.domain)
            all_results.extend(results)

    else:
        # 向量检索模式
        if args.track in ("local", "both"):
            local_db = local_root / "vector_db" / "local" / "chroma"
            results = search_chroma(local_db, query, top_n, args.domain)
            if not results:
                # fallback 到关键词索引
                idx_path = local_root / "vector_db" / "local" / "keyword_index.json"
                results = search_keyword_index(idx_path, query, top_n)
            all_results.extend(results)

        if args.track in ("global", "both"):
            global_db = local_root / "vector_db" / "global" / "chroma"
            results = search_chroma(global_db, query, top_n, args.domain)
            if not results:
                # fallback 到 MD 全文搜索
                results = search_md_files(root / "03_knowledge", query, top_n, args.domain)
            all_results.extend(results)

    # 去重 + 合并排序（local优先，同分数local排前）
    seen = set()
    deduped = []
    for r in sorted(all_results, key=lambda x: (-x["score"], 0 if "local" in x["track"] else 1)):
        key = r["meta"].get("id") or r["meta"].get("file") or r["content"][:50]
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    if not deduped:
        print("\n未找到相关结果。")
        print("提示: 运行 vector_db_rebuild.py 重建向量库后检索效果更好")
        return

    for i, result in enumerate(deduped[:top_n], 1):
        print(format_result(i, result))

    print(f"\n共找到 {len(deduped)} 条结果（显示前{min(top_n, len(deduped))}条）")
    print("🔒=本地记忆  🌐=协同知识库  📇=关键词索引  📄=MD全文")


if __name__ == "__main__":
    main()
