#!/usr/bin/env python3
"""
AgentOS 语义检索模块
用途：BM25 + 向量语义混合检索，为记忆体提供语义搜索能力

架构：
  L1 BM25 检索（关键词匹配，基于 keyword_index.json）
  + L1_vec 向量检索（语义匹配，基于 ChromaDB + oMLX embedding）
  → Reciprocal Rank Fusion (RRF) 加权融合
  → 返回排序后的 fact_id 列表

使用：
  # 检索
  python3 semantic_search.py search --root ~/workbuddy-agent-os/agent-sync --query "用户偏好什么编程语言" --top-k 5

  # 向量化单条
  python3 semantic_search.py embed --root ~/workbuddy-agent-os/agent-sync --text "测试文本"

  # 回填所有历史数据
  python3 semantic_search.py backfill --root ~/workbuddy-agent-os/agent-sync

  # 清除向量库并重建
  python3 semantic_search.py rebuild --root ~/workbuddy-agent-os/agent-sync
"""

import argparse
import json
import math
import os
import re
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ─── 默认配置 ──────────────────────────────────────────────────
EMBEDDING_API_URL = "http://localhost:8000/v1/embeddings"
EMBEDDING_MODEL = "Qwen3-Embedding-0.6B"
EMBEDDING_API_KEY = "omlx"
EMBEDDING_DIM = 1024
CHROMA_COLLECTION = "agentos_memories"
BM25_WEIGHT = 0.4       # BM25 在融合中的权重
VECTOR_WEIGHT = 0.6      # 向量相似度在融合中的权重
RRF_K = 60               # RRF 常数，越大排名差异的影响越小


# ─── Embedding API 调用 ─────────────────────────────────────────
def get_embeddings(texts, batch_size=5, retry=3, delay=1.0):
    """
    调用 oMLX embedding API 获取文本向量。
    
    Args:
        texts: 字符串或字符串列表
        batch_size: 每批请求的文本数量（oMLX 对大批量可能超时）
        retry: 失败重试次数
        delay: 批次间延迟（秒）
    
    Returns:
        向量列表（与输入顺序对应）
    """
    import requests

    if isinstance(texts, str):
        texts = [texts]

    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        for attempt in range(retry):
            try:
                resp = requests.post(
                    EMBEDDING_API_URL,
                    json={"model": EMBEDDING_MODEL, "input": batch},
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {EMBEDDING_API_KEY}"
                    },
                    timeout=30
                )
                resp.raise_for_status()
                data = resp.json()
                # 按 index 排序确保顺序一致
                sorted_data = sorted(data["data"], key=lambda x: x["index"])
                batch_embeddings = [item["embedding"] for item in sorted_data]
                all_embeddings.extend(batch_embeddings)
                break
            except Exception as e:
                if attempt < retry - 1:
                    time.sleep(delay * (attempt + 1))
                else:
                    raise RuntimeError(f"Embedding API 调用失败（批次 {i//batch_size + 1}）: {e}")

        if i + batch_size < len(texts):
            time.sleep(delay)

    return all_embeddings


