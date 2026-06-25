"""
小红书评论语料库
风格: 种草/经验分享/生活方式/美食/旅行/美妆/穿搭
特点: 语气亲切、emoji 适度、实用性强、避免营销感

分类标签:
- lifestyle: 生活方式/日常
- food: 美食/探店
- travel: 旅行/出游
- beauty: 美妆/护肤
- fashion: 穿搭/时尚
- tips: 经验/技巧
- emotion: 情感共鸣
"""

import random

# ════════════════════════════════════════════════════════════
# 会话级去重 — 同一运行中不重复发送相同评论
# ════════════════════════════════════════════════════════════

_used_comments: set = set()


def reset_session():
    """清空已用评论记录（新账号/新运行开始时调用）"""
    _used_comments.clear()

# ════════════════════════════════════════════════════════════
# 按分类组织的语料
# ════════════════════════════════════════════════════════════

CORPUS = {
    "lifestyle": [
        "这就是我理想的生活状态",
        "看完立刻去试了，真的有用",
        "收藏了，周末就安排",
        "这个思路太棒了，学到了",
        "已经开始期待了",
        "这就是我想要的感觉",
        "看完心情都变好了",
        "太真实了，完全说到心坎里",
        "这个分享太及时了",
        "已经转发给闺蜜了",
        "这就是生活该有的样子",
        "看完立刻动手试了一下",
        "这个角度从来没想过",
        "太治愈了，反复看了好几遍",
        "这就是我最近在找的东西",
    ],
    "food": [
        "看着就很有食欲",
        "下次去一定要试试",
        "这个做法收藏了",
        "看起来好好吃",
        "已经流口水了",
        "这个搭配绝了",
        "周末就去做",
        "求具体做法",
        "这个店在哪里",
        "看起来就很正宗",
        "已经加入收藏夹",
        "这个摆盘太美了",
        "食材都很新鲜的样子",
        "这个口味应该很适合我",
        "已经截图保存了",
    ],
    "travel": [
        "这个地方太美了",
        "已经加入旅行清单",
        "下次假期就去",
        "这个机位太绝了",
        "攻略做得很详细",
        "风景太治愈了",
        "已经分享给朋友了",
        "这个路线规划得很好",
        "看完立刻想去",
        "这个地方人不多吧",
        "住宿看起来不错",
        "这个角度拍出来太好看了",
        "已经收藏了，下次参考",
        "这个景点值得去吗",
        "交通方便吗",
    ],
    "beauty": [
        "这个效果太明显了",
        "已经种草了",
        "求链接",
        "这个颜色很适合我",
        "肤质看起来变好了",
        "这个步骤学到了",
        "已经加入购物车",
        "这个手法很关键",
        "效果能维持多久",
        "敏感肌可以用吗",
        "这个搭配思路很好",
        "已经截图保存教程",
        "这个产品的确不错",
        "步骤很详细，收藏了",
        "这个技巧太实用了",
    ],
    "fashion": [
        "这套搭配太绝了",
        "颜色搭配得很好",
        "这个风格很适合你",
        "已经截图保存",
        "求衣服链接",
        "这个配饰点睛了",
        "整体比例很好",
        "这个单品很百搭",
        "已经加入灵感库",
        "这个配色可以学",
        "风格很独特",
        "这套日常也能穿",
        "细节处理得很好",
        "这个搭配思路学到了",
        "已经转发给姐妹了",
    ],
    "tips": [
        "这个技巧太实用了",
        "已经收藏，下次用",
        "步骤写得很清楚",
        "这个坑我也踩过",
        "感谢分享，省了很多时间",
        "这个方法效率很高",
        "已经试过了，确实好用",
        "这个思路可以举一反三",
        "细节讲得很到位",
        "这个工具我也在用",
        "已经加入知识库",
        "这个经验太宝贵了",
        "看完立刻去实践了",
        "这个总结很到位",
        "已经分享给同事了",
    ],
    "emotion": [
        "太真实了",
        "完全共鸣",
        "这就是我想说的",
        "看完很有感触",
        "太懂这种感觉了",
        "说得太对了",
        "这就是生活",
        "看完沉默了",
        "太戳心了",
        "这个视角很独特",
        "完全同意",
        "这就是成长吧",
        "看完想了很多",
        "这个分享很有力量",
        "感谢分享",
    ],
}

# ════════════════════════════════════════════════════════════
# 通用短评（不分类，随机使用）
# ════════════════════════════════════════════════════════════

GENERAL_SHORT = [
    "学到了",
    "收藏了",
    "确实如此",
    "很有道理",
    "太棒了",
    "感谢分享",
    "已三连",
    "好文",
    "mark",
    "码住",
    "实用",
    "干货",
    "受教了",
    "涨知识了",
    "这个好",
    "不错",
    "可以",
    "666",
    "绝了",
    "牛",
]

