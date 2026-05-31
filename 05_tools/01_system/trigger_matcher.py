#!/usr/bin/env python3
"""
触发词语义匹配检测工具
混合模式：先关键词精确匹配，未命中则 Embedding 语义相似度匹配

用法：
  python3 trigger_matcher.py "用户说的话"
  
返回：
  matched: true/false
  category: "meta-thinking" / "cross-domain" / "knowledge-review" / ""
  match_type: "keyword" / "semantic" / ""
  similarity: 0.0-1.0
"""

import json, sys, os, urllib.request

# 触发类别及种子词
TRIGGER_CATEGORIES = {
    "meta-thinking": ["升维思考", "第一性原理", "前提挑战", "深层原因", "本质是什么", "批判地看", "升维", "本质", "前提"],
    "cross-domain": ["跨界视角", "换个角度", "类比一下", "新视角", "别的领域", "借鉴一下", "跨界", "类比", "新角度", "换个思路"],
    "knowledge-review": ["入库", "记录这条", "保存知识", "知识审查", "记录", "保存"],
}

EMBEDDING_URL = "http://localhost:8000/v1/embeddings"
EMBEDDING_MODEL = "Qwen3-Embedding-0.6B"
SIMILARITY_THRESHOLD = 0.8


def keyword_match(text: str) -> tuple:
    """关键词精确匹配，返回 (category, trigger_word) 或 ("", "")"""
    for category, keywords in TRIGGER_CATEGORIES.items():
        for kw in keywords:
            if kw in text:
                return category, kw
    return "", ""


def get_embedding(text: str) -> list:
    """调用 oMLX Embedding API 获取向量"""
    data = json.dumps({
        "model": EMBEDDING_MODEL,
        "input": text
    }).encode()
    req = urllib.request.Request(
        EMBEDDING_URL, data=data,
        headers={"Authorization": "Bearer omlx", "Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=10)
    result = json.loads(resp.read())
    return result["data"][0]["embedding"]


def cosine_similarity(a: list, b: list) -> float:
    """计算余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def semantic_match(text: str) -> tuple:
    """语义相似度匹配，返回 (best_category, best_score)"""
    try:
        text_vec = get_embedding(text)
    except Exception as e:
        return ("", 0.0)

    best_cat = ""
    best_score = 0.0
    for category, keywords in TRIGGER_CATEGORIES.items():
        # 用类别名 + 第一个种子词作为类别向量
        cat_text = f"{category}: {', '.join(keywords[:2])}"
        try:
            cat_vec = get_embedding(cat_text)
            score = cosine_similarity(text_vec, cat_vec)
            if score > best_score:
                best_score = score
                best_cat = category
        except:
            continue
    return (best_cat, best_score)


def detect(text: str) -> dict:
    """主检测函数：先关键词，再语义"""
    cat, kw = keyword_match(text)
    if cat:
        return {
            "matched": True,
            "category": cat,
            "match_type": "keyword",
            "trigger": kw,
            "similarity": 1.0
        }
    
    cat, score = semantic_match(text)
    if cat and score >= SIMILARITY_THRESHOLD:
        return {
            "matched": True,
            "category": cat,
            "match_type": "semantic",
            "trigger": "",
            "similarity": round(score, 4)
        }
    
    return {
        "matched": False,
        "category": "",
        "match_type": "",
        "trigger": "",
        "similarity": 0.0
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: trigger_matcher.py <文本>")
        sys.exit(1)
    text = sys.argv[1]
    result = detect(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