# ─── ChromaDB 向量存储 ─────────────────────────────────────────
class VectorStore:
    """基于 ChromaDB 的向量存储，持久化到磁盘"""

    def __init__(self, persist_dir: str):
        import chromadb
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )

    def upsert(self, fact_id: str, text: str, metadata: dict, embedding: list = None):
        """添加或更新一条向量记录"""
        if embedding is None:
            embeddings = get_embeddings([text])
            embedding = embeddings[0]

        self.collection.upsert(
            ids=[fact_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata]
        )

    def upsert_batch(self, items: list):
        """
        批量添加/更新向量记录。
        
        Args:
            items: [{"fact_id": str, "text": str, "metadata": dict}, ...]
        """
        if not items:
            return

        ids = [item["fact_id"] for item in items]
        texts = [item["text"] for item in items]
        metadatas = [item["metadata"] for item in items]

        # 分批 embedding（避免 API 超时）
        batch_size = 5
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_emb = get_embeddings(texts[i:i + batch_size])
            all_embeddings.extend(batch_emb)
            if i + batch_size < len(texts):
                time.sleep(0.5)

        # 分批 upsert（ChromaDB 建议每批 < 100）
        upsert_batch_size = 50
        for i in range(0, len(ids), upsert_batch_size):
            self.collection.upsert(
                ids=ids[i:i + upsert_batch_size],
                documents=texts[i:i + upsert_batch_size],
                embeddings=all_embeddings[i:i + upsert_batch_size],
                metadatas=metadatas[i:i + upsert_batch_size]
            )

    def search(self, query: str, top_k: int = 10, query_embedding: list = None) -> list:
        """
        向量相似度搜索。
        
        Returns:
            [{"fact_id": str, "score": float, "metadata": dict}, ...]
        """
        if query_embedding is None:
            query_embedding = get_embeddings([query])[0]

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            include=["metadatas", "documents", "distances"]
        )

        items = []
        if results["ids"] and results["ids"][0]:
            for i, fid in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                # ChromaDB cosine distance → 相似度分数（1 - distance）
                score = 1.0 - distance
                items.append({
                    "fact_id": fid,
                    "score": max(0, score),
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "document": results["documents"][0][i] if results["documents"] else ""
                })
        return items

    def delete(self, fact_id: str):
        """删除一条向量记录"""
        self.collection.delete(ids=[fact_id])

    def count(self) -> int:
        """返回向量总数"""
        return self.collection.count()

    def get_all_ids(self) -> list:
        """获取所有 fact_id"""
        result = self.collection.get(include=[])
        return result["ids"] if result["ids"] else []


# ─── BM25 关键词检索 ────────────────────────────────────────────
class BM25Searcher:
    """基于 L1 keyword_index.json 的 BM25 检索"""

    def __init__(self, index_path: str):
        self.index_path = Path(index_path)
        self._build_index()

    def _build_index(self):
        """构建 BM25 索引"""
        from rank_bm25 import BM25Okapi

        if not self.index_path.exists():
            self.entries = []
            self.bm25 = None
            return

        with open(self.index_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.entries = data.get("entries", [])
        if not self.entries:
            self.bm25 = None
            return

        # 用 keywords + summary 构建 BM25 语料库
        self.corpus = []
        for entry in self.entries:
            # 合并关键词和摘要作为 BM25 文档
            doc_words = entry.get("keywords", []) + [entry.get("summary", "")]
            # 中文分词：按 2-4 字切分 + 英文按空格分
            tokens = []
            for w in doc_words:
                if re.match(r'^[\u4e00-\u9fff]+$', w):
                    # 中文：2-4 字 ngram
                    for n in range(2, min(5, len(w) + 1)):
                        tokens.extend([w[i:i+n] for i in range(len(w) - n + 1)])
                    tokens.append(w)  # 也保留完整词
                else:
                    tokens.extend(w.lower().split())
            self.corpus.append(tokens)

        self.bm25 = BM25Okapi(self.corpus)

    def search(self, query: str, top_k: int = 10) -> list:
        """
        BM25 关键词搜索。
        
        Returns:
            [{"fact_id": str, "score": float, "keywords": list}, ...]
        """
        if not self.bm25:
            return []

        # 查询分词
        query_tokens = []
        for w in re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}', query):
            if re.match(r'^[\u4e00-\u9fff]+$', w):
                for n in range(2, min(5, len(w) + 1)):
                    query_tokens.extend([w[i:i+n] for i in range(len(w) - n + 1)])
                query_tokens.append(w)
            else:
                query_tokens.extend(w.lower().split())

        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)

        # 取 top_k
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for idx, score in ranked:
            if score > 0:
                entry = self.entries[idx]
                results.append({
                    "fact_id": entry.get("fact_id", ""),
                    "score": float(score),
                    "keywords": entry.get("keywords", []),
                    "summary": entry.get("summary", ""),
                    "domain": entry.get("domain", ""),
                    "nature": entry.get("nature", "fact")
                })

        return results


