"""
comment_corpus.py — 评论语料库引擎

从 comment_corpus.yaml 加载分类评论，按权重随机选取。
支持模板填充、分类筛选、手动增加。
"""
import random
import yaml
from pathlib import Path

CORPUS_PATH = Path(__file__).parent.parent.parent / "config" / "comment_corpus.yaml"


def load_corpus() -> dict:
    """加载语料库 YAML"""
    with open(CORPUS_PATH, encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_comment(keyword: str = "", category: str = None) -> str:
    """获取一条随机评论

    Args:
        keyword: 当前视频关键词，用于模板替换
        category: 指定分类（None=从所有启用分类中选）

    Returns:
        评论文本
    """
    corpus = load_corpus()
    cfg = corpus.get("config", {})
    enabled = cfg.get("enabled_categories", [])
    disabled = cfg.get("disabled_categories", [])
    prefer_templates = cfg.get("prefer_templates", True)

    # 筛选可用分类
    categories = []
    for cat_key, cat_data in corpus.get("categories", {}).items():
        weight = cat_data.get("weight", 0)
        if weight <= 0:
            continue
        if enabled and cat_key not in enabled:
            continue
        if cat_key in disabled:
            continue
        if category and cat_key != category:
            continue
        categories.append((cat_key, cat_data, weight))

    if not categories:
        return "好内容"  # 兜底

    # 按权重选分类
    keys, datas, weights = zip(*categories)
    chosen_key = random.choices(keys, weights=weights, k=1)[0]
    chosen_data = datas[keys.index(chosen_key)]

    # 从选中的分类中选一条评论
    comments = chosen_data.get("comments", [])
    templates = chosen_data.get("templates", [])

    # 优先用模板
    if prefer_templates and templates and random.random() < 0.4:
        template = random.choice(templates)
        return template.format(keyword=keyword or "这个")
    elif comments:
        return random.choice(comments)
    elif templates:
        template = random.choice(templates)
        return template.format(keyword=keyword or "这个")
    return "👍"


def add_comment(category: str, comment: str):
    """手动增加一条评论到语料库"""
    with open(CORPUS_PATH, encoding='utf-8') as f:
        corpus = yaml.safe_load(f)

    cat = corpus.get("categories", {}).get(category)
    if not cat:
        print(f"❌ 分类 '{category}' 不存在")
        return

    if "comments" not in cat:
        cat["comments"] = []
    cat["comments"].append(comment)

    with open(CORPUS_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(corpus, f, allow_unicode=True, indent=2, sort_keys=False)
    print(f"✅ 已添加评论到 [{category}]: {comment}")


def list_categories() -> str:
    """列出所有可用分类"""
    corpus = load_corpus()
    lines = ["📋 语料库分类:"]
    for key, data in corpus.get("categories", {}).items():
        w = data.get("weight", 0)
        status = "✅" if w > 0 else "⛔"
        n = len(data.get("comments", [])) + len(data.get("templates", []))
        lines.append(f"  {status} {key:20s} (权重{w}, {n}条) - {data.get('label','')}")
    return '\n'.join(lines)


if __name__ == "__main__":
    print(list_categories())
    print()
    for _ in range(5):
        print(f"  → {get_comment('编程')}")
