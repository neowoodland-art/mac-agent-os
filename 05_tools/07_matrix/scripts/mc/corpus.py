"""
corpus.py — 评论语料库管理

双平台隔离: 抖音/小红书 各自独立语料
每个平台下分多个分类，含权重、启用状态

文件结构:
  corpus/
  ├── douyin.yaml       ← 抖音语料
  └── xiaohongshu.yaml  ← 小红书语料

YAML 格式:
  version: "1.0"
  categories:
    赞美:
      weight: 30
      enabled: true
      label: "赞美评论"
      comments:
        - "讲得太好了，受益匪浅！"
        - "这个观点很新颖，学习了"
    搞笑:
      weight: 20
      enabled: true
      label: "搞笑评论"
      comments:
        - "笑死我了哈哈哈哈哈"
"""
import logging
import random
import re
import yaml
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)

TOOL_DIR = Path(__file__).resolve().parent.parent.parent
CORPUS_DIR = TOOL_DIR / "corpus"

# ── 关键词 → 方向 映射 ──────────────────────────────────────────
KEYWORD_CATEGORY_MAP = [
    (["科技", "数码", "手机"], ["称赞", "提问"]),
    (["美食", "做饭", "菜"], ["称赞", "共鸣"]),
    (["旅游", "风景", "旅行"], ["称赞", "提问"]),
    (["情感", "生活", "感悟"], ["共鸣", "安慰"]),
    (["知识", "科普", "教育"], ["提问", "补充"]),
]

# 方向名称 → 实际分类名称（兼容两个平台已有的分类）
DIRECTION_TO_CATEGORY = {
    "称赞": "赞美",
    "正面": "赞美",
    "提问": "提问",
    "共鸣": "感慨",
    "安慰": "感慨",
    "补充": "客观",
}

# 默认方向标签（用于 fallback）
ALL_DIRECTIONS = list(DIRECTION_TO_CATEGORY.keys())
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

# 默认跨平台通用分类
DEFAULT_DOUYIN_COMMENTS = {
    "赞美": {
        "weight": 30, "enabled": True, "label": "赞美评论",
        "comments": [
            "讲得太好了，受益匪浅！",
            "这个观点很新颖，学习了",
            "说得真是振聋发聩",
            "干货满满，感谢分享",
            "条理清晰，逻辑严密",
            "每一句话都说到了心坎里",
        ],
        "templates": ["关于{keyword}的观点很到位", "感谢分享{keyword}的心得", "说得太好了，{keyword}这部分启发很大"],
    },
    "搞笑": {
        "weight": 20, "enabled": True, "label": "搞笑评论",
        "comments": ["哈哈哈哈哈笑死", "有才，这评论比视频还精彩", "笑不活了家人们", "你要把我笑死"],
        "templates": ["{keyword}这个梗笑死我了", "哈哈哈哈{keyword}太有才了"],
    },
    "客观": {
        "weight": 15, "enabled": True, "label": "客观评价",
        "comments": ["比较客观", "抛开立场看，说得有道理", "中肯的评价", "理性分析，值得一读"],
        "templates": ["关于{keyword}的分析很客观", "理性的声音，{keyword}这部分说得好"],
    },
    "提问": {
        "weight": 10, "enabled": True, "label": "提问互动",
        "comments": ["请问这是在哪里？", "能分享一下具体方法吗？", "新手想问一下怎么入门", "这个需要什么工具？"],
        "templates": ["{keyword}具体怎么操作？", "能详细讲讲{keyword}吗？"],
    },
    "感慨": {
        "weight": 10, "enabled": True, "label": "生活感慨",
        "comments": ["生活不易，且行且珍惜", "每个人都有自己的故事", "看得我热泪盈眶", "这就是生活啊"],
        "templates": ["看到{keyword}想起了自己", "{keyword}真的太真实了"],
    },
}