# ─── Reciprocal Rank Fusion ─────────────────────────────────────
def reciprocal_rank_fusion(bm25_results: list, vector_results: list,
                           bm25_weight: float = BM25_WEIGHT,
                           vector_weight: float = VECTOR_WEIGHT,
                           rrf_k: int = RRF_K) -> list:
    """
    使用 Reciprocal Rank Fusion 融合 BM25 和向量检索结果。
    
    RRF 公式：score(d) = Σ 1/(k + rank(d))
    加权：score(d) = w_bm25 * rrf_bm25(d) + w_vec * rrf_vec(d)
    
    Returns:
        [{"fact_id": str, "rrf_score": float, "bm25_rank": int, "vec_rank": int,
          "bm25_score": float, "vec_score": float}, ...]
    """
    fact_scores = defaultdict(lambda: {
        "rrf_bm25": 0.0, "rrf_vec": 0.0,
        "bm25_rank": None, "vec_rank": None,
        "bm25_score": 0.0, "vec_score": 0.0,
        "summary": "", "domain": "", "nature": ""
    })

    # BM25 排名贡献
    for rank, item in enumerate(bm25_results, 1):
        fid = item["fact_id"]
        fact_scores[fid]["rrf_bm25"] = 1.0 / (rrf_k + rank)
        fact_scores[fid]["bm25_rank"] = rank
        fact_scores[fid]["bm25_score"] = item["score"]
        fact_scores[fid]["summary"] = item.get("summary", "")
        fact_scores[fid]["domain"] = item.get("domain", "")
        fact_scores[fid]["nature"] = item.get("nature", "fact")

    # 向量排名贡献
    for rank, item in enumerate(vector_results, 1):
        fid = item["fact_id"]
        fact_scores[fid]["rrf_vec"] = 1.0 / (rrf_k + rank)
        fact_scores[fid]["vec_rank"] = rank
        fact_scores[fid]["vec_score"] = item["score"]
        if item.get("metadata"):
            fact_scores[fid]["summary"] = item["metadata"].get("summary", fact_scores[fid]["summary"])
            fact_scores[fid]["domain"] = item["metadata"].get("domain", fact_scores[fid]["domain"])
            fact_scores[fid]["nature"] = item["metadata"].get("nature", fact_scores[fid]["nature"])
        if item.get("document") and not fact_scores[fid]["summary"]:
            fact_scores[fid]["summary"] = item["document"][:120]

    # 加权融合 + 排序
    fused = []
    for fid, scores in fact_scores.items():
        rrf_score = bm25_weight * scores["rrf_bm25"] + vector_weight * scores["rrf_vec"]
        fused.append({
            "fact_id": fid,
            "rrf_score": rrf_score,
            "bm25_rank": scores["bm25_rank"],
            "vec_rank": scores["vec_rank"],
            "bm25_score": scores["bm25_score"],
            "vec_score": scores["vec_score"],
            "summary": scores["summary"],
            "domain": scores["domain"],
            "nature": scores["nature"]
        })

    fused.sort(key=lambda x: x["rrf_score"], reverse=True)
    return fused