# ── 三级接力语料（评论→回复→再回复的自然互动链）──
# 每个分类含 first/reply/second 三层
CHAIN_CORPUS = {
    "food": [
        {"first": "看着就很有食欲，周末去试试", "reply": "同意！上次去吃过一次确实不错", "second": "我也去过，他家那个招牌菜绝了"},
        {"first": "这个做法收藏了，回家就做", "reply": "做了好几次了，家人都说好吃", "second": "是的，跟着做了一次很成功"},
    ],
    "travel": [
        {"first": "这个地方太美了，已加入旅行清单", "reply": "去年去过，风景确实好，值得二刷", "second": "求攻略！准备下个月去"},
        {"first": "这个机位太绝了，拍得真好", "reply": "早上五点去占的位置，值得", "second": "太卷了哈哈哈，不过效果确实好"},
    ],
    "tech": [
        {"first": "分析得很透彻，学到了", "reply": "对，第三点我之前完全没想到", "second": "是的，按这个方法试了效果很好"},
    ],
    "lifestyle": [
        {"first": "这就是我理想的生活状态", "reply": "同款生活！每天都很充实", "second": "羡慕了，我也要这样过"},
    ],
    "emotion": [
        {"first": "太真实了，完全说到心坎里", "reply": "是啊，经历过的人才懂", "second": "抱抱，都会好起来的"},
    ],
}


def get_chain(group: str = "food", position: str = "first") -> str:
    """获取三级接力语料。group=分类, position=first/reply/second"""
    import random
    pool = CHAIN_CORPUS.get(group, CHAIN_CORPUS["food"])
    item = random.choice(pool)
    return item.get(position, item["first"])


def get_chain_group(group: str = "food") -> dict:
    """获取一组完整的三级接力语料"""
    import random
    pool = CHAIN_CORPUS.get(group, CHAIN_CORPUS["food"])
    return random.choice(pool)


# ════════════════════════════════════════════════════════════
# 评论生成器
# ════════════════════════════════════════════════════════════


def get_comment(category: str = None, length: str = "medium") -> str:
    """
    获取一条小红书风格评论（自动去重：同一运行中不会重复返回相同评论）

    Args:
        category: 分类标签 (lifestyle/food/travel/beauty/fashion/tips/emotion)
                  None 时随机选择分类
        length: 长度控制
            - short: 2~8 字短评
            - medium: 10~25 字常规评论 (默认)
            - long: 25~50 字长评论

    Returns:
        评论文本
    """
    global _used_comments

    if length == "short":
        available = [c for c in GENERAL_SHORT if c not in _used_comments]
        if not available:
            available = GENERAL_SHORT  # 用完了就复用
        comment = random.choice(available)
        _used_comments.add(comment)
        return comment

    if category and category in CORPUS:
        pool = [c for c in CORPUS[category] if c not in _used_comments]
        if not pool:
            pool = CORPUS[category]  # 用完了就复用
    else:
        all_items = []
        for cat_items in CORPUS.values():
            all_items.extend(cat_items)
        pool = [c for c in all_items if c not in _used_comments]
        if not pool:
            pool = all_items  # 用完了就复用

    comment = random.choice(pool)
    _used_comments.add(comment)

    # 长度控制
    if length == "long" and len(comment) < 20:
        # 追加一条短评组合
        comment += "。" + random.choice(GENERAL_SHORT)
    elif length == "medium" and len(comment) > 30:
        # 截断到合适长度
        comment = comment[:28] + "..."

    return comment


def get_comments(count: int = 3, category: str = None, length: str = "medium") -> list:
    """获取多条不重复评论"""
    results = []
    pool = []

    if category and category in CORPUS:
        pool = CORPUS[category].copy()
    else:
        for cat_items in CORPUS.values():
            pool.extend(cat_items)

    # 去重并随机选择
    unique_pool = list(set(pool))
    if count > len(unique_pool):
        count = len(unique_pool)

    selected = random.sample(unique_pool, count)

    for comment in selected:
        if length == "short":
            comment = random.choice(GENERAL_SHORT)
        elif length == "long" and len(comment) < 20:
            comment += "。" + random.choice(GENERAL_SHORT)
        results.append(comment)

    return results


# ════════════════════════════════════════════════════════════
# 快捷函数
# ════════════════════════════════════════════════════════════


def random_comment() -> str:
    """随机获取一条中等长度评论（养号默认使用）"""
    return get_comment(length="medium")


def short_comment() -> str:
    """获取短评"""
    return get_comment(length="short")


def long_comment() -> str:
    """获取长评"""
    return get_comment(length="long")