# 小红书专属分类
DEFAULT_XHS_COMMENTS = {
    "穿搭": {
        "weight": 25, "enabled": True, "label": "穿搭评论",
        "comments": ["这套搭配好好看！", "求链接！", "色系搭配太舒服了", "超有气质", "这个风格很适合你"],
        "templates": ["{keyword}这套太好看了", "求{keyword}的链接"],
    },
    "美妆": {
        "weight": 20, "enabled": True, "label": "美妆评论",
        "comments": ["这个妆面好干净", "求粉底色号", "口红颜色太美了", "教程很详细，收藏了"],
        "templates": ["{keyword}这个妆容好干净", "{keyword}是什么色号"],
    },
    "种草": {
        "weight": 20, "enabled": True, "label": "种草评论",
        "comments": ["种草了！", "我也买了同款，真的不错", "已加购物车", "求推荐更多好物"],
        "templates": ["被{keyword}种草了", "{keyword}已加入清单"],
    },
    "美食": {
        "weight": 15, "enabled": True, "label": "美食评论",
        "comments": ["看着好好吃", "求地址", "收藏了，周末去试试", "这个做法很简单，明天就试"],
        "templates": ["{keyword}看着好好吃", "求{keyword}的店名"],
    },
    "家居": {
        "weight": 10, "enabled": True, "label": "家居评论",
        "comments": ["布置得好温馨", "求家具链接", "这个风格好喜欢", "家的感觉真好"],
        "templates": ["{keyword}的布置好温馨", "求{keyword}的链接"],
    },
}