# ─── 统一检索入口 ──────────────────────────────────────────────
class MemorySearcher:
    """
    AgentOS 记忆检索器 — BM25 + 向量语义混合检索
    
    Usage:
        searcher = MemorySearcher("/path/to/agent-os")
        results = searcher.search("用户偏好什么编程语言", top_k=5)
    """

    def __init__(self, root: str):
        self.root = Path(root)
        self.vector_store = VectorStore(str(self.root / "04_memory" / "vector_db" / "chroma"))
        self.bm25_searcher = BM25Searcher(str(self.root / "04_memory" / "vector_db" / "keyword_index.json"))
        self.db_path = self.root / "04_memory" / "long_term" / "facts.db"

    def search(self, query: str, top_k: int = 10,
               bm25_weight: float = BM25_WEIGHT,
               vector_weight: float = VECTOR_WEIGHT) -> dict:
        """
        混合检索入口。
        
        Args:
            query: 检索查询文本
            top_k: 返回结果数量
            bm25_weight: BM25 权重（0-1）
            vector_weight: 向量权重（0-1）
        
        Returns:
            {
                "query": str,
                "total_vector": int,  # 向量库总数
                "results": [
                    {
                        "fact_id": str,
                        "rrf_score": float,
                        "bm25_rank": int|null,
                        "vec_rank": int|null,
                        "confidence": float,  # L2 置信度
                        "subject": str,
                        "predicate": str,
                        "object": str,        # L2 完整事实
                        "summary": str,       # L1 摘要
                        "domain": str,
                        "nature": str
                    }, ...
                ]
            }
        """
        # 并行执行两种检索
        bm25_results = self.bm25_searcher.search(query, top_k=top_k * 2)
        vector_results = self.vector_store.search(query, top_k=top_k * 2)

        # RRF 融合
        fused = reciprocal_rank_fusion(
            bm25_results, vector_results,
            bm25_weight=bm25_weight,
            vector_weight=vector_weight
        )

        # 截取 top_k
        fused = fused[:top_k]

        # 从 L2 获取完整事实信息
        results = self._enrich_with_l2(fused)

        return {
            "query": query,
            "total_vector": self.vector_store.count(),
            "bm25_results": len(bm25_results),
            "vector_results": len(vector_results),
            "results": results
        }

    def _enrich_with_l2(self, fused_results: list) -> list:
        """从 L2 facts.db 补充完整事实信息"""
        if not self.db_path.exists():
            return fused_results

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        enriched = []
        for item in fused_results:
            fid = item["fact_id"]
            row = cursor.execute(
                "SELECT subject, predicate, object, confidence, nature, domain FROM facts WHERE id = ?",
                (fid,)
            ).fetchone()

            if row:
                enriched.append({
                    "fact_id": fid,
                    "rrf_score": round(item["rrf_score"], 6),
                    "bm25_rank": item["bm25_rank"],
                    "vec_rank": item["vec_rank"],
                    "confidence": row["confidence"],
                    "subject": row["subject"],
                    "predicate": row["predicate"],
                    "object": row["object"],
                    "summary": item.get("summary", row["object"][:120]),
                    "domain": row["domain"],
                    "nature": row["nature"]
                })
            else:
                # L2 中不存在（不应该发生，但防御性处理）
                enriched.append({
                    "fact_id": fid,
                    "rrf_score": round(item["rrf_score"], 6),
                    "bm25_rank": item["bm25_rank"],
                    "vec_rank": item["vec_rank"],
                    "confidence": 0,
                    "subject": "",
                    "predicate": "",
                    "object": item.get("summary", ""),
                    "summary": item.get("summary", ""),
                    "domain": item.get("domain", ""),
                    "nature": item.get("nature", "")
                })

        conn.close()
        return enriched

    def add_fact(self, fact_id: str, text: str, metadata: dict):
        """添加单条事实到向量库"""
        self.vector_store.upsert(fact_id, text, metadata)

    def remove_fact(self, fact_id: str):
        """从向量库删除一条事实"""
        self.vector_store.delete(fact_id)

    def backfill_all(self, batch_size: int = 5, verbose: bool = True):
        """
        回填所有 L2 事实到向量库。
        从 facts.db 读取所有事实，生成 embedding 并写入 ChromaDB。
        """
        if not self.db_path.exists():
            print("[ERROR] facts.db 不存在")
            return 0

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        facts = cursor.execute(
            "SELECT id, subject, predicate, object, confidence, nature, domain, source, date_created FROM facts"
        ).fetchall()
        conn.close()

        if not facts:
            print("[INFO] facts.db 为空，无需回填")
            return 0

        # 获取向量库已有 ID
        existing_ids = set(self.vector_store.get_all_ids())

        # 构建待回填列表
        to_fill = []
        for fact in facts:
            if fact["id"] not in existing_ids:
                text = f"{fact['subject']} {fact['predicate']} {fact['object']}"
                metadata = {
                    "summary": fact["object"][:120],
                    "domain": fact["domain"],
                    "nature": fact["nature"],
                    "source": fact["source"],
                    "date_created": fact["date_created"],
                    "confidence": fact["confidence"]
                }
                to_fill.append({
                    "fact_id": fact["id"],
                    "text": text,
                    "metadata": metadata
                })

        if not to_fill:
            print(f"[INFO] 全部 {len(facts)} 条事实已在向量库中，无需回填")
            return 0

        if verbose:
            print(f"[INFO] 需要回填 {len(to_fill)} 条事实（总共 {len(facts)} 条）")

        # 分批处理
        filled = 0
        for i in range(0, len(to_fill), batch_size):
            batch = to_fill[i:i + batch_size]
            try:
                self.vector_store.upsert_batch(batch)
                filled += len(batch)
                if verbose:
                    pct = filled / len(to_fill) * 100
                    print(f"  [{pct:5.1f}%] {filled}/{len(to_fill)} 已回填")
            except Exception as e:
                print(f"  [ERROR] 批次 {i//batch_size + 1} 失败: {e}")
                # 尝试逐条重试
                for item in batch:
                    try:
                        self.vector_store.upsert(
                            item["fact_id"], item["text"],
                            item["metadata"]
                        )
                        filled += 1
                        if verbose:
                            print(f"    [RETRY] {item['fact_id']} OK")
                    except Exception as e2:
                        print(f"    [FAIL] {item['fact_id']}: {e2}")

        if verbose:
            print(f"[OK] 回填完成: {filled}/{len(to_fill)} 成功, 向量库总数: {self.vector_store.count()}")
        return filled

    def rebuild(self):
        """清除向量库并完全重建"""
        import chromadb
        persist_dir = str(self.root / "04_memory" / "vector_db" / "chroma")

        # 删除旧数据库
        import shutil
        if os.path.exists(persist_dir):
            shutil.rmtree(persist_dir)
            print(f"[OK] 已清除旧向量库: {persist_dir}")

        # 重新初始化
        self.vector_store = VectorStore(persist_dir)
        print("[OK] 向量库已重建")

        # 回填
        return self.backfill_all()


# ─── CLI 入口 ──────────────────────────────────────────────────
def cmd_search(args):
    searcher = MemorySearcher(args.root)
    result = searcher.search(args.query, top_k=args.top_k)

    print(f"\n{'='*60}")
    print(f"检索: {result['query']}")
    print(f"向量库总数: {result['total_vector']} | "
          f"BM25命中: {result['bm25_results']} | 向量命中: {result['vector_results']}")
    print(f"{'='*60}\n")

    if not result["results"]:
        print("（无匹配结果）")
        return

    for i, item in enumerate(result["results"], 1):
        bm25_r = f"BM25#{item['bm25_rank']}" if item["bm25_rank"] else "BM25#-"
        vec_r = f"VEC#{item['vec_rank']}" if item["vec_rank"] else "VEC#-"
        print(f"[{i}] {item['fact_id']}  RRF={item['rrf_score']:.4f}  conf={item['confidence']}  "
              f"{bm25_r}  {vec_r}")
        print(f"    [{item['domain']}] {item['subject']} → {item['object'][:100]}")
        print()


def cmd_embed(args):
    embeddings = get_embeddings([args.text])
    print(f"维度: {len(embeddings[0])}")
    print(f"前5值: {embeddings[0][:5]}")
    print(f"范数: {math.sqrt(sum(x*x for x in embeddings[0])):.4f}")


def cmd_backfill(args):
    searcher = MemorySearcher(args.root)
    searcher.backfill_all()


def cmd_rebuild(args):
    searcher = MemorySearcher(args.root)
    searcher.rebuild()


def main():
    parser = argparse.ArgumentParser(description="AgentOS 语义检索模块")
    parser.add_argument("--root", required=True, help="agent-os 根目录路径")
    subparsers = parser.add_subparsers(dest="command")

    # search
    sp_search = subparsers.add_parser("search", help="混合检索")
    sp_search.add_argument("--query", required=True, help="检索查询")
    sp_search.add_argument("--top-k", type=int, default=5, help="返回结果数量")

    # embed
    sp_embed = subparsers.add_parser("embed", help="测试 embedding")
    sp_embed.add_argument("--text", required=True, help="测试文本")

    # backfill
    subparsers.add_parser("backfill", help="回填所有历史数据到向量库")

    # rebuild
    subparsers.add_parser("rebuild", help="清除并重建向量库")

    args = parser.parse_args()

    if args.command == "search":
        cmd_search(args)
    elif args.command == "embed":
        cmd_embed(args)
    elif args.command == "backfill":
        cmd_backfill(args)
    elif args.command == "rebuild":
        cmd_rebuild(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