class CorpusManager:
    """语料库管理器"""

    def __init__(self):
        self._cache = {}
        self._ensure_files()

    def _ensure_files(self):
        """确保语料库 YAML 文件存在"""
        for platform, data in [("douyin", DEFAULT_DOUYIN_COMMENTS), ("xiaohongshu", DEFAULT_XHS_COMMENTS)]:
            path = CORPUS_DIR / f"{platform}.yaml"
            if not path.exists():
                content = {"version": "1.0", "categories": data}
                path.write_text(yaml.dump(content, default_flow_style=False, allow_unicode=True, sort_keys=False))
                log.info(f"  📝 创建语料文件: {path.name} ({sum(1 for c in data.values() for _ in c.get('comments',[]))} 条)")

    def _load(self, platform: str) -> dict:
        """加载指定平台的语料"""
        if platform not in self._cache:
            path = CORPUS_DIR / f"{platform}.yaml"
            if path.exists():
                self._cache[platform] = yaml.safe_load(path.read_text()) or {}
            else:
                self._cache[platform] = {"version": "1.0", "categories": {}}
        return self._cache[platform]

    def list_categories(self) -> list:
        """列出所有平台的分类"""
        result = []
        for platform in ["douyin", "xiaohongshu"]:
            data = self._load(platform)
            for name, info in data.get("categories", {}).items():
                count = len(info.get("comments", [])) + len(info.get("templates", []))
                result.append({
                    "platform": platform,
                    "name": name,
                    "weight": info.get("weight", 0),
                    "enabled": info.get("enabled", True),
                    "count": count,
                    "label": info.get("label", name),
                })
        return result

    def get_comments(self, categories: List[str] = None, platform: str = None, count: int = 20) -> List[str]:
        """获取评论列表

        Args:
            categories: 指定分类（None = 所有启用分类）
            platform: 指定平台（None = 所有平台）
            count: 最多返回数量

        Returns:
            评论文本列表
        """
        results = []
        platforms = [platform] if platform else ["douyin", "xiaohongshu"]

        for p in platforms:
            data = self._load(p)
            for name, info in data.get("categories", {}).items():
                # 筛选分类
                if categories and name not in categories:
                    continue
                if not info.get("enabled", True):
                    continue
                if info.get("weight", 0) <= 0:
                    continue

                # 取评论
                comments = info.get("comments", [])
                templates = info.get("templates", [])
                combined = comments + templates
                # 按权重比例取
                take = max(1, int(count * info.get("weight", 10) / 100))
                results.extend(random.sample(combined, min(take, len(combined))))

        random.shuffle(results)
        return results[:count]

    def add_comment(self, category: str, text: str, platform: str = "douyin"):
        """添加一条评论到指定平台指定分类"""
        data = self._load(platform)
        cats = data.get("categories", {})
        if category not in cats:
            cats[category] = {"weight": 10, "enabled": True, "label": category, "comments": [], "templates": []}
        if "comments" not in cats[category]:
            cats[category]["comments"] = []
        cats[category]["comments"].append(text)
        data["categories"] = cats

        path = CORPUS_DIR / f"{platform}.yaml"
        path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False))
        self._cache.pop(platform, None)  # 清除缓存
        log.info(f"  ✅ 已添加评论到 [{platform}/{category}]: {text}")

    def delete_comment(self, category: str, index: int, platform: str = "douyin"):
        """删除指定索引的评论"""
        data = self._load(platform)
        cats = data.get("categories", {}).get(category, {})
        comments = cats.get("comments", [])
        if 0 <= index < len(comments):
            removed = comments.pop(index)
            cats["comments"] = comments
            path = CORPUS_DIR / f"{platform}.yaml"
            path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False))
            self._cache.pop(platform, None)
            log.info(f"  🗑 已删除评论 [{platform}/{category}]: {removed}")

    # ── 账号上下文 ──────────────────────────────────────────

    def set_account_id(self, account_id: str):
        """设置当前账号 ID，方便后续跟踪上下文"""
        self._account_id = account_id
        log.info(f"  👤 设置账号: {account_id}")

    # ── 视频标题匹配 → 评论 ──────────────────────────────────

    @staticmethod
    def _extract_first_keyword(video_title: str) -> Optional[str]:
        """从视频标题中提取第一个匹配的关键词"""
        for keywords, _ in KEYWORD_CATEGORY_MAP:
            for kw in keywords:
                if kw in video_title:
                    return kw
        # fallback: 取标题第一个有意义的词
        import re
        words = re.findall(r'[\w\u4e00-\u9fff]{2,}', video_title)
        return words[0] if words else ""

    @staticmethod
    def _match_keywords(video_title: str) -> list:
        """根据视频标题匹配关键词，返回匹配到的方向列表"""
        matched_directions = []
        for keywords, directions in KEYWORD_CATEGORY_MAP:
            for kw in keywords:
                if kw in video_title:
                    matched_directions.extend(directions)
                    break  # 一个关键词组只匹配一次
        return matched_directions

    def _get_comment_from_categories(self, category_names: list, platform: str = None) -> Optional[str]:
        """从指定的分类名列表中随机取一条评论（遍历所有平台）"""
        platforms = [platform] if platform else ["douyin", "xiaohongshu"]
        candidates = []

        for p in platforms:
            data = self._load(p)
            for cat_name, info in data.get("categories", {}).items():
                if cat_name not in category_names:
                    continue
                if not info.get("enabled", True):
                    continue
                comments = info.get("comments", []) + info.get("templates", [])
                candidates.extend(comments)

        if candidates:
            return random.choice(candidates)
        return None

    def _get_random_comment(self, platform: str = None) -> Optional[str]:
        """从所有启用分类中随机取一条评论"""
        platforms = [platform] if platform else ["douyin", "xiaohongshu"]
        all_comments = []

        for p in platforms:
            data = self._load(p)
            for name, info in data.get("categories", {}).items():
                if not info.get("enabled", True):
                    continue
                if info.get("weight", 0) <= 0:
                    continue
                comments = info.get("comments", []) + info.get("templates", [])
                all_comments.extend(comments)

        if all_comments:
            return random.choice(all_comments)
        return None

    def get_comment_for_video(self, video_title: str, direction: str = None) -> Optional[str]:
        """根据视频标题（和可选方向）从语料库中匹配一条评论

        Args:
            video_title: 视频标题文本
            direction:   可选，指定方向，如 "正面"/"提问"/"共鸣"/"补充"

        Returns:
            匹配到的评论文本，或 None
        """
        # 1) 从标题匹配关键词，得到方向列表
        matched_directions = self._match_keywords(video_title)

        # 2) 如果用户指定了 direction，优先使用，且排在前面
        if direction and direction in DIRECTION_TO_CATEGORY:
            # 去重：把指定的 direction 放到最前面
            if direction in matched_directions:
                matched_directions.remove(direction)
            matched_directions = [direction] + matched_directions
        elif direction:
            # direction 不在已知方向中时回退到默认匹配
            pass

        # 3) 有匹配的方向 → 尝试依次取对应分类的评论
        if matched_directions:
            for d in matched_directions:
                cat = DIRECTION_TO_CATEGORY.get(d)
                if not cat:
                    continue
                comment = self._get_comment_from_categories([cat])
                if comment:
                    # 替换 {keyword} 为视频标题中的第一个关键词
                    kw = self._extract_first_keyword(video_title)
                    if kw:
                        comment = comment.replace("{keyword}", kw)
                    return comment

        # 4) 没有匹配 → 随机返回一条
        comment = self._get_random_comment()
        if comment and "{keyword}" in comment:
            kw = self._extract_first_keyword(video_title)
            if kw:
                comment = comment.replace("{keyword}", kw)
        return comment
